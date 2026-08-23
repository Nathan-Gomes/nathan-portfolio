"""
AWS Lambda entrypoint for the portfolio-intelligence MCP connector.

Design note: mcp_server.py's streamable_http_app() runs a
StreamableHTTPSessionManager built for a long-lived server process (its
lifespan is meant to start once and stay open). Lambda invocations don't
give you that -- each request may land on a fresh execution environment,
and re-entering that session manager's lifespan more than once raises
RuntimeError. Rather than fight that mismatch, this handler talks to the
same registered tools (mcp.list_tools() / mcp.call_tool()) directly and
implements the minimal JSON-RPC surface an MCP client actually needs:
initialize, notifications/initialized, tools/list, tools/call. This is
correctly stateless per Lambda invocation and avoids SSE/session machinery
that Lambda's request/response model doesn't support anyway.
"""
import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(__file__))

# Lambda's filesystem is read-only except /tmp. The main portfolio.db is
# bundled read-only (fine -- it's only ever queried, never written by
# tool calls), but the audit_log table does get INSERTed into on every
# tool call, so that needs a writable location. Must be set before
# mcp_server is imported, since it reads this env var at import time.
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("MCP_AUDIT_DB_PATH", "/tmp/portfolio-audit.db")

from mcp_server import mcp

PROTOCOL_VERSION = "2024-11-05"
# Lambda Function URLs look like <id>.lambda-url.<region>.on.aws, not a
# custom domain, since this deployment skips API Gateway/CloudFront for
# simplicity. Set MCP_ALLOWED_HOSTS (comma-separated) as a Lambda
# environment variable to the actual Function URL host once you have it
# (shown after `aws lambda create-function-url-config` -- see deploy/README).
_default_hosts = "localhost,127.0.0.1"
ALLOWED_HOSTS = {
    h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", _default_hosts).split(",") if h.strip()
}


def _json_response(status, payload, extra_headers=None):
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(payload),
    }


def _jsonrpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _tool_to_dict(tool):
    d = {
        "name": tool.name,
        "description": tool.description or "",
        "inputSchema": tool.input_schema,
    }
    if tool.output_schema:
        d["outputSchema"] = tool.output_schema
    return d


async def _handle_rpc(body: dict):
    method = body.get("method")
    req_id = body.get("id")

    if method == "initialize":
        return _jsonrpc_result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": mcp.name, "version": mcp.version or ""},
        })

    if method in ("notifications/initialized", "notifications/cancelled"):
        # Notifications have no response per JSON-RPC; caller returns 202.
        return None

    if method == "tools/list":
        tools = await mcp.list_tools()
        return _jsonrpc_result(req_id, {"tools": [_tool_to_dict(t) for t in tools]})

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        try:
            result = await mcp.call_tool(name, arguments)
        except Exception as e:
            return _jsonrpc_error(req_id, -32000, f"Tool execution error: {e}")
        content = [block.model_dump(by_alias=True, exclude_none=True) for block in result.content]
        return _jsonrpc_result(req_id, {
            "content": content,
            "isError": getattr(result, "isError", False),
        })

    if method == "ping":
        return _jsonrpc_result(req_id, {})

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    # Optional shared-secret check. Since this Function URL is public with
    # no other auth in front of it, set MCP_SHARED_SECRET as a Lambda
    # environment variable and requests must send it back as a header.
    # Leave MCP_SHARED_SECRET unset while first testing if that's easier.
    required_secret = os.environ.get("MCP_SHARED_SECRET")
    if required_secret and headers.get("x-mcp-secret") != required_secret:
        return _json_response(403, {"error": "Forbidden"})

    # Minimal DNS-rebinding guard: only accept requests for the real domain
    # (or localhost while testing), same intent as the SDK's transport
    # security settings, applied manually since we bypass the ASGI app.
    host = headers.get("host", "").split(":")[0]
    if host and host not in ALLOWED_HOSTS:
        return _json_response(421, {"error": f"Invalid Host header: {host}"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _json_response(400, _jsonrpc_error(None, -32700, "Parse error"))

    try:
        result = asyncio.run(_handle_rpc(body))
    except Exception as e:
        return _json_response(500, _jsonrpc_error(body.get("id"), -32000, str(e)))

    if result is None:
        return {"statusCode": 202, "headers": {}, "body": ""}

    return _json_response(200, result)

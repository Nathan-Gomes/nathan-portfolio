"""
Tests the direct stateless Lambda handler (no Mangum/ASGI layer) by
simulating what API Gateway would send it -- no AWS account, Docker, or
network access required. Confirms cold-start-safe statelessness: every
call is independent, exactly like separate Lambda invocations would be.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

os.environ["MCP_ALLOWED_HOSTS"] = "mcp.nathan-gomes.com,localhost,127.0.0.1"

from lambda_handler import handler


def make_event(body, host="mcp.nathan-gomes.com", query=None):
    return {
        "headers": {"host": host, "content-type": "application/json"},
        "queryStringParameters": query,
        "body": json.dumps(body),
    }


def call(body, host="mcp.nathan-gomes.com", query=None):
    return handler(make_event(body, host, query), None)


print("=== initialize ===")
resp = call({"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"}}})
assert resp["statusCode"] == 200
body = json.loads(resp["body"])
assert body["result"]["serverInfo"]["name"] == "portfolio-intelligence"
print("OK\n")

print("=== notifications/initialized (should be 202, no body) ===")
resp = call({"jsonrpc": "2.0", "method": "notifications/initialized"})
assert resp["statusCode"] == 202
print("OK\n")

print("=== tools/list (fresh call, no prior state) ===")
resp = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
assert resp["statusCode"] == 200
body = json.loads(resp["body"])
tool_names = [t["name"] for t in body["result"]["tools"]]
print("tools:", tool_names)
assert len(tool_names) == 8 and "resolve_property" in tool_names
print("OK\n")

print("=== tools/call resolve_property (fresh call) ===")
resp = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "resolve_property", "arguments": {"query": "Cedar Place"}}})
assert resp["statusCode"] == 200
body = json.loads(resp["body"])
parsed = json.loads(body["result"]["content"][0]["text"])
print("resolved:", parsed["resolved"], "| property:", parsed["property"]["canonical_name"])
assert parsed["resolved"] and parsed["property"]["canonical_name"] == "Cedar Place"
print("OK\n")

print("=== tools/call get_open_anomalies (independent 'cold start' call) ===")
resp = call({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "get_open_anomalies", "arguments": {"property_id": 1}}})
assert resp["statusCode"] == 200
body = json.loads(resp["body"])
parsed = json.loads(body["result"]["content"][0]["text"])
print("open findings count:", parsed["count"])
assert parsed["count"] == 3
print("OK\n")

print("=== bogus tool name -> JSON-RPC error, not a crash ===")
resp = call({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
             "params": {"name": "delete_everything", "arguments": {}}})
body = json.loads(resp["body"])
print("error present:", "error" in body)
assert "error" in body
print("OK\n")

print("=== DNS-rebinding guard: unexpected Host header rejected ===")
resp = call({"jsonrpc": "2.0", "id": 6, "method": "tools/list"}, host="evil.example.com")
print("status:", resp["statusCode"])
assert resp["statusCode"] == 421
print("OK\n")

print("=== unknown method -> JSON-RPC method-not-found ===")
resp = call({"jsonrpc": "2.0", "id": 7, "method": "resources/list"})
body = json.loads(resp["body"])
assert body["error"]["code"] == -32601
print("OK\n")

print("=== shared secret accepted from query parameter for Claude connector URL ===")
os.environ["MCP_SHARED_SECRET"] = "test-secret"
resp = call({"jsonrpc": "2.0", "id": 8, "method": "tools/list", "params": {}},
            query={"secret": "test-secret"})
assert resp["statusCode"] == 200
body = json.loads(resp["body"])
assert len(body["result"]["tools"]) == 8
print("OK\n")

print("=== shared secret rejects missing credential ===")
resp = call({"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}})
assert resp["statusCode"] == 403
os.environ.pop("MCP_SHARED_SECRET", None)
print("OK\n")

print("ALL LAMBDA HANDLER CHECKS PASSED")

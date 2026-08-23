"""
End-to-end test: spawns mcp_server.py as a real subprocess and talks to it
over the MCP stdio protocol, exactly like Claude (or any MCP client) would.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = os.path.join(os.path.dirname(__file__), "..", "server", "mcp_server.py")


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER_PATH])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== Registered tools ===")
            for t in tools.tools:
                print(f"- {t.name}: {t.description.strip().splitlines()[0]}")

            print("\n=== Calling resolve_property('Cedar Place') ===")
            result = await session.call_tool("resolve_property", {"query": "Cedar Place"})
            payload = json.loads(result.content[0].text)
            print(json.dumps(payload, indent=2))
            assert payload["resolved"]
            property_id = payload["property"]["property_id"]

            print("\n=== Calling get_property_summary ===")
            result = await session.call_tool("get_property_summary", {"property_id": property_id})
            payload = json.loads(result.content[0].text)
            print(f"Open findings: {len(payload['open_findings'])}")
            print(f"Recent maintenance events: {len(payload['recent_maintenance_events'])}")
            for f in payload["open_findings"]:
                print(f"  - [{f['severity']}] {f['finding_type']}: {f['description'][:90]}...")

            print("\n=== Calling get_maintenance_history (repeat repairs) ===")
            result = await session.call_tool("get_maintenance_history", {"property_id": property_id})
            payload = json.loads(result.content[0].text)
            print(f"Total maintenance cost: ${payload['total_cost']}")
            for ri in payload["repeat_issues"]:
                print(f"  Repeat issue: {ri['equipment_name']} x{ri['event_count']}, ${ri['total_cost']}")

            print("\n=== Calling search_property_documents('circulation pump') ===")
            result = await session.call_tool(
                "search_property_documents",
                {"property_id": property_id, "query": "circulation pump"}
            )
            payload = json.loads(result.content[0].text)
            print(f"Found {payload['result_count']} matching chunks:")
            for r in payload["results"]:
                print(f"  - {r['title']} (p.{r['page_number']}, status={r['document_status']}): {r['text'][:80]}...")

            print("\n=== Calling get_open_anomalies ===")
            result = await session.call_tool("get_open_anomalies", {"property_id": property_id})
            payload = json.loads(result.content[0].text)
            assert payload["count"] == 3

            print("\n=== Unknown / ambiguous property ===")
            result = await session.call_tool("resolve_property", {"query": "Random Nonexistent Building"})
            payload = json.loads(result.content[0].text)
            assert not payload["resolved"]
            print("Correctly returned resolved=False:", payload["message"])

    print("\n\nMCP CLIENT/SERVER ROUND TRIP: ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())

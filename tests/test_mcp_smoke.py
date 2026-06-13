from __future__ import annotations

import os
import unittest

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_SMOKE_URL = os.environ.get("MCP_SMOKE_URL", "").strip()


@unittest.skipUnless(MCP_SMOKE_URL, "Set MCP_SMOKE_URL to run the external MCP smoke test")
class MCPExternalSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_list_tools_and_parse_intent(self) -> None:
        async with streamable_http_client(MCP_SMOKE_URL) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                initialize = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "parse_travel_intent",
                    {"payload": {"message": "sunny under $1000"}},
                )

        self.assertEqual(initialize.serverInfo.name, "flights-anywhere")
        self.assertEqual(
            {tool.name for tool in tools.tools},
            {
                "parse_travel_intent",
                "search_flights",
                "explore_destinations",
                "rank_destinations",
                "recommend_destinations",
            },
        )
        self.assertFalse(result.isError)
        self.assertEqual(result.structuredContent["applied_filters"]["budget_max"], 1000)


if __name__ == "__main__":
    unittest.main()

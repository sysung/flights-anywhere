from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient = None  # type: ignore[assignment]

from api.travel.intent import AIUnavailableError
from api.travel.models import RecommendationRequest, TravelFilters

from tests.test_travel_recommendation import FakeFlights, FakePlaces, FakeWeather


MCP_ACCEPT = "application/json, text/event-stream"
MCP_PROTOCOL_VERSION = "2025-03-26"
EXPECTED_TOOLS = {
    "parse_travel_intent",
    "search_flights",
    "explore_destinations",
    "rank_destinations",
    "recommend_destinations",
}


class MCPTestSession:
    def __init__(self, client: Any, name: str = "integration-test") -> None:
        self.client = client
        self.request_id = 1
        response = client.post(
            "/mcp/",
            json={
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": name, "version": "1.0"},
                },
            },
            headers={"Accept": MCP_ACCEPT},
        )
        if response.status_code != 200:
            raise AssertionError(f"MCP initialize failed: {response.status_code} {response.text}")
        self.session_id = response.headers["mcp-session-id"]
        self.headers = {
            "Accept": MCP_ACCEPT,
            "Mcp-Session-Id": self.session_id,
            "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        self.request_id += 1
        initialized = client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=self.headers,
        )
        if initialized.status_code != 202:
            raise AssertionError(f"MCP initialized notification failed: {initialized.status_code} {initialized.text}")
        self.active = True

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        response = self.client.post(
            "/mcp/",
            json={
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {},
            },
            headers=self.headers,
        )
        self.request_id += 1
        return response

    def list_tools(self) -> Any:
        return self.request("tools/list")

    def call_tool(self, name: str, payload: dict[str, Any] | None = None, *, include_payload: bool = True) -> Any:
        arguments = {"payload": payload or {}} if include_payload else {}
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> Any:
        response = self.client.delete("/mcp/", headers=self.headers)
        self.active = False
        return response


@unittest.skipIf(TestClient is None, "fastapi is not installed in this environment")
class MCPHTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from api import main

        cls.main = main
        cls.client_context = TestClient(main.app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def setUp(self) -> None:
        self.sessions: list[MCPTestSession] = []

    def tearDown(self) -> None:
        for session in self.sessions:
            if session.active:
                session.close()

    def session(self, name: str = "integration-test") -> MCPTestSession:
        session = MCPTestSession(self.client, name)
        self.sessions.append(session)
        return session

    def recommendation_response(self) -> Any:
        from api.travel.service import TravelRecommendationService

        service = TravelRecommendationService(flights=FakeFlights(), weather=FakeWeather(), places=FakePlaces())
        return service.recommend(
            RecommendationRequest(
                message="find trips that match my filters",
                filters=TravelFilters(
                    origin="SFO",
                    outbound_date="2026-08-01",
                    return_date="2026-08-08",
                    budget_max=1000,
                ),
            )
        )

    def test_lists_and_executes_every_published_tool(self) -> None:
        session = self.session()
        fake_flights = FakeFlights()
        recommendation = self.recommendation_response()

        with (
            patch.object(self.main.service, "search", side_effect=fake_flights.search) as search,
            patch.object(self.main.travel_service, "recommend", return_value=recommendation) as recommend,
        ):
            tools_response = session.list_tools()
            parse_response = session.call_tool("parse_travel_intent", {"message": "sunny under $1000"})
            search_response = session.call_tool(
                "search_flights",
                {
                    "origin": "SFO",
                    "destination": "HNL",
                    "outbound_date": "2026-08-01",
                    "return_date": "2026-08-08",
                },
            )
            explore_response = session.call_tool(
                "explore_destinations",
                {
                    "origin": "SFO",
                    "destination": "HNL",
                    "outbound_date": "2026-08-01",
                    "return_date": "2026-08-08",
                },
            )
            rank_response = session.call_tool(
                "rank_destinations",
                {
                    "message": "rank these",
                    "filters": {
                        "origin": "SFO",
                        "outbound_date": "2026-08-01",
                        "return_date": "2026-08-08",
                    },
                },
            )
            recommend_response = session.call_tool(
                "recommend_destinations",
                {
                    "message": "surprise me",
                    "filters": {
                        "origin": "SFO",
                        "outbound_date": "2026-08-01",
                        "return_date": "2026-08-08",
                    },
                },
            )

        tool_names = {tool["name"] for tool in tools_response.json()["result"]["tools"]}
        self.assertEqual(tool_names, EXPECTED_TOOLS)
        self.assertEqual(parse_response.json()["result"]["structuredContent"]["applied_filters"]["budget_max"], 1000)
        self.assertEqual(search_response.json()["result"]["structuredContent"]["query"]["destination"], "HNL")
        self.assertIsNone(explore_response.json()["result"]["structuredContent"]["query"]["destination"])
        self.assertIn("recommendations", rank_response.json()["result"]["structuredContent"])
        self.assertIn("recommendations", recommend_response.json()["result"]["structuredContent"])
        self.assertEqual(search.call_count, 2)
        self.assertEqual(recommend.call_count, 2)

    def test_rest_and_mcp_use_the_same_service_instances(self) -> None:
        session = self.session()
        fake_flights = FakeFlights()
        recommendation = self.recommendation_response()
        search_request = {
            "origin": "SFO",
            "destination": "HNL",
            "outbound_date": "2026-08-01",
            "return_date": "2026-08-08",
        }
        recommendation_request = {
            "message": "find trips that match my filters",
            "filters": {
                "origin": "SFO",
                "outbound_date": "2026-08-01",
                "return_date": "2026-08-08",
            },
        }

        with (
            patch.object(self.main.service, "search", side_effect=fake_flights.search) as search,
            patch.object(self.main.travel_service, "recommend", return_value=recommendation) as recommend,
        ):
            rest_search = self.client.post("/api/flights/search", json=search_request)
            mcp_search = session.call_tool("search_flights", search_request)
            rest_recommend = self.client.post("/api/travel/recommend", json=recommendation_request)
            mcp_recommend = session.call_tool("recommend_destinations", recommendation_request)

        self.assertEqual(rest_search.status_code, 200)
        self.assertFalse(mcp_search.json()["result"]["isError"])
        self.assertEqual(rest_recommend.status_code, 200)
        self.assertFalse(mcp_recommend.json()["result"]["isError"])
        self.assertEqual(search.call_count, 2)
        self.assertEqual(recommend.call_count, 2)

    def test_invalid_requests_return_protocol_errors_without_ending_session(self) -> None:
        session = self.session()
        malformed = self.client.post(
            "/mcp/",
            content="{",
            headers={**session.headers, "Content-Type": "application/json"},
        )
        unknown_method = session.request("not/a/method")
        unknown_tool = session.call_tool("not_a_tool")
        missing_payload = session.call_tool("parse_travel_intent", include_payload=False)
        invalid_filter = session.call_tool(
            "parse_travel_intent",
            {"message": "somewhere fun", "filters": {"sort": "invalid"}},
        )
        tools_after_errors = session.list_tools()

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()["error"]["code"], -32700)
        self.assertEqual(unknown_method.json()["error"]["code"], -32602)
        self.assertTrue(unknown_tool.json()["result"]["isError"])
        self.assertIn("Unknown tool", unknown_tool.json()["result"]["content"][0]["text"])
        self.assertTrue(missing_payload.json()["result"]["isError"])
        self.assertIn("Field required", missing_payload.json()["result"]["content"][0]["text"])
        self.assertTrue(invalid_filter.json()["result"]["isError"])
        self.assertEqual(tools_after_errors.status_code, 200)

    def test_provider_failures_are_recoverable_mcp_tool_errors(self) -> None:
        session = self.session()
        search_payload = {
            "origin": "SFO",
            "destination": "HNL",
            "outbound_date": "2026-08-01",
            "return_date": "2026-08-08",
        }
        recommendation_payload = {
            "message": "somewhere obscure that requires AI",
            "filters": {
                "origin": "SFO",
                "outbound_date": "2026-08-01",
                "return_date": "2026-08-08",
            },
        }

        with patch.object(
            self.main.service,
            "search",
            side_effect=TimeoutError("Timed out waiting for a Google Flights session request."),
        ):
            timeout = session.call_tool("search_flights", search_payload)
        with patch.object(
            self.main.travel_service,
            "recommend",
            side_effect=AIUnavailableError("GOOGLE_CLOUD_API_KEY is required for AI travel intent extraction."),
        ):
            ai_unavailable = session.call_tool("recommend_destinations", recommendation_payload)
        tools_after_errors = session.list_tools()

        self.assertTrue(timeout.json()["result"]["isError"])
        self.assertIn("Timed out waiting", timeout.json()["result"]["content"][0]["text"])
        self.assertTrue(ai_unavailable.json()["result"]["isError"])
        self.assertIn("GOOGLE_CLOUD_API_KEY", ai_unavailable.json()["result"]["content"][0]["text"])
        self.assertEqual(tools_after_errors.status_code, 200)

    def test_sessions_are_isolated_and_can_terminate_independently(self) -> None:
        first = self.session("first-client")
        second = self.session("second-client")

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(first.call_tool, "parse_travel_intent", {"message": "under $500"})
            second_future = executor.submit(second.call_tool, "parse_travel_intent", {"message": "under $1500"})
            first_result = first_future.result()
            second_result = second_future.result()
        first_close = first.close()
        second_tools = second.list_tools()
        closed_session_request = self.client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 99, "method": "tools/list", "params": {}},
            headers=first.headers,
        )

        self.assertNotEqual(first.session_id, second.session_id)
        self.assertEqual(first_result.json()["result"]["structuredContent"]["applied_filters"]["budget_max"], 500)
        self.assertEqual(second_result.json()["result"]["structuredContent"]["applied_filters"]["budget_max"], 1500)
        self.assertEqual(first_close.status_code, 200)
        self.assertEqual(closed_session_request.status_code, 404)
        self.assertEqual(second_tools.status_code, 200)

    def test_ui_rest_health_and_mcp_routes_coexist(self) -> None:
        session = self.session()
        fake_flights = FakeFlights()

        with patch.object(self.main.service, "search", side_effect=fake_flights.search):
            health = self.client.get("/healthz")
            rest = self.client.post(
                "/api/flights/search",
                json={
                    "origin": "SFO",
                    "destination": "HNL",
                    "outbound_date": "2026-08-01",
                    "return_date": "2026-08-08",
                },
            )
        mcp = session.list_tools()
        root = self.client.get("/")
        redirect = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 50, "method": "tools/list", "params": {}},
            headers=session.headers,
            follow_redirects=False,
        )

        self.assertEqual(health.status_code, 200)
        self.assertEqual(rest.status_code, 200)
        self.assertEqual(mcp.status_code, 200)
        self.assertEqual(redirect.status_code, 307)
        self.assertEqual(redirect.headers["location"], "/mcp/")
        expected_root_status = 200 if self.main.WEB_DIST.exists() else 404
        self.assertEqual(root.status_code, expected_root_status)


if __name__ == "__main__":
    unittest.main()

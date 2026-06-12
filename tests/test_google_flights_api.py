from __future__ import annotations

import base64
import json
import logging
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from api.google_flights.builders import explore_request, shopping_request
from api.google_flights.codec import decode_f_req, encode_inner, parse_rpc_response
from api.google_flights.entities import Place, resolve_place
from api.google_flights.models import FlightSearchRequest, SearchResponse
from api.google_flights.parsers import parse_explore, parse_flight_options
from api.google_flights.service import GoogleFlightsService
from api.google_flights.session import SessionManager, SessionTemplate, _has_mutable_round_trip_legs, _seed_f_req, _select_bootstrap_origin

logging.disable(logging.CRITICAL)


class FakeSessionManager:
    def __init__(self, template: SessionTemplate | None = None) -> None:
        self.template = template or session_template()
        self.refresh_count = 0

    def get(self) -> SessionTemplate:
        return self.template

    def refresh(self) -> SessionTemplate:
        self.refresh_count += 1
        return self.template

    def invalidate(self) -> None:
        pass


def seed_inner() -> list:
    return [
        [],
        None,
        None,
        [
            None,
            None,
            1,
            None,
            [],
            1,
            [1, 0, 0, 0],
            None,
            None,
            None,
            None,
            None,
            None,
            [
                [[[[ "/m/0r5yp", 5]]], [[[ "/m/02j71", 6]]], None, 0, None, None, "2026-08-01", None, None, None, None, None, None, None, 3],
                [[[[ "/m/02j71", 6]]], [[[ "/m/0r5yp", 5]]], None, 0, None, None, "2026-08-08", None, None, None, None, None, None, None, 3],
            ],
            None,
            None,
            None,
            1,
        ],
    ]


def session_template() -> SessionTemplate:
    data = encode_inner(seed_inner(), {"at": ""})
    return SessionTemplate(
        url="https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetExploreDestinations?f.sid=1&bl=test&hl=en",
        headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
        data=data,
    )


def bad_session_template() -> SessionTemplate:
    inner = [[], [None, None, 1, None, [], 1, [1, 0, 0, 0], None, None, None, None, None, None, [[[[["/m/0r5yp", 4]]], [], None, 0]]]]
    data = encode_inner(inner, {"at": ""})
    return SessionTemplate(session_template().url, session_template().headers, data)


def rpc_text(value: object) -> str:
    return ")]}'\n\n" + json.dumps(value)


def option_token(*flight_nums: str) -> str:
    raw = ("|" + "|".join(flight_nums)).encode()
    return base64.b64encode(raw).decode()


def explore_row(dest: str = "LAX", price: int = 106, route_token: str = "ROUTE") -> list:
    return [
        "/m/030qb3t",
        [[None, price], route_token],
        None,
        None,
        None,
        None,
        ["F9", "Frontier", 0, 96, None, dest, "/m/0r5yp"],
    ]


def flight_option_row(
    token: str | None = None,
    *,
    airline_code: str = "F9",
    airline: str = "Frontier",
    origin: str = "SFO",
    dest: str = "LAX",
    date: str = "2026-08-01",
    price: int = 106,
) -> list:
    return [
        [[None, price], token or option_token("F92858")],
        airline_code,
        airline,
        0,
        96,
        True,
        date,
        origin,
        "San Francisco International Airport",
        dest,
        "Los Angeles International Airport",
    ]


class UnitTests(unittest.TestCase):
    def test_resolve_place_handles_anywhere_and_unknown_codes(self) -> None:
        entities = {"SFO": Place("SFO", "/m/0r5yp", type=5)}

        anywhere = resolve_place(None, entities, anywhere=True)

        self.assertEqual(anywhere.code, "ANYWHERE")
        self.assertEqual(anywhere.entity_id, "/m/02j71")
        with self.assertRaises(ValueError):
            resolve_place("NOPE", entities)

    def test_decode_and_encode_f_req_round_trip(self) -> None:
        data = session_template().data

        outer, inner, form = decode_f_req(data)
        encoded = encode_inner(inner, form)

        self.assertIsNone(outer[0])
        self.assertIn("f.req=", encoded)
        self.assertEqual(decode_f_req(encoded)[1], inner)

    def test_seed_f_req_has_mutable_round_trip_legs(self) -> None:
        inner = json.loads(json.loads(_seed_f_req())[1])
        legs = inner[3][13]

        self.assertEqual(legs[0][0][0][0][0], "/m/0r5yp")
        self.assertEqual(legs[0][1][0][0][0], "/m/02j71")
        self.assertEqual(legs[1][0][0][0][0], "/m/02j71")
        self.assertEqual(legs[1][1][0][0][0], "/m/0r5yp")

    def test_compact_origin_only_f_req_is_accepted_and_repaired(self) -> None:
        compact_inner = [
            [],
            None,
            None,
            [
                None,
                None,
                1,
                None,
                [],
                1,
                [1, 0, 0, 0],
                None,
                None,
                None,
                None,
                None,
                None,
                [
                    [[[["SFO", 0]]], [], None, 0],
                    [[], [[["SFO", 0]]], None, 0],
                ],
            ],
        ]
        data = encode_inner(compact_inner, {"at": ""})
        query = FlightSearchRequest(origin="SFO", outbound_date="2026-09-01", return_date="2026-09-08")

        self.assertTrue(_has_mutable_round_trip_legs(data))
        mutated = decode_f_req(explore_request(compact_inner, {"at": ""}, query, Place("SFO", "/m/0r5yp", type=5), Place("ANYWHERE", "/m/02j71", type=6)))[1]
        legs = mutated[3][13]

        self.assertEqual(legs[0][0][0][0], ["/m/0r5yp", 5])
        self.assertEqual(legs[0][1][0][0], ["/m/02j71", 6])
        self.assertEqual(legs[0][6], "2026-09-01")
        self.assertEqual(legs[1][6], "2026-09-08")

    def test_session_manager_refreshes_bad_cached_session_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/session.json"
            with open(path, "w") as fh:
                json.dump({"url": bad_session_template().url, "headers": {}, "data": bad_session_template().data}, fh)

            manager = SessionManager(path=Path(path), ttl_seconds=3600)
            with patch("api.google_flights.session.capture_session", return_value={"url": session_template().url, "headers": {}, "data": session_template().data}):
                session = manager.get()

        self.assertEqual(decode_f_req(session.data)[1][3][13][0][1][0][0][0], "/m/02j71")

    def test_session_manager_refreshes_expired_and_corrupt_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            path.write_text("not json")
            manager = SessionManager(path=path, ttl_seconds=3600)
            fresh = {"url": session_template().url, "headers": {}, "data": session_template().data}
            with patch("api.google_flights.session.capture_session", return_value=fresh) as capture:
                self.assertEqual(manager.get().url, session_template().url)
                self.assertEqual(capture.call_count, 1)

            old_time = time.time() - 10
            path.write_text(json.dumps(fresh))
            __import__("os").utime(path, (old_time, old_time))
            manager = SessionManager(path=path, ttl_seconds=1)
            with patch("api.google_flights.session.capture_session", return_value=fresh) as capture:
                self.assertEqual(manager.get().url, session_template().url)
                self.assertEqual(capture.call_count, 1)

    def test_select_bootstrap_origin_uses_visible_origin_picker(self) -> None:
        class FakeKeyboard:
            def __init__(self) -> None:
                self.actions = []

            def press(self, value: str) -> None:
                self.actions.append(("press", value))

            def type(self, value: str) -> None:
                self.actions.append(("type", value))

        class FakeLocator:
            def __init__(self, page, selector: str) -> None:
                self.page = page
                self.selector = selector
                self.first = self

            def inner_text(self, timeout: int | None = None) -> str:
                return self.page.body

            def is_visible(self, timeout: int | None = None) -> bool:
                return self.selector == 'input[placeholder="Where from?"]'

            def click(self, timeout: int | None = None) -> None:
                self.page.clicks.append(self.selector)

        class FakeText:
            def __init__(self, page, text: str) -> None:
                self.page = page
                self.text = text
                self.first = self

            def click(self, timeout: int | None = None) -> None:
                self.page.clicks.append(self.text)

        class FakePage:
            def __init__(self) -> None:
                self.body = "Where are you flying from?"
                self.keyboard = FakeKeyboard()
                self.clicks = []

            def locator(self, selector: str) -> FakeLocator:
                return FakeLocator(self, selector)

            def get_by_text(self, text: str, exact: bool = False) -> FakeText:
                return FakeText(self, text)

            def wait_for_timeout(self, _milliseconds: int) -> None:
                pass

        page = FakePage()

        _select_bootstrap_origin(page, "SFO")

        self.assertIn('input[placeholder="Where from?"]', page.clicks)
        self.assertIn("San Francisco International Airport", page.clicks)
        self.assertIn(("type", "SFO"), page.keyboard.actions)

    def test_builders_mutate_explore_and_shopping_requests(self) -> None:
        query = FlightSearchRequest(
            origin="SFO",
            destination="LAX",
            outbound_date="2026-09-01",
            return_date="2026-09-08",
            nonstop=True,
        )
        _outer, inner, form = decode_f_req(session_template().data)
        origin = Place("SFO", "/m/0r5yp", type=5)
        dest = Place("LAX", "/m/030qb3t", type=4)

        explore_inner = decode_f_req(explore_request(inner, form, query, origin, dest))[1]
        shopping_inner = decode_f_req(shopping_request(inner, form, query, origin, dest))[1]

        for block in (explore_inner[3], shopping_inner[1]):
            legs = block[13]
            self.assertEqual(legs[0][0][0][0], ["/m/0r5yp", 5])
            self.assertEqual(legs[0][1][0][0], ["/m/030qb3t", 4])
            self.assertEqual(legs[0][6], "2026-09-01")
            self.assertEqual(legs[1][6], "2026-09-08")
            self.assertEqual(legs[0][3], 1)
            self.assertEqual(legs[1][3], 1)

    def test_parse_explore_normalizes_destination_cards(self) -> None:
        query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")

        rows = parse_explore([[explore_row()]], query)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, "explore")
        self.assertEqual(rows[0].selection_stage, "destination")
        self.assertEqual(rows[0].dest, "LAX")
        self.assertEqual(rows[0].price, 106)
        self.assertEqual(rows[0].route_token, "ROUTE")

    def test_parsers_return_empty_for_unknown_shapes_and_dedupe_explore(self) -> None:
        query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")

        unknown_explore = parse_explore([{"unexpected": "shape"}], query)
        unknown_options = parse_flight_options([{"unexpected": "shape"}], query, source="shopping", stage="outbound")
        duplicate_explore = parse_explore([[explore_row(), explore_row()]], query)

        self.assertEqual(unknown_explore, [])
        self.assertEqual(unknown_options, [])
        self.assertEqual(len(duplicate_explore), 1)

    def test_parse_flight_options_extracts_direct_and_multi_flight_numbers(self) -> None:
        query = FlightSearchRequest(origin="SFO", destination="LAX", outbound_date="2026-08-01", return_date="2026-08-08")

        direct = parse_flight_options([[flight_option_row(option_token("F92858"))]], query, source="shopping", stage="outbound")
        multi = parse_flight_options(
            [[flight_option_row(option_token("AS1620", "LA2479"), airline_code="multi", airline="Alaska, LATAM")]],
            query,
            source="shopping",
            stage="outbound",
        )

        self.assertEqual(direct[0].flight_nums, ["F92858"])
        self.assertEqual(multi[0].flight_nums, ["AS1620", "LA2479"])


class IntegrationTests(unittest.TestCase):
    def test_service_explore_branch_enriches_route_details(self) -> None:
        query = FlightSearchRequest(
            origin="SFO",
            outbound_date="2026-08-01",
            return_date="2026-08-08",
            include_details=True,
            details_limit=1,
        )
        entities = {
            "SFO": Place("SFO", "/m/0r5yp", type=5),
            "ANYWHERE": Place("ANYWHERE", "/m/02j71", type=6),
        }
        responses = [rpc_text([[explore_row()]]), rpc_text([[flight_option_row()]])]

        manager = FakeSessionManager()
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", side_effect=responses
        ):
            response = GoogleFlightsService(manager).search(query)

        self.assertEqual(response.mode, "explore")
        self.assertEqual(response.selection_stage, "results")
        self.assertEqual(response.results[0].flight_num, "F92858")
        self.assertEqual(response.results[0].outbound_options[0]["flight_nums"], ["F92858"])

    def test_include_details_false_skips_details_rpc_and_limit_caps_enrichment(self) -> None:
        entities = {
            "SFO": Place("SFO", "/m/0r5yp", type=5),
            "ANYWHERE": Place("ANYWHERE", "/m/02j71", type=6),
        }

        no_details_query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", return_value=rpc_text([[explore_row()]])
        ) as post:
            response = GoogleFlightsService(FakeSessionManager()).search(no_details_query)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(response.results[0].outbound_options, [])

        limited_query = FlightSearchRequest(
            origin="SFO",
            outbound_date="2026-08-01",
            return_date="2026-08-08",
            include_details=True,
            details_limit=1,
        )
        explore = rpc_text([[explore_row("LAX", route_token="R1"), explore_row("LAS", route_token="R2")]])
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", side_effect=[explore, rpc_text([[flight_option_row()]])]
        ) as post:
            response = GoogleFlightsService(FakeSessionManager()).search(limited_query)
        self.assertEqual(post.call_count, 2)
        self.assertNotEqual(response.results[0].outbound_options, [])
        self.assertEqual(response.results[1].outbound_options, [])

    def test_service_shopping_branch_returns_outbound_options(self) -> None:
        query = FlightSearchRequest(origin="SFO", destination="LAX", outbound_date="2026-08-01", return_date="2026-08-08")
        entities = {
            "SFO": Place("SFO", "/m/0r5yp", type=5),
            "LAX": Place("LAX", "/m/030qb3t", type=4),
        }

        manager = FakeSessionManager()
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", return_value=rpc_text([[flight_option_row()]])
        ):
            response = GoogleFlightsService(manager).search(query)

        self.assertEqual(response.mode, "shopping")
        self.assertEqual(response.selection_stage, "outbound")
        self.assertEqual(response.results[0].source, "shopping")
        self.assertEqual(response.results[0].flight_num, "F92858")

    def test_service_refreshes_after_bad_session_shape(self) -> None:
        query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
        entities = {
            "SFO": Place("SFO", "/m/0r5yp", type=5),
            "ANYWHERE": Place("ANYWHERE", "/m/02j71", type=6),
        }
        manager = FakeSessionManager(bad_session_template())
        manager.template = bad_session_template()

        def refresh() -> SessionTemplate:
            manager.refresh_count += 1
            manager.template = session_template()
            return manager.template

        manager.refresh = refresh  # type: ignore[method-assign]
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", return_value=rpc_text([[explore_row()]])
        ):
            response = GoogleFlightsService(manager).search(query)

        self.assertEqual(manager.refresh_count, 1)
        self.assertEqual(response.results[0].dest, "LAX")

    def test_service_retries_once_after_http_error(self) -> None:
        query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
        entities = {
            "SFO": Place("SFO", "/m/0r5yp", type=5),
            "ANYWHERE": Place("ANYWHERE", "/m/02j71", type=6),
        }
        manager = FakeSessionManager()
        with patch("api.google_flights.service.load_entities", return_value=entities), patch(
            "api.google_flights.service.post", side_effect=[httpx.HTTPStatusError("403", request=httpx.Request("POST", "https://example.com"), response=httpx.Response(403)), rpc_text([[explore_row()]])]
        ):
            response = GoogleFlightsService(manager).search(query)

        self.assertEqual(manager.refresh_count, 1)
        self.assertEqual(response.results[0].dest, "LAX")

    def test_service_does_not_retry_session_capture_timeout(self) -> None:
        class TimeoutSessionManager:
            def __init__(self) -> None:
                self.refresh_count = 0
                self.invalidate_count = 0

            def get(self) -> SessionTemplate:
                raise TimeoutError("Timed out waiting for a Google Flights session request.")

            def refresh(self) -> SessionTemplate:
                self.refresh_count += 1
                return session_template()

            def invalidate(self) -> None:
                self.invalidate_count += 1

        query = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
        manager = TimeoutSessionManager()

        with self.assertRaises(TimeoutError):
            GoogleFlightsService(manager).search(query)  # type: ignore[arg-type]

        self.assertEqual(manager.refresh_count, 0)
        self.assertEqual(manager.invalidate_count, 1)


class E2ETests(unittest.TestCase):
    def test_fastapi_search_endpoint_uses_unified_response_schema(self) -> None:
        try:
            from api.main import search_flights
        except ModuleNotFoundError:
            self.skipTest("fastapi is not installed in this environment")

        fake_response = SearchResponse(
            mode="explore",
            selection_stage="results",
            query={"origin": "SFO", "destination": None},
            results=[],
            workflow_state={"mode": "explore"},
        )

        with patch("api.main.service.search", return_value=fake_response):
            response = search_flights(
                FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
            )

        self.assertEqual(response.mode, "explore")
        self.assertEqual(response.results, [])
        self.assertEqual(response.workflow_state["mode"], "explore")

    def test_healthz_endpoint(self) -> None:
        try:
            from api.main import healthz
        except ModuleNotFoundError:
            self.skipTest("fastapi is not installed in this environment")

        self.assertEqual(healthz(), {"status": "ok"})

    def test_api_maps_validation_and_unavailable_errors(self) -> None:
        try:
            from fastapi import HTTPException
            from api.main import search_flights
        except ModuleNotFoundError:
            self.skipTest("fastapi is not installed in this environment")

        request = FlightSearchRequest(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08")
        with patch("api.main.service.search", side_effect=ValueError("bad airport")):
            with self.assertRaises(HTTPException) as bad_request:
                search_flights(request)
        with patch("api.main.service.search", side_effect=httpx.HTTPError("google failed")):
            with self.assertRaises(HTTPException) as unavailable:
                search_flights(request)

        self.assertEqual(bad_request.exception.status_code, 400)
        self.assertEqual(unavailable.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()

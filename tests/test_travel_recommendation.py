from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from api.google_flights.models import FlightOption, SearchResponse
from api.travel.enrichment import PlacesSignal, WeatherSignal
from api.travel.intent import TravelIntentExtractor, is_iso_date, merge_filters
from api.travel.mcp_server import parse_travel_intent_tool, recommend_destinations_tool
from api.travel.models import FilterParseRequest, RecommendationRequest, TravelFilters
from api.travel.service import TravelRecommendationService


class FakeFlights:
    def __init__(self) -> None:
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        return SearchResponse(
            mode="explore",
            selection_stage="results",
            query=request.model_dump(),
            results=[
                FlightOption(
                    source="explore",
                    selection_stage="destination",
                    origin=request.origin,
                    dest="HNL",
                    outbound_date=request.outbound_date,
                    return_date=request.return_date,
                    price=450,
                    stops=0,
                    duration_minutes=330,
                ),
                FlightOption(
                    source="explore",
                    selection_stage="destination",
                    origin=request.origin,
                    dest="SEA",
                    outbound_date=request.outbound_date,
                    return_date=request.return_date,
                    price=180,
                    stops=1,
                    duration_minutes=130,
                ),
                FlightOption(
                    source="explore",
                    selection_stage="destination",
                    origin=request.origin,
                    dest="HND",
                    outbound_date=request.outbound_date,
                    return_date=request.return_date,
                    price=980,
                    stops=0,
                    duration_minutes=660,
                ),
            ],
            workflow_state={"mode": "explore"},
        )


class DateSensitiveFakeFlights:
    def __init__(self) -> None:
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        day = date.fromisoformat(request.outbound_date).day
        price = 120 if len(self.requests) == 3 else 500 + day
        return SearchResponse(
            mode="explore",
            selection_stage="results",
            query=request.model_dump(),
            results=[
                FlightOption(
                    source="explore",
                    selection_stage="destination",
                    origin=request.origin,
                    dest="CUN",
                    outbound_date=request.outbound_date,
                    return_date=request.return_date,
                    price=price,
                    stops=0,
                    duration_minutes=300,
                )
            ],
            workflow_state={"mode": "explore"},
        )


class FakeWeather:
    def get_weather(self, destination: str, filters: TravelFilters) -> WeatherSignal:
        scores = {"HNL": 0.95, "HND": 0.6, "SEA": 0.3}
        score = scores.get(destination, 0.5)
        return WeatherSignal(summary=f"{destination} weather profile", sunny_score=score, warm_score=score, rainy_risk=1 - score)


class FakePlaces:
    def get_places(self, destination: str, filters: TravelFilters) -> PlacesSignal:
        matched = ["temples"] if destination == "HND" and "temples" in filters.vibes else []
        return PlacesSignal(summary=f"{destination} places profile", matched_interests=matched, score=1.0 if matched else 0.2)


class TravelIntentTests(unittest.TestCase):
    def test_extracts_surprise_budget_and_weather_prompt(self) -> None:
        intent = TravelIntentExtractor().extract("Surprise me somewhere sunny next week under $1000")

        self.assertTrue(intent.surprise)
        self.assertEqual(intent.filters.budget_max, 1000)
        self.assertIn("sunny", intent.filters.climates)
        self.assertEqual(intent.filters.sort, "best_match")
        self.assertTrue(intent.requires_weather)
        self.assertIsNotNone(intent.filters.outbound_date)

    def test_extracts_japanese_temple_places_prompt(self) -> None:
        intent = TravelIntentExtractor().extract("I want to go to places with Japanese temples")

        self.assertIn("temples", intent.filters.vibes)
        self.assertTrue(intent.requires_places)

    def test_extracts_week_trip_length_followup(self) -> None:
        intent = TravelIntentExtractor().extract("for a week", TravelFilters(origin="SFO"))

        self.assertEqual(intent.filters.trip_length_days, 7)

    def test_flexible_next_week_uses_current_trip_length(self) -> None:
        intent = TravelIntentExtractor().extract("sometime next week", TravelFilters(origin="SFO", trip_length_days=7))

        self.assertTrue(is_iso_date(intent.filters.outbound_date))
        self.assertTrue(is_iso_date(intent.filters.return_date))
        self.assertEqual(
            (date.fromisoformat(intent.filters.return_date) - date.fromisoformat(intent.filters.outbound_date)).days,
            7,
        )

    def test_merge_normalizes_natural_language_date_strings(self) -> None:
        filters = merge_filters(
            TravelFilters(origin="SFO", trip_length_days=7),
            TravelFilters(outbound_date="next week"),
        )

        self.assertNotEqual(filters.outbound_date, "next week")
        self.assertTrue(is_iso_date(filters.outbound_date))
        self.assertTrue(is_iso_date(filters.return_date))

    def test_extracts_cheapest_anytime_as_flexible_dates(self) -> None:
        intent = TravelIntentExtractor().extract("Find the cheapest 1 week trip anytime in the next 6 months under $1000")

        self.assertEqual(intent.filters.date_mode, "flexible")
        self.assertEqual(intent.filters.flexible_window, "next_6_months")
        self.assertEqual(intent.filters.trip_length_days, 7)
        self.assertEqual(intent.filters.sort, "cheapest")


class TravelRecommendationTests(unittest.TestCase):
    def service(self) -> TravelRecommendationService:
        return TravelRecommendationService(flights=FakeFlights(), weather=FakeWeather(), places=FakePlaces())

    def test_filter_merging_prefers_new_chat_intent(self) -> None:
        request = FilterParseRequest(
            message="sunny under $900",
            filters=TravelFilters(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08", budget_max=1200),
        )

        response = self.service().parse_filters(request)

        self.assertEqual(response.applied_filters.origin, "SFO")
        self.assertEqual(response.applied_filters.budget_max, 900)
        self.assertIn("sunny", response.applied_filters.climates)
        self.assertIsNone(response.clarifying_question)

    def test_recommendation_ranks_with_weather_and_places(self) -> None:
        request = RecommendationRequest(
            message="sunny place with Japanese temples under $1000",
            filters=TravelFilters(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08"),
        )

        response = self.service().recommend(request)

        self.assertEqual(response.recommendations[0].destination, "HND")
        self.assertEqual(response.recommendations[0].weather.summary, "HND weather profile")
        self.assertIn("temples", response.recommendations[0].places.matched_interests)
        self.assertTrue(response.active_filters)

    def test_recommendation_asks_for_missing_origin_or_dates(self) -> None:
        response = self.service().recommend(RecommendationRequest(message="surprise me somewhere tropical under $1000"))

        self.assertIsNotNone(response.clarifying_question)
        self.assertEqual(response.clarifying_question.field, "origin")
        self.assertEqual(response.recommendations, [])

    def test_recommendation_remembers_trip_length_when_asking_for_dates(self) -> None:
        response = self.service().recommend(
            RecommendationRequest(message="for a week", filters=TravelFilters(origin="SFO", budget_max=1000))
        )

        self.assertIsNotNone(response.clarifying_question)
        self.assertIn("7-day trip", response.clarifying_question.question)

    def test_recommendation_accepts_choose_any_date_followup(self) -> None:
        service = self.service()

        response = service.recommend(
            RecommendationRequest(
                message="choose any date then for me",
                filters=TravelFilters(origin="SFO", trip_length_days=7, budget_max=1000, vibes=["nightlife"]),
            )
        )

        self.assertIsNone(response.clarifying_question)
        self.assertEqual(response.applied_filters.date_mode, "flexible")
        self.assertIsNotNone(response.applied_filters.flexible_window_start)
        self.assertIsNotNone(response.applied_filters.flexible_window_end)
        self.assertGreater(len(service.flights.requests), 1)
        self.assertTrue(is_iso_date(service.flights.requests[0].outbound_date))

    def test_flexible_recommendation_searches_candidate_dates_and_keeps_cheapest(self) -> None:
        service = TravelRecommendationService(flights=DateSensitiveFakeFlights(), weather=FakeWeather(), places=FakePlaces())

        response = service.recommend(
            RecommendationRequest(
                message="cheapest trip any date",
                filters=TravelFilters(origin="SFO", destination="CUN", trip_length_days=7, budget_max=1000),
            )
        )

        self.assertEqual(response.applied_filters.date_mode, "flexible")
        self.assertGreater(len(service.flights.requests), 1)
        self.assertEqual(response.recommendations[0].price, 120)
        self.assertIn("Cheapest flexible date", response.recommendations[0].tags)

    def test_rest_recommend_endpoint_uses_shared_service(self) -> None:
        try:
            from api.main import recommend_travel
        except ModuleNotFoundError:
            self.skipTest("fastapi is not installed in this environment")

        expected = self.service().recommend(
            RecommendationRequest(
                message="sunny under $1000",
                filters=TravelFilters(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08"),
            )
        )
        with patch("api.main.travel_service.recommend", return_value=expected):
            response = recommend_travel(
                RecommendationRequest(
                    message="sunny under $1000",
                    filters=TravelFilters(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08"),
                )
            )

        self.assertEqual(response.recommendations[0].destination, expected.recommendations[0].destination)

    def test_rest_recommend_endpoint_maps_session_timeout_to_503(self) -> None:
        try:
            from fastapi import HTTPException
            from api.main import recommend_travel
        except ModuleNotFoundError:
            self.skipTest("fastapi is not installed in this environment")

        with patch("api.main.travel_service.recommend", side_effect=TimeoutError("Timed out waiting for a Google Flights session request.")):
            with self.assertRaises(HTTPException) as unavailable:
                recommend_travel(
                    RecommendationRequest(
                        message="sunny next week under $1000",
                        filters=TravelFilters(origin="SFO", outbound_date="2026-08-01", return_date="2026-08-08"),
                    )
                )

        self.assertEqual(unavailable.exception.status_code, 503)
        self.assertIn("Timed out waiting", unavailable.exception.detail)

    def test_mcp_tool_wrappers_return_serializable_payloads(self) -> None:
        parse_payload = parse_travel_intent_tool({"message": "sunny under $1000"}, service=self.service())
        recommend_payload = recommend_destinations_tool(
            {
                "message": "sunny under $1000",
                "filters": {"origin": "SFO", "outbound_date": "2026-08-01", "return_date": "2026-08-08"},
            },
            service=self.service(),
        )

        self.assertIn("applied_filters", parse_payload)
        self.assertIn("recommendations", recommend_payload)


if __name__ == "__main__":
    unittest.main()

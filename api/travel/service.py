from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from api.google_flights.models import FlightOption, FlightSearchRequest
from api.google_flights.service import GoogleFlightsService
from api.travel.enrichment import PlacesProvider, ProfilePlacesProvider, ProfileWeatherProvider, WeatherProvider, destination_name
from api.travel.intent import AIUnavailableError, TravelIntentExtractor, flexible_window_bounds, merge_filters
from api.travel.models import (
    ActiveFilterChip,
    ClarifyingQuestion,
    DestinationRecommendation,
    ExtractedIntent,
    FallbackOption,
    FilterAction,
    FilterParseRequest,
    FilterParseResponse,
    RecommendationRequest,
    RecommendationResponse,
    TravelFilters,
)

logger = logging.getLogger(__name__)


@dataclass
class RankedFlight:
    flight: FlightOption
    score: float
    tags: list[str]


class TravelRecommendationService:
    def __init__(
        self,
        *,
        flights: GoogleFlightsService | None = None,
        extractor: TravelIntentExtractor | None = None,
        weather: WeatherProvider | None = None,
        places: PlacesProvider | None = None,
    ) -> None:
        self.flights = flights or GoogleFlightsService()
        self.extractor = extractor or TravelIntentExtractor()
        self.weather = weather or ProfileWeatherProvider()
        self.places = places or ProfilePlacesProvider()

    def parse_filters(self, request: FilterParseRequest) -> FilterParseResponse:
        intent = self.extractor.extract(request.message, request.filters)
        applied = merge_filters(request.filters, intent.filters)
        question = self._clarifying_question(applied)
        return FilterParseResponse(
            intent=intent,
            applied_filters=applied,
            active_filters=self._active_chips(applied, intent.sources),
            clarifying_question=question,
        )

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        parsed = self.parse_filters(FilterParseRequest(message=request.message, filters=request.filters))
        question = parsed.clarifying_question
        if question:
            return RecommendationResponse(
                assistant_message=question.question,
                applied_filters=parsed.applied_filters,
                active_filters=parsed.active_filters,
                actions=[FilterAction(action="ask_clarifying_question", key=question.field)],
                clarifying_question=question,
            )

        flight_results = self._search_flights(parsed.applied_filters)
        ranked = self._rank(flight_results, parsed.applied_filters, parsed.intent)
        exact_recommendations = self._matching_recommendations(ranked, parsed.applied_filters, parsed.intent)
        relaxed = False
        if exact_recommendations:
            recommendations = exact_recommendations
            fallback_options: list[FallbackOption] = []
        else:
            recommendations = self._recommendations(ranked, parsed.applied_filters, parsed.intent, relaxed=True)
            fallback_options = [] if recommendations else self._fallback_options(ranked, parsed.applied_filters, parsed.intent)
            relaxed = bool(recommendations)
        assistant = self._assistant_message(recommendations, parsed.applied_filters, fallback_options, relaxed=relaxed)
        return RecommendationResponse(
            assistant_message=assistant,
            applied_filters=parsed.applied_filters,
            active_filters=parsed.active_filters,
            actions=[FilterAction(action="run_search")],
            recommendations=recommendations,
            fallback_options=fallback_options,
        )

    def _search_flights(self, filters: TravelFilters) -> list[FlightOption]:
        if filters.date_mode == "flexible":
            results: list[FlightOption] = []
            candidates = self._flexible_flight_requests(filters)
            logger.info(
                "travel.recommend.flexible_search origin=%s destination=%s candidates=%s window=%s",
                filters.origin or "SFO",
                filters.destination or "ANYWHERE",
                len(candidates),
                filters.flexible_window,
            )
            for search in candidates:
                logger.info(
                    "travel.recommend.search origin=%s destination=%s outbound_date=%s return_date=%s",
                    search.origin,
                    search.destination or "ANYWHERE",
                    search.outbound_date,
                    search.return_date,
                )
                results.extend(self.flights.search(search).results)
            return self._cheapest_per_destination(results)

        search = self._flight_request(filters)
        logger.info("travel.recommend.search origin=%s destination=%s", search.origin, search.destination or "ANYWHERE")
        return self.flights.search(search).results

    def _flight_request(self, filters: TravelFilters) -> FlightSearchRequest:
        return_date = filters.return_date
        if not return_date and filters.outbound_date and filters.trip_length_days:
            return_date = (date.fromisoformat(filters.outbound_date) + timedelta(days=filters.trip_length_days)).isoformat()
        return FlightSearchRequest(
            origin=filters.origin or "SFO",
            destination=filters.destination,
            outbound_date=filters.outbound_date or "",
            return_date=return_date or "",
            nonstop=filters.nonstop,
            include_details=True,
            details_limit=8,
        )

    def _flexible_flight_requests(self, filters: TravelFilters) -> list[FlightSearchRequest]:
        window_start = filters.flexible_window_start
        window_end = filters.flexible_window_end
        if not window_start or not window_end:
            window_start, window_end = flexible_window_bounds(filters.flexible_window)
        trip_length = filters.trip_length_days or 7
        start = date.fromisoformat(window_start)
        end = date.fromisoformat(window_end)
        latest_departure = max(start, end - timedelta(days=trip_length))

        max_requests = {"next_month": 4, "next_3_months": 5, "next_6_months": 6}.get(filters.flexible_window, 5)
        total_days = max((latest_departure - start).days, 0)
        step_days = max(7, round(total_days / max(max_requests - 1, 1))) if total_days else 7

        requests: list[FlightSearchRequest] = []
        current = start
        while current <= latest_departure and len(requests) < max_requests:
            requests.append(
                FlightSearchRequest(
                    origin=filters.origin or "SFO",
                    destination=filters.destination,
                    outbound_date=current.isoformat(),
                    return_date=(current + timedelta(days=trip_length)).isoformat(),
                    nonstop=filters.nonstop,
                    include_details=True,
                    details_limit=4,
                )
            )
            current += timedelta(days=step_days)

        if requests and requests[-1].outbound_date != latest_departure.isoformat() and len(requests) < max_requests:
            requests.append(
                FlightSearchRequest(
                    origin=filters.origin or "SFO",
                    destination=filters.destination,
                    outbound_date=latest_departure.isoformat(),
                    return_date=(latest_departure + timedelta(days=trip_length)).isoformat(),
                    nonstop=filters.nonstop,
                    include_details=True,
                    details_limit=4,
                )
            )
        return requests

    def _cheapest_per_destination(self, flights: list[FlightOption]) -> list[FlightOption]:
        cheapest: dict[str, FlightOption] = {}
        for index, flight in enumerate(flights):
            key = flight.dest or flight.option_token or flight.route_token or f"{flight.origin}-{flight.outbound_date}-{index}"
            existing = cheapest.get(key)
            if not existing:
                cheapest[key] = flight
                continue
            existing_price = existing.price if existing.price is not None else 10**9
            candidate_price = flight.price if flight.price is not None else 10**9
            if candidate_price < existing_price:
                cheapest[key] = flight
        return list(cheapest.values())

    def _clarifying_question(self, filters: TravelFilters) -> ClarifyingQuestion | None:
        if not filters.origin:
            return ClarifyingQuestion(field="origin", question="Where are you flying from?")
        if filters.date_mode == "flexible":
            if not filters.trip_length_days:
                return ClarifyingQuestion(field="dates", question="How many days should the trip be?")
            return None
        if not filters.outbound_date or not (filters.return_date or filters.trip_length_days):
            if filters.trip_length_days and not filters.outbound_date:
                return ClarifyingQuestion(field="dates", question=f"I have a {filters.trip_length_days}-day trip. Should I use next week, this weekend, or any dates that work?")
            return ClarifyingQuestion(field="dates", question="When do you want to go, and for how long?")
        return None

    def _rank(self, flights: list[FlightOption], filters: TravelFilters, intent: ExtractedIntent) -> list[RankedFlight]:
        ranked: list[RankedFlight] = []
        for index, flight in enumerate(flights):
            score = 50.0
            tags: list[str] = []
            if flight.price is not None and filters.budget_max:
                if flight.price <= filters.budget_max:
                    score += 20
                    tags.append("Under budget")
                else:
                    score -= min((flight.price - filters.budget_max) / 25, 25)
            if filters.nonstop is True and flight.stops == 0:
                score += 10
                tags.append("Nonstop")
            if filters.date_mode == "flexible":
                tags.append("Cheapest flexible date")
            if flight.duration_minutes and filters.max_flight_duration_minutes:
                if flight.duration_minutes <= filters.max_flight_duration_minutes:
                    score += 8
                    tags.append("Good flight time")
                else:
                    score -= 8
            if intent.surprise:
                score += max(0, 8 - index)
                tags.append("Surprise pick")
            weather_signal = self.weather.get_weather(flight.dest or "", filters)
            places_signal = self.places.get_places(flight.dest or "", filters)
            if filters.climates:
                weather_score = self._weather_score(weather_signal, filters)
                score += weather_score * 15
                if weather_score >= 0.7:
                    tags.append("Weather match")
            if filters.vibes:
                score += places_signal.score * 15
                if places_signal.matched_interests:
                    tags.extend([item.title() for item in places_signal.matched_interests[:2]])
            ranked.append(RankedFlight(flight=flight, score=round(max(score, 0), 2), tags=dedupe(tags)))
        sort = filters.sort
        if sort == "cheapest":
            return sorted(ranked, key=lambda item: item.flight.price if item.flight.price is not None else 10**9)
        if sort == "shortest_flight":
            return sorted(ranked, key=lambda item: item.flight.duration_minutes if item.flight.duration_minutes is not None else 10**9)
        if sort == "sunniest":
            return sorted(ranked, key=lambda item: self.weather.get_weather(item.flight.dest or "", filters).sunny_score, reverse=True)
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    def _recommendations(
        self,
        ranked: list[RankedFlight],
        filters: TravelFilters,
        intent: ExtractedIntent,
        *,
        relaxed: bool = False,
    ) -> list[DestinationRecommendation]:
        recommendations: list[DestinationRecommendation] = []
        for item in ranked[:8]:
            flight = item.flight
            weather = self.weather.get_weather(flight.dest or "", filters) if intent.requires_weather or filters.climates else None
            places = self.places.get_places(flight.dest or "", filters) if intent.requires_places or filters.vibes else None
            tags = item.tags if not relaxed or "Closest match" in item.tags else ["Closest match", *item.tags]
            recommendations.append(
                DestinationRecommendation(
                    destination=flight.dest,
                    destination_name=destination_name(flight.dest),
                    price=flight.price,
                    currency=flight.currency,
                    outbound_date=flight.outbound_date or filters.outbound_date,
                    return_date=flight.return_date or filters.return_date,
                    stops=flight.stops,
                    duration_minutes=flight.duration_minutes,
                    match_score=min(round(item.score / 100, 2), 1.0),
                    tags=tags,
                    why=self._why(flight, tags, weather, places),
                    weather=weather,
                    places=places,
                    flight=flight,
                )
            )
        return recommendations

    def _matching_recommendations(
        self,
        ranked: list[RankedFlight],
        filters: TravelFilters,
        intent: ExtractedIntent,
    ) -> list[DestinationRecommendation]:
        matched: list[RankedFlight] = []
        for item in ranked:
            weather = self.weather.get_weather(item.flight.dest or "", filters)
            places = self.places.get_places(item.flight.dest or "", filters)
            if self._matches_filters(item.flight, filters, weather, places):
                matched.append(item)
        return self._recommendations(matched, filters, intent)

    def _matches_filters(self, flight: FlightOption, filters: TravelFilters, weather, places) -> bool:
        if filters.budget_max is not None and (flight.price is None or flight.price > filters.budget_max):
            return False
        if filters.nonstop is True and flight.stops != 0:
            return False
        if filters.max_flight_duration_minutes is not None and (
            flight.duration_minutes is None or flight.duration_minutes > filters.max_flight_duration_minutes
        ):
            return False
        if filters.climates and self._weather_score(weather, filters) < 0.55:
            return False
        if filters.vibes and not places.matched_interests:
            return False
        return True

    def _fallback_options(
        self,
        ranked: list[RankedFlight],
        filters: TravelFilters,
        intent: ExtractedIntent,
    ) -> list[FallbackOption]:
        if not ranked:
            return []

        options: list[FallbackOption] = []
        seen_filters: set[str] = set()

        def add_option(label: str, fallback_filters: TravelFilters, assistant_message: str) -> None:
            key = fallback_filters.model_dump_json()
            if key in seen_filters:
                return
            recommendations = self._matching_recommendations(ranked, fallback_filters, intent)
            if not recommendations:
                return
            seen_filters.add(key)
            options.append(
                FallbackOption(
                    label=label,
                    assistant_message=assistant_message,
                    applied_filters=fallback_filters,
                    active_filters=self._active_chips(fallback_filters, {}),
                    recommendations=recommendations,
                )
            )

        if filters.budget_max is not None:
            budget_target = self._fallback_budget_target(ranked, filters)
            if budget_target is not None and budget_target > filters.budget_max:
                fallback_filters = filters.model_copy(update={"budget_max": budget_target})
                add_option(
                    f"Raise budget to ${budget_target}",
                    fallback_filters,
                    f"I couldn't find a match with your current budget, but I did verify options if we raise it to ${budget_target}.",
                )

        if filters.climates:
            fallback_filters = filters.model_copy(update={"climates": []})
            add_option(
                "Remove climate filter",
                fallback_filters,
                "I couldn't find a destination that matches the current weather filter, but I did verify options once I removed it.",
            )

        if filters.vibes:
            fallback_filters = filters.model_copy(update={"vibes": []})
            add_option(
                "Remove vibe filter",
                fallback_filters,
                "I couldn't find a destination that matches the current vibe filter, but I did verify options once I removed it.",
            )

        if filters.nonstop is True:
            fallback_filters = filters.model_copy(update={"nonstop": None})
            add_option(
                "Allow stops",
                fallback_filters,
                "I couldn't find nonstop matches, but I did verify options once I allowed flights with stops.",
            )

        if filters.max_flight_duration_minutes is not None:
            fallback_filters = filters.model_copy(update={"max_flight_duration_minutes": None})
            add_option(
                "Remove flight-time cap",
                fallback_filters,
                "I couldn't find matches within the current flight-time cap, but I did verify options once I removed it.",
            )

        return options[:3]

    def _fallback_budget_target(self, ranked: list[RankedFlight], filters: TravelFilters) -> int | None:
        relaxed_filters = filters.model_copy(update={"budget_max": None})
        candidate_prices: list[int] = []
        for item in ranked:
            if item.flight.price is None:
                continue
            weather = self.weather.get_weather(item.flight.dest or "", relaxed_filters)
            places = self.places.get_places(item.flight.dest or "", relaxed_filters)
            if self._matches_filters(item.flight, relaxed_filters, weather, places):
                candidate_prices.append(item.flight.price)
        return min(candidate_prices) if candidate_prices else None

    def _weather_score(self, weather, filters: TravelFilters) -> float:
        scores: list[float] = []
        for climate in filters.climates:
            if climate in ("sunny", "tropical"):
                scores.append(weather.sunny_score)
            elif climate == "warm":
                scores.append(weather.warm_score)
            elif climate == "not_rainy":
                scores.append(1 - weather.rainy_risk)
            else:
                scores.append(0.5)
        return sum(scores) / len(scores) if scores else 0.5

    def _why(self, flight: FlightOption, tags: list[str], weather, places) -> str:
        bits = []
        if flight.price is not None:
            bits.append(f"${flight.price}")
        if tags:
            bits.append(", ".join(tags[:3]).lower())
        if weather:
            bits.append(weather.summary)
        if places and places.matched_interests:
            bits.append(places.summary)
        return "This fits because " + "; ".join(bits) + "." if bits else "This destination is a solid match for the current filters."

    def _assistant_message(
        self,
        recommendations: list[DestinationRecommendation],
        filters: TravelFilters,
        fallback_options: list[FallbackOption],
        *,
        relaxed: bool = False,
    ) -> str:
        if not recommendations:
            if fallback_options:
                suggestions = ", or ".join(option.label.lower() for option in fallback_options[:2])
                return (
                    "I couldn't find an exact match for every filter. "
                    f"I already verified fallback options that do work: {suggestions}."
                )
            return "I could not find matching flights for those filters. Try a higher budget, broader dates, or Anywhere."
        top = recommendations[0]
        price = f" around ${top.price}" if top.price is not None else ""
        if relaxed:
            return (
                "I couldn't satisfy every filter exactly, but I found "
                f"{len(recommendations)} close matches. My best broader match is "
                f"{top.destination_name or top.destination}{price}."
            )
        return f"I found {len(recommendations)} options. My top pick is {top.destination_name or top.destination}{price}."

    def _active_chips(self, filters: TravelFilters, sources: dict[str, str]) -> list[ActiveFilterChip]:
        chips: list[ActiveFilterChip] = []
        labels = {
            "origin": "From",
            "destination": "To",
            "date_mode": "Dates",
            "outbound_date": "Depart",
            "return_date": "Return",
            "trip_length_days": "Length",
            "flexible_window": "Window",
            "budget_max": "Budget",
            "nonstop": "Stops",
            "domestic_international": "Region",
            "climates": "Climate",
            "vibes": "Vibe",
            "sort": "Sort",
        }
        for key, value in filters.model_dump().items():
            if value in (None, "", [], "any", "best_match", "exact"):
                continue
            if key in ("flexible_window_start", "flexible_window_end"):
                continue
            if filters.date_mode == "flexible" and key in ("outbound_date", "return_date"):
                continue
            display = (
                f"${value}"
                if key == "budget_max"
                else f"{value} days"
                if key == "trip_length_days"
                else "Flexible"
                if key == "date_mode" and value == "flexible"
                else flexible_window_label(str(value))
                if key == "flexible_window"
                else ", ".join(value)
                if isinstance(value, list)
                else str(value)
            )
            chips.append(
                ActiveFilterChip(
                    key=key,
                    label=labels.get(key, key.replace("_", " ").title()),
                    value=display,
                    source=sources.get(key, "user"),  # type: ignore[arg-type]
                )
            )
        return chips


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def flexible_window_label(value: str) -> str:
    return {
        "next_month": "Next month",
        "next_3_months": "Next 3 months",
        "next_6_months": "Next 6 months",
    }.get(value, value.replace("_", " ").title())

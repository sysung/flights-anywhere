from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from typing import Any

from api.travel.config import AIConfig, load_ai_config
from api.travel.models import ExtractedIntent, FlexibleWindow, TravelFilters

logger = logging.getLogger(__name__)


class AIUnavailableError(RuntimeError):
    """Raised when model-backed interpretation is required but unavailable."""


IATA_RE = re.compile(r"\b[A-Z]{3}\b")
BUDGET_RE = re.compile(r"(?:under|below|less than|<=?|budget(?: of)?|around)?\s*\$?\s*(\d{2,5})", re.IGNORECASE)

CLIMATE_KEYWORDS = {
    "sunny": ("sunny", True),
    "sun": ("sunny", True),
    "warm": ("warm", True),
    "tropical": ("tropical", True),
    "beach": ("tropical", True),
    "snow": ("snowy", True),
    "cold": ("snowy", True),
    "mild": ("mild", True),
    "not rainy": ("not_rainy", True),
    "no rain": ("not_rainy", True),
}

VIBE_KEYWORDS = {
    "japanese temple": "temples",
    "temple": "temples",
    "shrine": "temples",
    "food": "food",
    "restaurant": "food",
    "nightlife": "nightlife",
    "museum": "museums",
    "culture": "culture",
    "romantic": "romantic",
    "family": "family",
    "adventure": "adventure",
    "nature": "nature",
    "luxury": "luxury",
    "budget": "budget",
    "beach": "beaches",
}


class TravelIntentExtractor:
    def __init__(self, config: AIConfig | None = None) -> None:
        self.config = config or load_ai_config()

    def extract(self, message: str, current_filters: TravelFilters | None = None) -> ExtractedIntent:
        current = current_filters or TravelFilters()
        heuristic = self._heuristic_extract(message, current)
        if self._is_good_enough(heuristic, message):
            return heuristic
        if not self.config.google_api_key:
            raise AIUnavailableError("GOOGLE_CLOUD_API_KEY is required for AI travel intent extraction.")
        model_intent = self._extract_with_gemini(message, current)
        return merge_intent(heuristic, model_intent)

    def _heuristic_extract(self, message: str, current_filters: TravelFilters | None = None) -> ExtractedIntent:
        text = message.strip()
        lower = text.lower()
        current_filters = current_filters or TravelFilters()
        filters = TravelFilters()
        sources: dict[str, str] = {}
        confidence = 0.45
        requires_weather = False
        requires_places = False

        codes = IATA_RE.findall(text)
        if codes:
            filters.origin = codes[0]
            sources["origin"] = "user"
            confidence += 0.1
            if len(codes) > 1:
                filters.destination = codes[1]
                sources["destination"] = "user"

        budget = self._extract_budget(lower)
        if budget:
            filters.budget_max = budget
            sources["budget_max"] = "user"
            confidence += 0.1

        trip_length_days = extract_trip_length_days(lower)
        if trip_length_days:
            filters.trip_length_days = trip_length_days
            sources["trip_length_days"] = "user"
            confidence += 0.08

        flexible_window = extract_flexible_window(lower)
        if wants_flexible_dates(lower):
            filters.date_mode = "flexible"
            filters.flexible_window = flexible_window
            sources["date_mode"] = "ai"
            sources["flexible_window"] = "ai"
            filters.trip_length_days = trip_length_days or current_filters.trip_length_days or 7
            sources["trip_length_days"] = sources.get("trip_length_days", "default")
            confidence += 0.12

        if "nonstop" in lower or "direct flight" in lower:
            filters.nonstop = True
            sources["nonstop"] = "user"
        elif "one stop" in lower:
            filters.nonstop = False
            sources["nonstop"] = "user"

        date_window = None if filters.date_mode == "flexible" else flexible_date_window(lower, trip_length_days or current_filters.trip_length_days)
        if date_window:
            filters.outbound_date = date_window[0]
            filters.return_date = date_window[1]
            sources["outbound_date"] = "ai"
            sources["return_date"] = "ai"
            confidence += 0.15

        climates: list[str] = []
        for keyword, (climate, uses_weather) in CLIMATE_KEYWORDS.items():
            if keyword in lower and climate not in climates:
                climates.append(climate)
                requires_weather = requires_weather or uses_weather
        if climates:
            filters.climates = climates
            sources["climates"] = "user"
            confidence += 0.1

        vibes: list[str] = []
        for keyword, vibe in VIBE_KEYWORDS.items():
            if keyword in lower and vibe not in vibes:
                vibes.append(vibe)
                requires_places = True
        if vibes:
            filters.vibes = vibes
            sources["vibes"] = "user"
            confidence += 0.1

        if "domestic" in lower:
            filters.domestic_international = "domestic"
            sources["domestic_international"] = "user"
        elif "international" in lower or "passport" in lower:
            filters.domestic_international = "international"
            sources["domestic_international"] = "user"

        if "cheapest" in lower:
            filters.sort = "cheapest"
            sources["sort"] = "user"
            if not filters.date_mode == "flexible" and any(phrase in lower for phrase in ("any", "anytime", "whenever", "flexible", "sometime")):
                filters.date_mode = "flexible"
                filters.flexible_window = flexible_window
                filters.trip_length_days = trip_length_days or current_filters.trip_length_days or 7
                sources["date_mode"] = "ai"
                sources["flexible_window"] = "ai"
        elif "shortest" in lower:
            filters.sort = "shortest_flight"
            sources["sort"] = "user"
        elif "sunniest" in lower or "most sun" in lower:
            filters.sort = "sunniest"
            sources["sort"] = "ai"

        surprise = any(phrase in lower for phrase in ("surprise me", "anywhere", "where to next", "pick for me"))
        if surprise:
            filters.destination = None
            sources["destination"] = "ai"
            confidence += 0.1

        return ExtractedIntent(
            filters=filters,
            surprise=surprise,
            requires_weather=requires_weather,
            requires_places=requires_places,
            confidence=min(confidence, 0.95),
            sources=sources,  # type: ignore[arg-type]
        )

    def _extract_budget(self, lower: str) -> int | None:
        for match in BUDGET_RE.finditer(lower):
            value = int(match.group(1))
            if value >= 100:
                return value
        return None

    def _is_good_enough(self, intent: ExtractedIntent, message: str) -> bool:
        lower = message.lower()
        if intent.filters.outbound_date or intent.filters.return_date or intent.filters.trip_length_days:
            return True
        if intent.filters.date_mode == "flexible":
            return True
        if intent.surprise or intent.filters.budget_max or intent.filters.climates or intent.filters.vibes:
            return True
        simple_words = {"hi", "hello", "hey", "where to next", "surprise me"}
        return lower.strip() in simple_words

    def _extract_with_gemini(self, message: str, current_filters: TravelFilters) -> ExtractedIntent:
        try:
            import google.generativeai as genai
        except ModuleNotFoundError as exc:
            raise AIUnavailableError("google-generativeai is required for Gemini travel intent extraction.") from exc

        genai.configure(api_key=self.config.google_api_key)
        model = genai.GenerativeModel(self.config.gemini_model)
        prompt = (
            "Extract travel search intent as strict JSON matching these keys: "
            "origin, destination, date_mode, outbound_date, return_date, trip_length_days, "
            "flexible_window, flexible_window_start, flexible_window_end, budget_max, "
            "nonstop, max_flight_duration_minutes, domestic_international, climates, vibes, sort, "
            "surprise, requires_weather, requires_places, confidence. "
            "Use null when unknown. Do not invent flight facts.\n"
            f"Current filters: {current_filters.model_dump_json()}\n"
            f"User message: {message}"
        )
        response = model.generate_content(prompt)
        text = getattr(response, "text", "") or ""
        raw = self._json_from_text(text)
        filters = TravelFilters(
            origin=raw.get("origin"),
            destination=raw.get("destination"),
            date_mode=raw.get("date_mode") or "exact",
            outbound_date=raw.get("outbound_date"),
            return_date=raw.get("return_date"),
            trip_length_days=raw.get("trip_length_days"),
            flexible_window=raw.get("flexible_window") or "next_3_months",
            flexible_window_start=raw.get("flexible_window_start"),
            flexible_window_end=raw.get("flexible_window_end"),
            budget_max=raw.get("budget_max"),
            nonstop=raw.get("nonstop"),
            max_flight_duration_minutes=raw.get("max_flight_duration_minutes"),
            domestic_international=raw.get("domestic_international") or "any",
            climates=raw.get("climates") or [],
            vibes=raw.get("vibes") or [],
            sort=raw.get("sort") or "best_match",
        )
        return ExtractedIntent(
            filters=filters,
            surprise=bool(raw.get("surprise")),
            requires_weather=bool(raw.get("requires_weather")),
            requires_places=bool(raw.get("requires_places")),
            confidence=float(raw.get("confidence") or 0.65),
            sources={key: "ai" for key, value in filters.model_dump().items() if value not in (None, [], "any", "best_match")},
        )

    def _json_from_text(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)


def merge_intent(primary: ExtractedIntent, secondary: ExtractedIntent) -> ExtractedIntent:
    merged_filters = merge_filters(primary.filters, secondary.filters)
    sources = dict(secondary.sources)
    sources.update(primary.sources)
    return ExtractedIntent(
        filters=merged_filters,
        surprise=primary.surprise or secondary.surprise,
        requires_weather=primary.requires_weather or secondary.requires_weather,
        requires_places=primary.requires_places or secondary.requires_places,
        confidence=max(primary.confidence, secondary.confidence),
        sources=sources,
    )


def merge_filters(base: TravelFilters, update: TravelFilters) -> TravelFilters:
    values = base.model_dump()
    for key, value in update.model_dump().items():
        if value not in (None, "", [], "any", "best_match", "exact", "next_3_months"):
            values[key] = value
    if update.date_mode != "exact":
        values["date_mode"] = update.date_mode
    if update.flexible_window != "next_3_months":
        values["flexible_window"] = update.flexible_window
    if update.domestic_international != "any":
        values["domestic_international"] = update.domestic_international
    if update.sort != "best_match":
        values["sort"] = update.sort
    normalize_flexible_dates(values)
    return TravelFilters(**values)


def normalize_flexible_dates(values: dict[str, Any], today: date | None = None) -> None:
    trip_length = values.get("trip_length_days")
    outbound = values.get("outbound_date")
    return_date = values.get("return_date")

    if isinstance(outbound, str) and outbound and not is_iso_date(outbound):
        window = flexible_date_window(outbound, trip_length, today=today)
        if window:
            values["outbound_date"] = window[0]
            if not is_iso_date(str(return_date or "")):
                values["return_date"] = window[1]
        else:
            values["outbound_date"] = None

    if isinstance(return_date, str) and return_date and not is_iso_date(return_date):
        window = flexible_date_window(return_date, trip_length, today=today)
        values["return_date"] = window[1] if window else None

    if values.get("outbound_date") and not values.get("return_date") and trip_length:
        values["return_date"] = (date.fromisoformat(values["outbound_date"]) + timedelta(days=int(trip_length))).isoformat()

    if values.get("date_mode") == "flexible":
        values["trip_length_days"] = int(values.get("trip_length_days") or 7)
        window_start, window_end = flexible_window_bounds(values.get("flexible_window") or "next_3_months", today=today)
        values["flexible_window_start"] = values.get("flexible_window_start") or window_start
        values["flexible_window_end"] = values.get("flexible_window_end") or window_end


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def extract_trip_length_days(lower: str) -> int | None:
    trip_length = re.search(r"\b(\d{1,2})\s*(?:day|days|night|nights)\b", lower)
    if trip_length:
        return int(trip_length.group(1))
    if re.search(r"\b(?:for\s+)?(?:a|one|1)\s+week\b", lower):
        return 7
    two_week = re.search(r"\b(?:for\s+)?(?:two|2)\s+weeks\b", lower)
    if two_week:
        return 14
    weekend = re.search(r"\b(?:weekend|getaway)\b", lower)
    if weekend:
        return 3
    return None


def flexible_date_window(lower: str, trip_length_days: int | None = None, today: date | None = None) -> tuple[str, str] | None:
    length = trip_length_days or 7
    if "next week" in lower:
        outbound, _inbound = next_week_dates(today=today, trip_length_days=length)
        return outbound, (date.fromisoformat(outbound) + timedelta(days=length)).isoformat()
    if "this weekend" in lower or "next weekend" in lower:
        return weekend_dates(today=today, next_weekend="next weekend" in lower, trip_length_days=length)
    flexible_phrases = (
        "any date",
        "any dates",
        "choose a date",
        "choose any date",
        "pick a date",
        "pick dates",
        "whatever date",
        "whenever",
        "flexible",
        "up to you",
        "for me",
    )
    if any(phrase in lower for phrase in flexible_phrases):
        outbound, _inbound = next_week_dates(today=today, trip_length_days=length)
        return outbound, (date.fromisoformat(outbound) + timedelta(days=length)).isoformat()
    return None


def wants_flexible_dates(lower: str) -> bool:
    phrases = (
        "any date",
        "any dates",
        "anytime",
        "any time",
        "whenever",
        "flexible",
        "cheapest date",
        "cheapest dates",
        "cheapest flight",
        "cheapest trip",
        "sometime this month",
        "sometime next month",
        "sometime in the next",
    )
    return any(phrase in lower for phrase in phrases)


def extract_flexible_window(lower: str) -> FlexibleWindow:
    if "next 6 month" in lower or "six month" in lower or "this year" in lower:
        return "next_6_months"
    if "next month" in lower or "this month" in lower or "next 30" in lower:
        return "next_month"
    return "next_3_months"


def flexible_window_bounds(window: str, today: date | None = None) -> tuple[str, str]:
    base = today or date.today()
    days = {"next_month": 30, "next_3_months": 90, "next_6_months": 180}.get(window, 90)
    return (base + timedelta(days=7)).isoformat(), (base + timedelta(days=days)).isoformat()


def weekend_dates(today: date | None = None, *, next_weekend: bool = False, trip_length_days: int = 3) -> tuple[str, str]:
    base = today or date.today()
    days_until_saturday = (5 - base.weekday()) % 7
    if days_until_saturday == 0 or next_weekend:
        days_until_saturday += 7
    outbound = base + timedelta(days=days_until_saturday)
    return outbound.isoformat(), (outbound + timedelta(days=trip_length_days)).isoformat()


def next_week_dates(today: date | None = None, trip_length_days: int = 4) -> tuple[str, str]:
    base = today or date.today()
    days_until_next_monday = (7 - base.weekday()) % 7 or 7
    outbound = base + timedelta(days=days_until_next_monday)
    inbound = outbound + timedelta(days=trip_length_days)
    return outbound.isoformat(), inbound.isoformat()

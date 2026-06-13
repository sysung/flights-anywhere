from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from api.google_flights.models import FlightOption


FilterSource = Literal["user", "ai", "default"]
SortMode = Literal["best_match", "cheapest", "shortest_flight", "sunniest", "most_surprising"]
DateMode = Literal["exact", "flexible"]
FlexibleWindow = Literal["next_month", "next_3_months", "next_6_months"]


class FilterValue(BaseModel):
    value: Any
    source: FilterSource = "user"
    confidence: float = 1.0


class TravelFilters(BaseModel):
    origin: str | None = None
    destination: str | None = None
    date_mode: DateMode = "exact"
    outbound_date: str | None = None
    return_date: str | None = None
    trip_length_days: int | None = None
    flexible_window: FlexibleWindow = "next_3_months"
    flexible_window_start: str | None = None
    flexible_window_end: str | None = None
    budget_max: int | None = None
    nonstop: bool | None = None
    max_flight_duration_minutes: int | None = None
    domestic_international: Literal["any", "domestic", "international"] = "any"
    climates: list[str] = Field(default_factory=list)
    vibes: list[str] = Field(default_factory=list)
    sort: SortMode = "best_match"


class ExtractedIntent(BaseModel):
    filters: TravelFilters = Field(default_factory=TravelFilters)
    surprise: bool = False
    requires_weather: bool = False
    requires_places: bool = False
    confidence: float = 0.6
    sources: dict[str, FilterSource] = Field(default_factory=dict)


class ActiveFilterChip(BaseModel):
    key: str
    label: str
    value: str
    source: FilterSource = "user"


class FilterAction(BaseModel):
    action: Literal["set_filter", "clear_filter", "run_search", "ask_clarifying_question"]
    key: str | None = None
    value: Any = None


class ClarifyingQuestion(BaseModel):
    field: Literal["origin", "dates"]
    question: str


class WeatherSignal(BaseModel):
    summary: str
    sunny_score: float = 0.5
    warm_score: float = 0.5
    rainy_risk: float = 0.5


class PlacesSignal(BaseModel):
    summary: str
    matched_interests: list[str] = Field(default_factory=list)
    score: float = 0.5


class DestinationRecommendation(BaseModel):
    destination: str | None = None
    destination_name: str | None = None
    price: int | None = None
    currency: str = "USD"
    outbound_date: str | None = None
    return_date: str | None = None
    stops: int | None = None
    duration_minutes: int | None = None
    match_score: float
    tags: list[str] = Field(default_factory=list)
    why: str
    weather: WeatherSignal | None = None
    places: PlacesSignal | None = None
    flight: FlightOption


class RecommendationRequest(BaseModel):
    message: str
    filters: TravelFilters = Field(default_factory=TravelFilters)
    conversation_id: str | None = None


class FallbackOption(BaseModel):
    label: str
    assistant_message: str
    applied_filters: TravelFilters
    active_filters: list[ActiveFilterChip] = Field(default_factory=list)
    recommendations: list[DestinationRecommendation] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    assistant_message: str
    applied_filters: TravelFilters
    active_filters: list[ActiveFilterChip] = Field(default_factory=list)
    actions: list[FilterAction] = Field(default_factory=list)
    recommendations: list[DestinationRecommendation] = Field(default_factory=list)
    fallback_options: list[FallbackOption] = Field(default_factory=list)
    clarifying_question: ClarifyingQuestion | None = None


class FilterParseRequest(BaseModel):
    message: str
    filters: TravelFilters = Field(default_factory=TravelFilters)


class FilterParseResponse(BaseModel):
    intent: ExtractedIntent
    applied_filters: TravelFilters
    active_filters: list[ActiveFilterChip] = Field(default_factory=list)
    clarifying_question: ClarifyingQuestion | None = None

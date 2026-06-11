from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FlightSearchRequest(BaseModel):
    origin: str = "SFO"
    destination: str | None = None
    outbound_date: str
    return_date: str
    nonstop: bool | None = None
    include_details: bool = False
    details_limit: int = 10


class FlightOption(BaseModel):
    id: str | None = None
    source: Literal["explore", "shopping", "booking"]
    selection_stage: Literal["destination", "outbound", "return", "booking"]
    origin: str | None = None
    dest: str | None = None
    outbound_date: str | None = None
    return_date: str | None = None
    date: str | None = None
    price: int | None = None
    price_delta: int | None = None
    currency: str = "USD"
    airline_code: str | None = None
    airline: str | None = None
    stops: int | None = None
    duration_minutes: int | None = None
    flight_num: str | None = None
    flight_nums: list[str] = Field(default_factory=list)
    route_token: str | None = None
    option_token: str | None = None
    outbound_options: list[dict[str, Any]] = Field(default_factory=list)
    return_options: list[dict[str, Any]] = Field(default_factory=list)
    booking_options: list[dict[str, Any]] = Field(default_factory=list)
    workflow_state: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    mode: Literal["explore", "shopping", "booking"]
    selection_stage: Literal["results", "destination", "outbound", "return", "booking"]
    query: dict[str, Any]
    results: list[FlightOption]
    workflow_state: dict[str, Any] = Field(default_factory=dict)

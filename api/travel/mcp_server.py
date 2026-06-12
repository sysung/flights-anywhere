from __future__ import annotations

from typing import Any

from api.google_flights.models import FlightSearchRequest
from api.google_flights.service import GoogleFlightsService
from api.travel.models import FilterParseRequest, RecommendationRequest, TravelFilters
from api.travel.service import TravelRecommendationService


def parse_travel_intent_tool(payload: dict[str, Any], service: TravelRecommendationService | None = None) -> dict[str, Any]:
    svc = service or TravelRecommendationService()
    request = FilterParseRequest(message=payload.get("message", ""), filters=TravelFilters(**payload.get("filters", {})))
    return svc.parse_filters(request).model_dump()


def search_flights_tool(payload: dict[str, Any], flights: GoogleFlightsService | None = None) -> dict[str, Any]:
    svc = flights or GoogleFlightsService()
    response = svc.search(FlightSearchRequest(**payload))
    return response.model_dump()


def explore_destinations_tool(payload: dict[str, Any], flights: GoogleFlightsService | None = None) -> dict[str, Any]:
    data = dict(payload)
    data["destination"] = None
    return search_flights_tool(data, flights=flights)


def rank_destinations_tool(payload: dict[str, Any], service: TravelRecommendationService | None = None) -> dict[str, Any]:
    svc = service or TravelRecommendationService()
    request = RecommendationRequest(message=payload.get("message", "Rank these destinations"), filters=TravelFilters(**payload.get("filters", {})))
    return svc.recommend(request).model_dump()


def recommend_destinations_tool(payload: dict[str, Any], service: TravelRecommendationService | None = None) -> dict[str, Any]:
    svc = service or TravelRecommendationService()
    request = RecommendationRequest(message=payload.get("message", ""), filters=TravelFilters(**payload.get("filters", {})))
    return svc.recommend(request).model_dump()


def create_mcp_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install the mcp package to run the travel MCP server.") from exc

    mcp = FastMCP("flights-anywhere")

    @mcp.tool()
    def parse_travel_intent(payload: dict[str, Any]) -> dict[str, Any]:
        return parse_travel_intent_tool(payload)

    @mcp.tool()
    def search_flights(payload: dict[str, Any]) -> dict[str, Any]:
        return search_flights_tool(payload)

    @mcp.tool()
    def explore_destinations(payload: dict[str, Any]) -> dict[str, Any]:
        return explore_destinations_tool(payload)

    @mcp.tool()
    def rank_destinations(payload: dict[str, Any]) -> dict[str, Any]:
        return rank_destinations_tool(payload)

    @mcp.tool()
    def recommend_destinations(payload: dict[str, Any]) -> dict[str, Any]:
        return recommend_destinations_tool(payload)

    return mcp


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()


import type { FlightSearchRequest, FlightSearchResponse, RecommendationResponse, TravelFilters } from "./types";

export async function recommendTravel(message: string, filters: TravelFilters): Promise<RecommendationResponse> {
  const response = await fetch("/api/travel/recommend", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, filters })
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(errorMessage(detail) || `Recommendation request failed with ${response.status}`);
  }
  return response.json();
}

export async function searchFlights(request: FlightSearchRequest): Promise<FlightSearchResponse> {
  const response = await fetch("/api/flights/search", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(errorMessage(detail) || `Flight search failed with ${response.status}`);
  }
  return response.json();
}

function errorMessage(detail: string): string {
  try {
    const parsed = JSON.parse(detail) as { detail?: unknown };
    return typeof parsed.detail === "string" ? parsed.detail : detail;
  } catch {
    return detail;
  }
}

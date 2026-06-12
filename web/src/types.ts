export type SortMode = "best_match" | "cheapest" | "shortest_flight" | "sunniest" | "most_surprising";
export type DateMode = "exact" | "flexible";
export type FlexibleWindow = "next_month" | "next_3_months" | "next_6_months";

export interface TravelFilters {
  origin?: string | null;
  destination?: string | null;
  date_mode: DateMode;
  outbound_date?: string | null;
  return_date?: string | null;
  trip_length_days?: number | null;
  flexible_window: FlexibleWindow;
  flexible_window_start?: string | null;
  flexible_window_end?: string | null;
  budget_max?: number | null;
  nonstop?: boolean | null;
  max_flight_duration_minutes?: number | null;
  domestic_international: "any" | "domestic" | "international";
  climates: string[];
  vibes: string[];
  sort: SortMode;
}

export interface ActiveFilterChip {
  key: string;
  label: string;
  value: string;
  source: "user" | "ai" | "default";
}

export interface Recommendation {
  destination?: string | null;
  destination_name?: string | null;
  price?: number | null;
  currency: string;
  outbound_date?: string | null;
  return_date?: string | null;
  stops?: number | null;
  duration_minutes?: number | null;
  match_score: number;
  tags: string[];
  why: string;
  weather?: { summary: string } | null;
  places?: { summary: string; matched_interests: string[] } | null;
  flight?: FlightOption | null;
}

export interface RecommendationResponse {
  assistant_message: string;
  applied_filters: TravelFilters;
  active_filters: ActiveFilterChip[];
  recommendations: Recommendation[];
  clarifying_question?: { field: string; question: string } | null;
}

export interface FlightSearchRequest {
  origin: string;
  destination?: string | null;
  outbound_date: string;
  return_date: string;
  nonstop?: boolean | null;
  include_details?: boolean;
  details_limit?: number;
}

export interface FlightOption {
  id?: string | null;
  source: "explore" | "shopping" | "booking";
  selection_stage: "destination" | "outbound" | "return" | "booking";
  origin?: string | null;
  dest?: string | null;
  outbound_date?: string | null;
  return_date?: string | null;
  date?: string | null;
  price?: number | null;
  price_delta?: number | null;
  currency: string;
  airline_code?: string | null;
  airline?: string | null;
  stops?: number | null;
  duration_minutes?: number | null;
  flight_num?: string | null;
  flight_nums: string[];
  route_token?: string | null;
  option_token?: string | null;
  outbound_options: Record<string, unknown>[];
  return_options: Record<string, unknown>[];
  booking_options: Record<string, unknown>[];
  workflow_state: Record<string, unknown>;
  raw?: Record<string, unknown> | null;
}

export interface FlightSearchResponse {
  mode: "explore" | "shopping" | "booking";
  selection_stage: "results" | "destination" | "outbound" | "return" | "booking";
  query: Record<string, unknown>;
  results: FlightOption[];
  workflow_state: Record<string, unknown>;
}

export const defaultFilters: TravelFilters = {
  origin: "SFO",
  destination: null,
  date_mode: "exact",
  outbound_date: "",
  return_date: "",
  trip_length_days: null,
  flexible_window: "next_3_months",
  flexible_window_start: null,
  flexible_window_end: null,
  budget_max: 1000,
  nonstop: null,
  max_flight_duration_minutes: null,
  domestic_international: "any",
  climates: [],
  vibes: [],
  sort: "best_match"
};

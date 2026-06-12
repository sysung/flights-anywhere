from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANYWHERE_ID = "/m/02j71"
ENTITY_CACHE_PATH = ROOT / "data" / "google_flights_entities.json"
DEFAULT_SESSION_PATH = ROOT / "api" / ".session" / "google_flights_session.json"
JSON_PREFIX = ")]}'"
SERVICE_MARKER = "/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/"

RPC_EXPLORE = "GetExploreDestinations"
RPC_EXPLORE_DETAILS = "GetExploreDestinationFlightDetails"
RPC_SHOPPING = "GetShoppingResults"
RPC_BOOKING = "GetBookingResults"

from __future__ import annotations

import logging
import os

import httpx
from fastapi import FastAPI, HTTPException

from api.google_flights.models import FlightSearchRequest, SearchResponse
from api.google_flights.service import GoogleFlightsService


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Google Flights API")
service = GoogleFlightsService()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/flights/search", response_model=SearchResponse)
def search_flights(request: FlightSearchRequest) -> SearchResponse:
    logger.info("api.search.request origin=%s destination=%s", request.origin, request.destination or "ANYWHERE")
    try:
        response = service.search(request)
        logger.info("api.search.response mode=%s count=%s", response.mode, len(response.results))
        return response
    except (FileNotFoundError, RuntimeError, TimeoutError, httpx.HTTPError) as exc:
        logger.exception("api.search.unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        logger.exception("api.search.bad_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("api.search.unhandled")
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc

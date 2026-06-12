from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from api.google_flights.models import FlightSearchRequest, SearchResponse
from api.google_flights.service import GoogleFlightsService
from api.travel.intent import AIUnavailableError
from api.travel.models import FilterParseRequest, FilterParseResponse, RecommendationRequest, RecommendationResponse
from api.travel.service import TravelRecommendationService


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Google Flights API")
service = GoogleFlightsService()
travel_service = TravelRecommendationService(flights=service)
WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"


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


@app.post("/api/travel/filters/parse", response_model=FilterParseResponse)
def parse_travel_filters(request: FilterParseRequest) -> FilterParseResponse:
    logger.info("api.travel.parse.request message_len=%s", len(request.message))
    try:
        return travel_service.parse_filters(request)
    except AIUnavailableError as exc:
        logger.exception("api.travel.parse.ai_unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        logger.exception("api.travel.parse.bad_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("api.travel.parse.unhandled")
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@app.post("/api/travel/recommend", response_model=RecommendationResponse)
def recommend_travel(request: RecommendationRequest) -> RecommendationResponse:
    logger.info("api.travel.recommend.request message_len=%s", len(request.message))
    try:
        response = travel_service.recommend(request)
        logger.info("api.travel.recommend.response count=%s", len(response.recommendations))
        return response
    except AIUnavailableError as exc:
        logger.exception("api.travel.recommend.ai_unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (FileNotFoundError, RuntimeError, TimeoutError, httpx.HTTPError) as exc:
        logger.exception("api.travel.recommend.unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        logger.exception("api.travel.recommend.bad_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("api.travel.recommend.unhandled")
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

from __future__ import annotations

import logging

import httpx

from api.google_flights.builders import explore_details_request, explore_request, shopping_request
from api.google_flights.codec import decode_f_req, parse_rpc_response
from api.google_flights.constants import RPC_EXPLORE, RPC_EXPLORE_DETAILS, RPC_SHOPPING
from api.google_flights.entities import Place, load_entities, resolve_place
from api.google_flights.models import FlightSearchRequest, SearchResponse
from api.google_flights.parsers import attach_details, parse_explore, parse_flight_options
from api.google_flights.session import SessionManager
from api.google_flights.transport import post, with_rpc

logger = logging.getLogger(__name__)


class GoogleFlightsService:
    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self.sessions = session_manager or SessionManager()

    def search(self, query: FlightSearchRequest) -> SearchResponse:
        try:
            return self._search_once(query, refresh=False)
        except (httpx.HTTPError, TimeoutError, RuntimeError, ValueError) as exc:
            logger.warning("google_flights.search.retry_after_failure error=%s", exc)
            if "session f.req" not in str(exc) and isinstance(exc, ValueError):
                raise
            self.sessions.invalidate()
            return self._search_once(query, refresh=True)

    def _search_once(self, query: FlightSearchRequest, *, refresh: bool) -> SearchResponse:
        session = self.sessions.refresh() if refresh else self.sessions.get()
        _outer, inner, form = decode_f_req(session.data)
        entities = load_entities()
        origin = resolve_place(query.origin, entities)
        dest = resolve_place(query.destination, entities, anywhere=True)
        mode = "explore" if dest.code == "ANYWHERE" else "shopping"
        logger.info(
            "google_flights.search.start mode=%s origin=%s destination=%s outbound_date=%s return_date=%s refresh=%s",
            mode,
            origin.code,
            dest.code,
            query.outbound_date,
            query.return_date,
            refresh,
        )

        if mode == "explore":
            data = explore_request(inner, form, query, origin, dest)
            results = parse_explore(parse_rpc_response(post(with_rpc(session, RPC_EXPLORE), data)), query)
            logger.info("google_flights.search.parsed rpc=%s count=%s", RPC_EXPLORE, len(results))
            if query.include_details:
                self._enrich_explore(session, inner, form, query, origin, results)
            stage = "results"
        else:
            data = shopping_request(inner, form, query, origin, dest)
            results = parse_flight_options(parse_rpc_response(post(with_rpc(session, RPC_SHOPPING), data)), query, source="shopping", stage="outbound")
            logger.info("google_flights.search.parsed rpc=%s count=%s", RPC_SHOPPING, len(results))
            stage = "outbound"

        logger.info("google_flights.search.done mode=%s stage=%s count=%s", mode, stage, len(results))
        return SearchResponse(
            mode=mode,
            selection_stage=stage,
            query=query.model_dump(),
            results=results,
            workflow_state={"mode": mode, "can_select_outbound": mode == "shopping", "can_book": False},
        )

    def _enrich_explore(self, session, inner, form, query, origin: Place, results) -> None:
        selected = results if query.details_limit == 0 else results[: max(query.details_limit, 0)]
        logger.info("google_flights.details.start selected=%s total=%s", len(selected), len(results))
        for result in selected:
            if not result.dest or not result.route_token or not result.raw:
                logger.info("google_flights.details.skip dest=%s reason=missing_token_or_raw", result.dest)
                continue
            dest = Place(result.dest, result.raw["destination_entity_id"], type=4)
            data = explore_details_request(inner, form, query, origin, dest, result.route_token)
            details = parse_flight_options(
                parse_rpc_response(post(with_rpc(session, RPC_EXPLORE_DETAILS), data)),
                query,
                source="explore",
                stage="outbound",
            )
            attach_details(result, details)
            logger.info("google_flights.details.parsed dest=%s count=%s", result.dest, len(details))

from __future__ import annotations

import base64
import re
from typing import Any

from api.google_flights.codec import walk
from api.google_flights.models import FlightOption


def parse_explore(parsed: list[Any], query: Any) -> list[FlightOption]:
    rows = []
    seen = set()
    for path, row in walk(parsed):
        if not _is_explore_row(row):
            continue
        price, token = row[1][0][1], row[1][1]
        airline = row[6]
        key = (airline[5], price, airline[0])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            FlightOption(
                id=token,
                source="explore",
                selection_stage="destination",
                origin=query.origin.upper(),
                dest=airline[5],
                outbound_date=query.outbound_date,
                return_date=query.return_date,
                price=price,
                airline_code=airline[0],
                airline=airline[1],
                stops=airline[2],
                duration_minutes=airline[3],
                route_token=token,
                workflow_state={"mode": "explore", "route_token": token},
                raw={"rpc": "GetExploreDestinations", "path": list(path), "destination_entity_id": row[0]},
            )
        )
    return rows


def parse_flight_options(parsed: list[Any], query: Any, *, source: str, stage: str) -> list[FlightOption]:
    rows = []
    seen = set()
    for path, row in walk(parsed):
        if not _is_option_row(row):
            continue
        token = row[0][1]
        code = row[1]
        flight_nums = _flight_nums(token, code)
        option = FlightOption(
            id=token,
            source=source,  # type: ignore[arg-type]
            selection_stage=stage,  # type: ignore[arg-type]
            origin=row[7],
            dest=row[9],
            date=row[6],
            outbound_date=query.outbound_date,
            return_date=query.return_date,
            price=row[0][0][1],
            airline_code=code,
            airline=row[2],
            stops=row[3],
            duration_minutes=row[4],
            flight_num=flight_nums[0] if flight_nums else None,
            flight_nums=flight_nums,
            option_token=token,
            workflow_state={"mode": source, "option_token": token},
            raw={"path": list(path), "origin_airport": row[8], "dest_airport": row[10]},
        )
        key = (option.option_token, option.origin, option.dest, option.date)
        if key not in seen:
            seen.add(key)
            rows.append(option)
    return rows


def attach_details(result: FlightOption, details: list[FlightOption]) -> None:
    outbound = [option.model_dump(exclude_none=True) for option in details if option.dest == result.dest]
    result.outbound_options = outbound
    if outbound:
        first = outbound[0]
        result.flight_num = first.get("flight_num")
        result.flight_nums = first.get("flight_nums", [])
        result.option_token = first.get("option_token")


def _is_explore_row(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 7:
        return False
    price, airline = value[1], value[6]
    return (
        isinstance(value[0], str)
        and isinstance(price, list)
        and len(price) > 1
        and isinstance(price[0], list)
        and isinstance(price[0][1], int)
        and isinstance(price[1], str)
        and isinstance(airline, list)
        and len(airline) >= 7
        and isinstance(airline[5], str)
        and re.fullmatch(r"[A-Z]{3}|", airline[5]) is not None
    )


def _is_option_row(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 11:
        return False
    price_token = value[0]
    price = price_token[0] if isinstance(price_token, list) and price_token else None
    return (
        isinstance(price, list)
        and len(price) > 1
        and isinstance(price[1], int)
        and len(price_token) > 1
        and isinstance(price_token[1], str)
        and isinstance(value[1], str)
        and isinstance(value[2], str)
        and isinstance(value[3], int)
        and isinstance(value[4], int)
        and isinstance(value[6], str)
        and isinstance(value[7], str)
        and isinstance(value[9], str)
    )


def _flight_nums(token: str, airline_code: str) -> list[str]:
    try:
        raw = base64.b64decode(token + "=" * ((4 - len(token) % 4) % 4))
    except ValueError:
        return []
    pattern = rb"(?:[A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])\d{2,4}" if airline_code == "multi" else re.escape(airline_code).encode() + rb"\d{1,4}"
    seen, out = set(), []
    for match in re.finditer(pattern, raw):
        value = match.group(0).decode("ascii", errors="ignore")
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out

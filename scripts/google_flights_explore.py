#!/usr/bin/env python3
"""
Fetch Google Flights Explore results from a copied browser curl.

Usage:
  python scripts/google_flights_explore.py google_flights_session.json --outbound-date 2026-08-01 --return-date 2026-08-08 --send --json-out flights.json

The copied curl contains Google session cookies and tokens. Treat it like a
password and do not commit or share it.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.parse import urlunparse

import httpx


JSON_PREFIX = ")]}'"
ANYWHERE_DESTINATION_ID = "/m/02j71"
ENTITY_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "google_flights_entities.json"
EXPLORE_DESTINATIONS_RPC = "GetExploreDestinations"
EXPLORE_DETAILS_RPC = "GetExploreDestinationFlightDetails"
FLIGHTS_SERVICE_MARKER = "/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class CurlRequest:
    url: str
    headers: dict[str, str]
    data: str


@dataclass(frozen=True)
class PlaceEntity:
    code: str
    entity_id: str
    name: str | None = None
    type: int | None = None


def parse_curl(text: str) -> CurlRequest:
    tokens = shlex.split(text.replace("\\\n", " "))
    if not tokens or tokens[0] != "curl":
        raise ValueError("Expected a command starting with curl")

    url = ""
    headers: dict[str, str] = {}
    data = ""
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("http"):
            url = token
        elif token in ("-H", "--header"):
            i += 1
            name, value = tokens[i].split(":", 1)
            headers[name.strip()] = value.strip()
        elif token in ("-b", "--cookie", "--cookie-jar"):
            i += 1
            headers["cookie"] = tokens[i]
        elif token in ("--data-raw", "--data", "--data-binary", "-d"):
            i += 1
            data = tokens[i]
        i += 1

    if not url or not data:
        raise ValueError("Could not find URL and --data-raw in curl command")
    return CurlRequest(url=url, headers=headers, data=data)


def load_request_template(path: Path) -> CurlRequest:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text())
        try:
            return CurlRequest(url=raw["url"], headers=raw["headers"], data=raw["data"])
        except KeyError as exc:
            raise ValueError(f"Session template is missing key: {exc.args[0]}") from exc
    return parse_curl(read_curl_text(path))


def read_curl_text(path: Path) -> str:
    if str(path) == "-":
        return sys.stdin.read()
    if not path.exists():
        raise FileNotFoundError(
            f"Curl file not found: {path}. Save your copied Google Flights curl to this path, "
            "or pass the real path to the file. Use '-' to read the curl from stdin."
        )
    return path.read_text()


def load_entity_cache(path: Path = ENTITY_CACHE_PATH) -> dict[str, PlaceEntity]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    cache: dict[str, PlaceEntity] = {}
    for code, value in raw.items():
        cache[code.upper()] = PlaceEntity(
            code=code.upper(),
            entity_id=value["entity_id"],
            name=value.get("name"),
            type=value.get("type"),
        )
    return cache


def resolve_place(value: str | None, cache: dict[str, PlaceEntity], *, default_anywhere: bool = False) -> PlaceEntity:
    if not value and default_anywhere:
        return cache.get("ANYWHERE", PlaceEntity("ANYWHERE", ANYWHERE_DESTINATION_ID, "Anywhere", 6))
    if not value:
        raise ValueError("Missing airport code")

    normalized = value.strip().upper()
    if value.startswith("/m/"):
        return PlaceEntity(code=value, entity_id=value, type=None)
    if normalized in cache:
        return cache[normalized]
    raise ValueError(f"Unknown airport code {value!r}. Add it to {ENTITY_CACHE_PATH}.")


def code_for_entity(entity_id: str, cache: dict[str, PlaceEntity]) -> str | None:
    for code, entity in cache.items():
        if entity.entity_id == entity_id and code != "ANYWHERE":
            return code
    if entity_id == ANYWHERE_DESTINATION_ID:
        return "ANYWHERE"
    return None


def decode_f_req(data: str) -> tuple[list[Any], list[Any], dict[str, str]]:
    form = {key: values[0] for key, values in parse_qs(data).items()}
    outer = json.loads(form["f.req"])
    inner = json.loads(outer[1])
    return outer, inner, form


def encode_f_req(outer: list[Any], inner: list[Any], form: dict[str, str]) -> str:
    updated = dict(form)
    updated["f.req"] = json.dumps([outer[0], json.dumps(inner, separators=(",", ":"))], separators=(",", ":"))
    return urlencode(updated)


def encode_inner_f_req(inner: list[Any], form: dict[str, str]) -> str:
    updated = dict(form)
    updated["f.req"] = json.dumps([None, json.dumps(inner, separators=(",", ":"))], separators=(",", ":"))
    return urlencode(updated)


def extract_f_req_from_encoded_form(data: str) -> str:
    parsed = parse_qs(data)
    if "f.req" not in parsed or not parsed["f.req"]:
        raise ValueError("Encoded request body does not contain f.req")
    return parsed["f.req"][0]


def get_search_block(inner: list[Any]) -> list[Any]:
    if len(inner) > 3 and isinstance(inner[3], list):
        return inner[3]
    if len(inner) > 1 and isinstance(inner[1], list):
        return inner[1]
    raise ValueError("Could not locate Google Flights search block in f.req")


def rpc_name(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]


def ensure_explore_destinations_request(req: CurlRequest) -> None:
    name = rpc_name(req.url)
    if name != EXPLORE_DESTINATIONS_RPC:
        raise ValueError(f"Expected a {EXPLORE_DESTINATIONS_RPC} curl, got {name}.")


def request_with_rpc(req: CurlRequest, rpc: str) -> CurlRequest:
    parsed = urlparse(req.url)
    prefix, sep, _current_rpc = parsed.path.partition(FLIGHTS_SERVICE_MARKER)
    if not sep:
        raise ValueError("Could not locate Google Flights service path in request URL.")
    url = urlunparse(parsed._replace(path=f"{prefix}{FLIGHTS_SERVICE_MARKER}{rpc}"))
    return CurlRequest(url=url, headers=req.headers, data=req.data)


def describe_request(req: CurlRequest, inner: list[Any], cache: dict[str, PlaceEntity]) -> dict[str, Any]:
    search = get_search_block(inner)
    legs = search[13]
    return {
        "rpc": rpc_name(req.url),
        "destination_mode": "anywhere" if legs[0][1][0][0][0] == ANYWHERE_DESTINATION_ID else "explicit",
        "passengers": {
            "adult_child_infant_seat_infant_lap": search[6],
        },
        "legs": [
            {
                "origin": {
                    "code": code_for_entity(leg[0][0][0][0], cache),
                    "entity_id": leg[0][0][0][0],
                    "type": leg[0][0][0][1],
                },
                "destination": {
                    "code": code_for_entity(leg[1][0][0][0], cache),
                    "entity_id": leg[1][0][0][0],
                    "type": leg[1][0][0][1],
                },
                "date": leg[6],
                "nonstop_only": leg[3] == 1,
            }
            for leg in legs
        ],
        "raw_search_block": search,
    }


def mutate_request(
    outer: list[Any],
    inner: list[Any],
    form: dict[str, str],
    *,
    origin: PlaceEntity,
    destination: PlaceEntity,
    outbound_date: str,
    return_date: str,
    nonstop: bool | None,
) -> str:
    _ = outer
    search = get_search_block(inner)
    legs = search[13]

    destination_type = destination.type or 4
    origin_type = origin.type or 4

    legs[0][0][0][0][0] = origin.entity_id
    legs[0][0][0][0][1] = origin_type
    legs[0][1][0][0][0] = destination.entity_id
    legs[0][1][0][0][1] = destination_type
    legs[1][0][0][0][0] = destination.entity_id
    legs[1][0][0][0][1] = destination_type
    legs[1][1][0][0][0] = origin.entity_id
    legs[1][1][0][0][1] = origin_type
    legs[0][6] = outbound_date
    legs[1][6] = return_date

    for item in search:
        if isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) and item[0].startswith("/m/"):
            item[0] = destination.entity_id
            item[1] = destination_type

    if nonstop is not None:
        for leg in legs:
            leg[3] = 1 if nonstop else 0

    return encode_f_req(outer, inner, form)


def build_details_data(
    inner: list[Any],
    form: dict[str, str],
    *,
    route_token: str,
    origin: PlaceEntity,
    destination: PlaceEntity,
    outbound_date: str,
    return_date: str,
    nonstop: bool | None,
) -> str:
    search = copy.deepcopy(get_search_block(inner))
    legs = search[13]
    destination_type = destination.type or 4
    origin_type = origin.type or 4

    legs[0][0][0][0][0] = origin.entity_id
    legs[0][0][0][0][1] = origin_type
    legs[0][1][0][0][0] = destination.entity_id
    legs[0][1][0][0][1] = destination_type
    legs[1][0][0][0][0] = destination.entity_id
    legs[1][0][0][0][1] = destination_type
    legs[1][1][0][0][0] = origin.entity_id
    legs[1][1][0][0][1] = origin_type
    legs[0][6] = outbound_date
    legs[1][6] = return_date

    if len(search) <= 26:
        search.extend([None] * (27 - len(search)))
    search[26] = [destination.entity_id, destination_type]

    if nonstop is not None:
        for leg in legs:
            leg[3] = 1 if nonstop else 0

    return encode_inner_f_req([[None, route_token], search], form)


def validate_date(value: str, name: str) -> None:
    if not DATE_RE.fullmatch(value):
        raise ValueError(f"{name} must use YYYY-MM-DD format, got {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} is not a real calendar date: {value!r}") from exc


def parse_google_rpc_response(text: str) -> list[Any]:
    stripped = text.lstrip()
    if stripped.startswith(JSON_PREFIX):
        stripped = stripped.split("\n", 1)[1].lstrip()

    parsed: list[Any] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line or line.isdigit():
            continue
        try:
            parsed.append(decode_json_strings(json.loads(line)))
        except json.JSONDecodeError:
            pass

    if parsed:
        return parsed

    try:
        return [decode_json_strings(json.loads(stripped))]
    except json.JSONDecodeError:
        return []


def decode_json_strings(value: Any) -> Any:
    if isinstance(value, list):
        return [decode_json_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: decode_json_strings(item) for key, item in value.items()}
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return decode_json_strings(json.loads(stripped))
            except json.JSONDecodeError:
                return value
    return value


def walk(value: Any, path: tuple[int | str, ...] = ()) -> list[tuple[tuple[int | str, ...], Any]]:
    found = [(path, value)]
    if isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk(item, (*path, index)))
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(walk(item, (*path, key)))
    return found


def extract_flights(
    parsed: list[Any],
    *,
    origin: PlaceEntity,
    requested_destination: PlaceEntity,
    outbound_date: str,
    return_date: str,
) -> list[dict[str, Any]]:
    flights: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, int | None, str | None]] = set()

    for path, row in walk(parsed):
        if not is_explore_fare_row(row):
            continue

        price_block = row[1]
        airline_block = row[6]
        route_token = price_block[1] if len(price_block) > 1 else None
        flight = {
            "path": list(path),
            "origin": origin.code,
            "origin_entity_id": origin.entity_id,
            "requested_destination": requested_destination.code,
            "requested_destination_entity_id": requested_destination.entity_id,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "destination_entity_id": row[0],
            "price_usd": price_block[0][1] if price_block and price_block[0] else None,
            "route_token": route_token,
            "airline_code": airline_block[0],
            "airline_name": airline_block[1],
            "stops": airline_block[2],
            "duration_minutes": airline_block[3],
            "destination": airline_block[5],
            "result_origin_entity_id": airline_block[6],
            "emissions_or_delta": airline_block[8] if len(airline_block) > 8 else None,
            "available": row[9] if len(row) > 9 else None,
            "trip_type": row[10] if len(row) > 10 else None,
            "result_type": row[14] if len(row) > 14 else None,
            "raw": row,
        }
        key = (
            flight["destination_entity_id"],
            flight["destination"],
            flight["price_usd"],
            flight["airline_code"],
        )
        if key not in seen:
            seen.add(key)
            flights.append(flight)
    return flights


def compact_rows(flights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "flight_num": first_option_flight_num(flight.get("outbound_options", [])),
            "origin": flight["origin"],
            "dest": flight["destination"],
            "outbound_date": flight["outbound_date"],
            "return_date": flight["return_date"],
            "price": flight["price_usd"],
            "currency": "USD",
            "airline_code": flight["airline_code"],
            "airline": flight["airline_name"],
            "stops": flight["stops"],
            "duration_minutes": flight["duration_minutes"],
            "route_token": flight["route_token"],
            "outbound_options": flight.get("outbound_options", []),
            "return_options": flight.get("return_options", []),
        }
        for flight in flights
    ]


def first_option_flight_num(options: list[dict[str, Any]]) -> str | None:
    for option in options:
        if option.get("flight_nums"):
            return option["flight_nums"][0]
        if option.get("flight_num"):
            return option["flight_num"]
    return None


def is_explore_fare_row(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 7:
        return False
    if not isinstance(value[0], str) or not (value[0].startswith("/m/") or value[0].startswith("/g/")):
        return False
    price_block = value[1]
    airline_block = value[6]
    if not (
        isinstance(price_block, list)
        and price_block
        and isinstance(price_block[0], list)
        and len(price_block[0]) > 1
        and isinstance(price_block[0][1], int)
    ):
        return False
    return (
        isinstance(airline_block, list)
        and len(airline_block) >= 7
        and isinstance(airline_block[0], str)
        and isinstance(airline_block[5], str)
        and re.fullmatch(r"[A-Z]{3}|", airline_block[5]) is not None
    )


def extract_detail_options(
    parsed: list[Any],
    *,
    origin: PlaceEntity,
    destination: PlaceEntity,
    outbound_date: str,
    return_date: str,
) -> dict[str, list[dict[str, Any]]]:
    options = {"outbound": [], "return": [], "unknown": []}
    seen: set[tuple[str | None, str | None, int | None, str | None]] = set()
    for _path, row in walk(parsed):
        if not is_detail_flight_row(row):
            continue
        option = detail_option(row)
        flight_nums = decode_flight_numbers(option["token"], option["airline_code"])
        flight_num = flight_nums[0] if flight_nums else None
        option["flight_num"] = flight_num
        option["flight_nums"] = flight_nums
        if option["dest"] == destination.code and option["date"] == outbound_date:
            leg = "outbound"
        elif option["origin"] == destination.code and option["date"] == return_date:
            leg = "return"
        else:
            leg = "unknown"
        option["leg"] = leg
        key = (flight_num, option["date"], option["price"], option["token"])
        if key in seen:
            continue
        seen.add(key)
        options[leg].append(option)
    return options


def is_detail_flight_row(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 12:
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
        and isinstance(value[8], str)
        and isinstance(value[9], str)
    )


def detail_option(row: list[Any]) -> dict[str, Any]:
    return {
        "flight_num": None,
        "flight_nums": [],
        "price": row[0][0][1],
        "currency": "USD",
        "token": row[0][1],
        "airline_code": row[1],
        "airline": row[2],
        "stops": row[3],
        "duration_minutes": row[4],
        "date": row[6],
        "origin": row[7],
        "origin_airport": row[8],
        "dest": row[9],
        "dest_airport": row[10],
    }


def decode_flight_numbers(token: str | None, airline_code: str | None) -> list[str]:
    if not token or not airline_code:
        return []
    try:
        raw = base64.b64decode(token + "=" * ((4 - len(token) % 4) % 4))
    except ValueError:
        return []
    if airline_code != "multi":
        pattern = re.escape(airline_code).encode() + rb"\d{1,4}"
    else:
        pattern = rb"(?:[A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])\d{2,4}"
    seen: set[str] = set()
    flight_nums: list[str] = []
    for match in re.finditer(pattern, raw):
        flight_num = match.group(0).decode("ascii", errors="ignore")
        if flight_num not in seen:
            seen.add(flight_num)
            flight_nums.append(flight_num)
    return flight_nums


def enrich_with_details(
    req: CurlRequest,
    inner: list[Any],
    form: dict[str, str],
    flights: list[dict[str, Any]],
    *,
    origin: PlaceEntity,
    outbound_date: str,
    return_date: str,
    nonstop: bool | None,
    limit: int | None,
) -> None:
    details_req = request_with_rpc(req, EXPLORE_DETAILS_RPC)
    selected = flights if limit is None else flights[:limit]
    for flight in selected:
        route_token = flight.get("route_token")
        destination_code = flight.get("destination")
        destination_entity_id = flight.get("destination_entity_id")
        if not route_token or not destination_code or not destination_entity_id:
            continue
        destination = PlaceEntity(
            code=destination_code,
            entity_id=destination_entity_id,
            type=4,
        )
        data = build_details_data(
            inner,
            form,
            route_token=route_token,
            origin=origin,
            destination=destination,
            outbound_date=outbound_date,
            return_date=return_date,
            nonstop=nonstop,
        )
        response = send(details_req, data)
        response.raise_for_status()
        parsed = parse_google_rpc_response(response.text)
        options = extract_detail_options(
            parsed,
            origin=origin,
            destination=destination,
            outbound_date=outbound_date,
            return_date=return_date,
        )
        flight["outbound_options"] = options["outbound"]
        flight["return_options"] = options["return"]
        flight["unknown_detail_options"] = options["unknown"]


def send(req: CurlRequest, data: str) -> httpx.Response:
    headers = {
        name: value
        for name, value in req.headers.items()
        if not name.startswith(":") and name.lower() not in {"content-length", "host", "accept-encoding"}
    }
    headers.setdefault("content-type", "application/x-www-form-urlencoded;charset=UTF-8")
    return httpx.post(req.url, headers=headers, content=data, timeout=30.0)


def env_default(name: str, fallback: str | None = None) -> str | None:
    return os.environ.get(name) or fallback


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "curl_file",
        nargs="?",
        type=Path,
        default=Path(env_default("GOOGLE_FLIGHTS_TEMPLATE", "google_flights_session.json")),
        help="Path to copied curl text, captured session JSON, or '-' for curl stdin. Defaults to $GOOGLE_FLIGHTS_TEMPLATE or google_flights_session.json.",
    )
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--decode-only", action="store_true")
    parser.add_argument("--raw-out", type=Path)
    parser.add_argument("--json-out", type=Path, help="Writes compact rows: flight_num, price, origin, dest, and extras.")
    parser.add_argument("--full-json-out", type=Path, help="Optional path for the full parsed internal rows.")
    parser.add_argument("--prices-out", type=Path, help="Alias for --json-out compact output.")
    parser.add_argument("--f-req-out", type=Path, help="Write the generated f.req value to a file.")
    parser.add_argument("--print-f-req", action="store_true", help="Print the generated f.req to stdout and exit unless --send is set.")
    parser.add_argument("--include-details", action="store_true", help="Fetch route-token details for exact outbound flight options.")
    parser.add_argument(
        "--details-limit",
        type=int,
        default=10,
        help="Maximum destination rows to enrich when --include-details is set. Use 0 for all rows.",
    )
    parser.add_argument(
        "--origin",
        default=env_default("GOOGLE_FLIGHTS_ORIGIN", "SFO"),
        help="IATA code or Google entity id. Defaults to $GOOGLE_FLIGHTS_ORIGIN or SFO.",
    )
    parser.add_argument("--destination", default=env_default("GOOGLE_FLIGHTS_DESTINATION"), help="Optional IATA code or entity id. Defaults to anywhere.")
    parser.add_argument("--outbound-date", default=env_default("GOOGLE_FLIGHTS_OUTBOUND_DATE"))
    parser.add_argument("--return-date", default=env_default("GOOGLE_FLIGHTS_RETURN_DATE"))
    parser.add_argument("--nonstop", choices=("true", "false"))
    args = parser.parse_args()

    try:
        if not args.outbound_date:
            raise ValueError("Missing --outbound-date or $GOOGLE_FLIGHTS_OUTBOUND_DATE")
        if not args.return_date:
            raise ValueError("Missing --return-date or $GOOGLE_FLIGHTS_RETURN_DATE")
        validate_date(args.outbound_date, "--outbound-date")
        validate_date(args.return_date, "--return-date")
        req = load_request_template(args.curl_file)
        ensure_explore_destinations_request(req)
        outer, inner, form = decode_f_req(req.data)
        cache = load_entity_cache()
        origin = resolve_place(args.origin, cache)
        destination = resolve_place(args.destination, cache, default_anywhere=True)
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    nonstop = None if args.nonstop is None else args.nonstop == "true"
    data = mutate_request(
        outer,
        inner,
        form,
        origin=origin,
        destination=destination,
        outbound_date=args.outbound_date,
        return_date=args.return_date,
        nonstop=nonstop,
    )
    request_description = describe_request(req, inner, cache)
    eprint(json.dumps(request_description, indent=2))

    generated_f_req = extract_f_req_from_encoded_form(data)
    if args.f_req_out:
        args.f_req_out.parent.mkdir(parents=True, exist_ok=True)
        args.f_req_out.write_text(generated_f_req)
        eprint(f"wrote f.req to {args.f_req_out}")
    if args.print_f_req:
        if args.send:
            eprint(generated_f_req)
        else:
            print(generated_f_req)

    if args.decode_only or not args.send:
        return 0

    response = send(req, data)
    eprint(f"HTTP {response.status_code}")
    response.raise_for_status()

    if args.raw_out:
        args.raw_out.parent.mkdir(parents=True, exist_ok=True)
        args.raw_out.write_text(response.text)
        eprint(f"wrote raw response to {args.raw_out}")

    parsed = parse_google_rpc_response(response.text)
    flights = extract_flights(
        parsed,
        origin=origin,
        requested_destination=destination,
        outbound_date=args.outbound_date,
        return_date=args.return_date,
    )
    if args.include_details and flights:
        detail_limit = None if args.details_limit == 0 else max(args.details_limit, 0)
        eprint(
            "fetching route details for "
            f"{len(flights) if detail_limit is None else min(detail_limit, len(flights))} destination rows"
        )
        enrich_with_details(
            req,
            inner,
            form,
            flights,
            origin=origin,
            outbound_date=args.outbound_date,
            return_date=args.return_date,
            nonstop=nonstop,
            limit=detail_limit,
        )
    compact = compact_rows(flights)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(compact, indent=2))
        eprint(f"wrote compact flights to {args.json_out}")
    if args.full_json_out:
        args.full_json_out.parent.mkdir(parents=True, exist_ok=True)
        args.full_json_out.write_text(json.dumps(flights, indent=2))
        eprint(f"wrote full parsed rows to {args.full_json_out}")
    if args.prices_out:
        args.prices_out.parent.mkdir(parents=True, exist_ok=True)
        args.prices_out.write_text(json.dumps(compact, indent=2))
        eprint(f"wrote compact prices to {args.prices_out}")
    if not flights:
        eprint(
            "No Explore fare rows were parsed. This parser is tuned for destination=anywhere; "
            "explicit destinations may require the Google flight-details RPC."
        )
    print(json.dumps(compact, indent=2)[:20000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

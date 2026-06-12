from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlencode

from api.google_flights.constants import JSON_PREFIX


def decode_f_req(data: str) -> tuple[list[Any], list[Any], dict[str, str]]:
    form = {key: values[0] for key, values in parse_qs(data).items()}
    outer = json.loads(form["f.req"])
    return outer, json.loads(outer[1]), form


def encode_inner(inner: list[Any], form: dict[str, str]) -> str:
    updated = dict(form)
    updated["f.req"] = json.dumps([None, json.dumps(inner, separators=(",", ":"))], separators=(",", ":"))
    return urlencode(updated)


def search_block(inner: list[Any]) -> list[Any]:
    if len(inner) > 3 and isinstance(inner[3], list):
        return inner[3]
    if len(inner) > 1 and isinstance(inner[1], list):
        return inner[1]
    raise ValueError("Could not locate Google Flights search block in f.req")


def parse_rpc_response(text: str) -> list[Any]:
    stripped = text.lstrip()
    if stripped.startswith(JSON_PREFIX):
        stripped = stripped.split("\n", 1)[1].lstrip()
    parsed = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line or line.isdigit():
            continue
        try:
            parsed.append(_decode_json_strings(json.loads(line)))
        except json.JSONDecodeError:
            pass
    if parsed:
        return parsed
    try:
        return [_decode_json_strings(json.loads(stripped))]
    except json.JSONDecodeError:
        return []


def walk(value: Any, path: tuple[int | str, ...] = ()) -> list[tuple[tuple[int | str, ...], Any]]:
    rows = [(path, value)]
    if isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(walk(item, (*path, index)))
    elif isinstance(value, dict):
        for key, item in value.items():
            rows.extend(walk(item, (*path, key)))
    return rows


def _decode_json_strings(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode_json_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _decode_json_strings(item) for key, item in value.items()}
    if isinstance(value, str) and value.strip()[:1] in {"[", "{"}:
        try:
            return _decode_json_strings(json.loads(value))
        except json.JSONDecodeError:
            return value
    return value

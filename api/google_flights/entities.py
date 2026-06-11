from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from api.google_flights.constants import ANYWHERE_ID, ENTITY_CACHE_PATH


@dataclass(frozen=True)
class Place:
    code: str
    entity_id: str
    name: str | None = None
    type: int | None = None


def load_entities(path: Path = ENTITY_CACHE_PATH) -> dict[str, Place]:
    raw = json.loads(path.read_text()) if path.exists() else {}
    return {
        code.upper(): Place(code.upper(), item["entity_id"], item.get("name"), item.get("type"))
        for code, item in raw.items()
    }


def resolve_place(value: str | None, entities: dict[str, Place], *, anywhere: bool = False) -> Place:
    if not value and anywhere:
        return entities.get("ANYWHERE", Place("ANYWHERE", ANYWHERE_ID, "Anywhere", 6))
    if not value:
        raise ValueError("Missing airport code")
    if value.startswith("/m/"):
        return Place(value, value)
    code = value.upper()
    if code not in entities:
        raise ValueError(f"Unknown airport code {value!r}. Add it to {ENTITY_CACHE_PATH}.")
    return entities[code]

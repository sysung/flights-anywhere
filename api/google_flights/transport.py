from __future__ import annotations

import logging
import time
from urllib.parse import urlparse, urlunparse

import httpx

from api.google_flights.constants import SERVICE_MARKER
from api.google_flights.session import SessionTemplate


DROP_HEADERS = {"content-length", "host", "accept-encoding"}
logger = logging.getLogger(__name__)


def with_rpc(session: SessionTemplate, rpc: str) -> SessionTemplate:
    parsed = urlparse(session.url)
    prefix, sep, _ = parsed.path.partition(SERVICE_MARKER)
    if not sep:
        raise ValueError("Session URL is not a Google Flights service URL")
    url = urlunparse(parsed._replace(path=f"{prefix}{SERVICE_MARKER}{rpc}"))
    return SessionTemplate(url, session.headers, session.data)


def post(session: SessionTemplate, data: str) -> str:
    headers = {
        name: value
        for name, value in session.headers.items()
        if not name.startswith(":") and name.lower() not in DROP_HEADERS
    }
    headers.setdefault("content-type", "application/x-www-form-urlencoded;charset=UTF-8")
    rpc = urlparse(session.url).path.rstrip("/").split("/")[-1]
    started = time.monotonic()
    logger.info("google_flights.rpc.start rpc=%s bytes=%s", rpc, len(data))
    response = httpx.post(session.url, headers=headers, content=data, timeout=30)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info("google_flights.rpc.done rpc=%s status=%s elapsed_ms=%s bytes=%s", rpc, response.status_code, elapsed_ms, len(response.content))
    response.raise_for_status()
    return response.text

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from api.google_flights.constants import DEFAULT_SESSION_PATH, RPC_EXPLORE, SERVICE_MARKER

logger = logging.getLogger(__name__)

SEED_INNER = [
    [],
    None,
    None,
    [
        None,
        None,
        1,
        None,
        [],
        1,
        [1, 0, 0, 0],
        None,
        None,
        None,
        None,
        None,
        None,
        [
            [[[[ "/m/0r5yp", 5]]], [[[ "/m/02j71", 6]]], None, 0, None, None, "2026-08-01", None, None, None, None, None, None, None, 3],
            [[[[ "/m/02j71", 6]]], [[[ "/m/0r5yp", 5]]], None, 0, None, None, "2026-08-08", None, None, None, None, None, None, None, 3],
        ],
        None,
        None,
        None,
        1,
        None,
        None,
        None,
        None,
        None,
        None,
        1,
        1,
    ],
    None,
    1,
    None,
    0,
    None,
    0,
    [1281, 521],
    2,
]


@dataclass(frozen=True)
class SessionTemplate:
    url: str
    headers: dict[str, str]
    data: str


class SessionManager:
    def __init__(self, path: Path | None = None, ttl_seconds: int | None = None) -> None:
        self.path = path or Path(os.environ.get("GOOGLE_FLIGHTS_SESSION_PATH", DEFAULT_SESSION_PATH))
        self.ttl_seconds = ttl_seconds or int(os.environ.get("GOOGLE_FLIGHTS_SESSION_TTL_SECONDS", "3600"))
        self._session: SessionTemplate | None = None
        self._loaded_at = 0.0
        self._lock = RLock()

    def get(self) -> SessionTemplate:
        with self._lock:
            if self._session and not self._expired(self._loaded_at):
                if not _has_mutable_round_trip_legs(self._session.data):
                    logger.warning("google_flights.session.cache_invalid source=memory path=%s", self.path)
                    self.invalidate()
                    return self.refresh()
                logger.info("google_flights.session.cache_hit memory path=%s", self.path)
                return self._session
            if self.path.exists() and not self._expired(self.path.stat().st_mtime):
                logger.info("google_flights.session.cache_hit file path=%s", self.path)
                try:
                    session = _read_template(self.path)
                except (KeyError, TypeError, json.JSONDecodeError) as exc:
                    logger.warning("google_flights.session.cache_invalid source=file path=%s error=%s", self.path, exc)
                    return self.refresh()
                if not _has_mutable_round_trip_legs(session.data):
                    logger.warning("google_flights.session.cache_invalid source=file path=%s", self.path)
                    return self.refresh()
                self._session = session
                self._loaded_at = time.time()
                return self._session
            logger.info("google_flights.session.cache_miss path=%s", self.path)
            return self.refresh()

    def refresh(self) -> SessionTemplate:
        with self._lock:
            logger.info("google_flights.session.refresh_start path=%s", self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            raw = capture_session()
            self.path.write_text(json.dumps(raw, indent=2))
            self._session = SessionTemplate(raw["url"], raw["headers"], raw["data"])
            self._loaded_at = time.time()
            logger.info("google_flights.session.refresh_done path=%s source_rpc=%s", self.path, raw.get("source_rpc"))
            return self._session

    def invalidate(self) -> None:
        with self._lock:
            logger.info("google_flights.session.invalidate path=%s", self.path)
            self._session = None
            self._loaded_at = 0.0

    def _expired(self, timestamp: float) -> bool:
        return time.time() - timestamp >= self.ttl_seconds


def capture_session(timeout_seconds: int = 45, headless: bool = True) -> dict[str, Any]:
    try:
        from playwright.sync_api import Request, sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError("Playwright is required to refresh Google Flights sessions.") from exc

    captured: dict[str, Any] | None = None

    def on_request(request: Request) -> None:
        nonlocal captured
        if captured or request.method != "POST" or SERVICE_MARKER not in request.url:
            return
        form = parse_qs(request.post_data or "")
        if "f.req" not in form:
            return
        headers = request.all_headers()
        at = form.get("at", [""])[0]
        source_rpc = urlparse(request.url).path.rstrip("/").split("/")[-1]
        logger.info("google_flights.session.request_captured source_rpc=%s at_present=%s", source_rpc, bool(at))
        captured = {
            "captured_at": time.time(),
            "rpc": RPC_EXPLORE,
            "source_rpc": source_rpc,
            "url": _rpc_url(request.url, RPC_EXPLORE),
            "headers": headers,
            "data": urlencode({"f.req": _seed_f_req(), "at": at}),
        }

    logger.info("google_flights.session.capture_start headless=%s timeout_seconds=%s", headless, timeout_seconds)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(locale="en-US", viewport={"width": 1400, "height": 950})
        page = context.new_page()
        page.on("request", on_request)
        page.goto("https://www.google.com/travel/explore", wait_until="domcontentloaded")
        _trigger_explore(page)
        deadline = time.time() + timeout_seconds
        while not captured and time.time() < deadline:
            page.wait_for_timeout(250)
        context.close()
        browser.close()

    if not captured:
        logger.warning("google_flights.session.capture_timeout timeout_seconds=%s", timeout_seconds)
        raise TimeoutError("Timed out waiting for a Google Flights session request.")
    return captured


def _read_template(path: Path) -> SessionTemplate:
    raw = json.loads(path.read_text())
    return SessionTemplate(raw["url"], raw["headers"], raw["data"])


def _rpc_url(url: str, rpc: str) -> str:
    parsed = urlparse(url)
    prefix, sep, _ = parsed.path.partition(SERVICE_MARKER)
    if not sep:
        return url
    return urlunparse(parsed._replace(path=f"{prefix}{SERVICE_MARKER}{rpc}"))


def _trigger_explore(page: Any) -> None:
    page.wait_for_timeout(2000)
    for selector in ('button[aria-label="Explore destinations"]', 'button:has-text("Explore")', 'text="Explore destinations"'):
        try:
            page.locator(selector).first.click(timeout=3000)
            page.wait_for_timeout(2500)
            return
        except Exception:
            continue


def _seed_f_req() -> str:
    return json.dumps([None, json.dumps(SEED_INNER, separators=(",", ":"))], separators=(",", ":"))


def _has_mutable_round_trip_legs(data: str) -> bool:
    try:
        form = parse_qs(data)
        outer = json.loads(form["f.req"][0])
        inner = json.loads(outer[1])
        block = inner[3] if len(inner) > 3 and isinstance(inner[3], list) else inner[1]
        legs = block[13]
        paths = [
            legs[0][0][0][0],
            legs[0][1][0][0],
            legs[1][0][0][0],
            legs[1][1][0][0],
        ]
        return all(isinstance(path, list) and len(path) >= 2 for path in paths)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return False

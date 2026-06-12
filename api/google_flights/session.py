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
    def __init__(self, path: Path | None = None, ttl_seconds: int | None = None, capture_timeout_seconds: int | None = None) -> None:
        self.path = path or Path(os.environ.get("GOOGLE_FLIGHTS_SESSION_PATH", DEFAULT_SESSION_PATH))
        self.ttl_seconds = ttl_seconds or int(os.environ.get("GOOGLE_FLIGHTS_SESSION_TTL_SECONDS", "3600"))
        self.capture_timeout_seconds = capture_timeout_seconds or int(os.environ.get("GOOGLE_FLIGHTS_SESSION_CAPTURE_TIMEOUT_SECONDS", "45"))
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
            raw = capture_session(timeout_seconds=self.capture_timeout_seconds)
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
    bootstrap_origin = os.environ.get("GOOGLE_FLIGHTS_SESSION_BOOTSTRAP_ORIGIN", "SFO").strip().upper() or "SFO"

    def on_request(request: Request) -> None:
        nonlocal captured
        if captured or request.method != "POST" or SERVICE_MARKER not in request.url:
            return
        form = parse_qs(request.post_data or "")
        if "f.req" not in form:
            return
        request_data = request.post_data or ""
        template_data = request_data
        template_source = "captured"
        if not _has_mutable_round_trip_legs(template_data):
            template_data = urlencode({"f.req": _seed_f_req(), "at": form.get("at", [""])[0]})
            template_source = "seed"
        headers = request.all_headers()
        at = form.get("at", [""])[0]
        source_rpc = urlparse(request.url).path.rstrip("/").split("/")[-1]
        logger.info(
            "google_flights.session.request_captured source_rpc=%s at_present=%s template_source=%s",
            source_rpc,
            bool(at),
            template_source,
        )
        captured = {
            "captured_at": time.time(),
            "rpc": RPC_EXPLORE,
            "source_rpc": source_rpc,
            "url": _rpc_url(request.url, RPC_EXPLORE),
            "headers": headers,
            "data": template_data,
            "template_source": template_source,
        }

    logger.info(
        "google_flights.session.capture_start headless=%s timeout_seconds=%s bootstrap_origin=%s",
        headless,
        timeout_seconds,
        bootstrap_origin,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--disable-dev-shm-usage"])
        context = browser.new_context(
            locale="en-US",
            timezone_id="America/Los_Angeles",
            viewport={"width": 1400, "height": 950},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()
        page.set_default_timeout(8000)
        page.on("request", on_request)
        deadline = time.time() + timeout_seconds
        for url in ("https://www.google.com/travel/explore?hl=en-US", "https://www.google.com/travel/flights?hl=en-US"):
            if captured or time.time() >= deadline:
                break
            try:
                logger.info("google_flights.session.capture_visit url=%s", url)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                _accept_google_consent(page)
                _trigger_explore(page, bootstrap_origin=bootstrap_origin)
            except Exception as exc:
                logger.warning("google_flights.session.capture_visit_failed url=%s error=%s", url, exc)
                continue
            wait_until = min(deadline, time.time() + 8)
            while not captured and time.time() < wait_until:
                page.wait_for_timeout(250)
        while not captured and time.time() < deadline:
            page.wait_for_timeout(250)
        if not captured:
            _log_capture_state(page)
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


def _trigger_explore(page: Any, *, bootstrap_origin: str = "SFO") -> None:
    page.wait_for_timeout(1500)
    _select_bootstrap_origin(page, bootstrap_origin)
    for selector in ('button[aria-label="Explore destinations"]', 'button:has-text("Explore")', 'text="Explore destinations"', 'button:has-text("Get started")'):
        try:
            page.locator(selector).first.click(timeout=3000)
            page.wait_for_timeout(2000)
            return
        except Exception:
            continue


def _accept_google_consent(page: Any) -> None:
    for label in ("Accept all", "I agree", "Agree", "Reject all"):
        try:
            page.get_by_role("button", name=label).click(timeout=1500)
            page.wait_for_timeout(1000)
            logger.info("google_flights.session.consent_clicked label=%s", label)
            return
        except Exception:
            continue


def _select_bootstrap_origin(page: Any, origin: str) -> None:
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body = ""
    if f"\u00a0{origin}" in body or f" {origin}" in body:
        return

    input_selectors = (
        'input[placeholder="Where from?"]',
        'input[aria-label^="Where from"]',
        'input[aria-label^="Origin"]',
    )
    for selector in input_selectors:
        try:
            field = page.locator(selector).first
            if not field.is_visible(timeout=1000):
                continue
            field.click(timeout=3000)
            page.keyboard.press("Control+A")
            page.keyboard.type(origin)
            page.wait_for_timeout(1200)
            _choose_origin_suggestion(page, origin)
            page.wait_for_timeout(1500)
            logger.info("google_flights.session.bootstrap_origin_selected origin=%s", origin)
            return
        except Exception as exc:
            logger.info("google_flights.session.bootstrap_origin_attempt_failed selector=%s error=%s", selector, exc)


def _choose_origin_suggestion(page: Any, origin: str) -> None:
    preferred_texts = {
        "SFO": ("San Francisco International Airport", "San Francisco"),
        "LAX": ("Los Angeles International Airport", "Los Angeles"),
        "JFK": ("John F. Kennedy International Airport", "New York"),
        "EWR": ("Newark Liberty International Airport", "Newark"),
        "ORD": ("O'Hare International Airport", "Chicago"),
    }
    for text in (*preferred_texts.get(origin, ()), origin):
        try:
            page.get_by_text(text, exact=False).first.click(timeout=2500)
            return
        except Exception:
            continue
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")


def _log_capture_state(page: Any) -> None:
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception as exc:
        logger.warning("google_flights.session.capture_state_unavailable error=%s", exc)
        return
    logger.warning(
        "google_flights.session.capture_state url=%s title=%s body_excerpt=%s",
        page.url,
        page.title(),
        " ".join(body.split())[:500],
    )


def _seed_f_req() -> str:
    return json.dumps([None, json.dumps(SEED_INNER, separators=(",", ":"))], separators=(",", ":"))


def _has_mutable_round_trip_legs(data: str) -> bool:
    try:
        form = parse_qs(data)
        outer = json.loads(form["f.req"][0])
        inner = json.loads(outer[1])
        block = inner[3] if len(inner) > 3 and isinstance(inner[3], list) else inner[1]
        legs = block[13]
        if not isinstance(legs, list) or len(legs) < 2:
            return False
        for leg in legs[:2]:
            if not isinstance(leg, list) or len(leg) < 2:
                return False
            for side in leg[:2]:
                if side and (not isinstance(side, list) or not isinstance(side[0][0], list)):
                    return False
        return True
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return False

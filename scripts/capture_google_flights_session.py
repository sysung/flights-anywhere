#!/usr/bin/env python3
"""Capture a Google Flights Explore request template with normal Playwright."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.async_api import Request, async_playwright


RPC_NAME = "GetExploreDestinations"
SERVICE_MARKER = "/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/"
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_explore_request(request: Request) -> bool:
    if request.method != "POST" or SERVICE_MARKER not in request.url:
        return False
    post_data = request.post_data or ""
    form = parse_qs(post_data)
    return "f.req" in form


async def template_from_request(request: Request) -> dict[str, Any]:
    headers = await request.all_headers()
    parsed = urlparse(request.url)
    query = parse_qs(parsed.query)
    form = parse_qs(request.post_data or "")
    source_rpc = parsed.path.rstrip("/").split("/")[-1]
    at = first(form.get("at"))
    return {
        "captured_at": now_iso(),
        "rpc": RPC_NAME,
        "source_rpc": source_rpc,
        "url": explore_url(request.url),
        "headers": headers,
        "data": urlencode({"f.req": seed_f_req(), "at": at or ""}),
        "metadata": {
            "f_sid": first(query.get("f.sid")),
            "bl": first(query.get("bl")),
            "hl": first(query.get("hl")),
            "at_present": bool(first(form.get("at"))),
            "f_req_present": True,
        },
    }


def first(values: list[str] | None) -> str | None:
    return values[0] if values else None


def seed_f_req() -> str:
    return json.dumps([None, json.dumps(SEED_INNER, separators=(",", ":"))], separators=(",", ":"))


def explore_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path
    prefix, _sep, _rpc = path.partition(SERVICE_MARKER)
    return urlunparse(parsed._replace(path=f"{prefix}{SERVICE_MARKER}{RPC_NAME}"))


async def main_async() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("google_flights_session.json"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--auto-search", action="store_true", help="Click Explore automatically after the page loads.")
    parser.add_argument("--debug-dir", type=Path, default=Path("capture_debug"))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    captured: asyncio.Future[dict[str, Any]] = asyncio.Future()
    seen_requests: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(locale="en-US", viewport={"width": 1400, "height": 950})
        page = await context.new_page()

        async def on_request(request: Request) -> None:
            if "google.com" in request.url:
                seen_requests.append(f"{request.method} {request.url}")
                del seen_requests[:-40]
            if not captured.done() and is_explore_request(request):
                captured.set_result(await template_from_request(request))

        page.on("request", lambda request: asyncio.create_task(on_request(request)))
        await page.goto("https://www.google.com/travel/explore", wait_until="domcontentloaded")

        if args.auto_search:
            await trigger_explore_search(page)

        print("Browser opened. Run any Google Flights Explore search in the page." if not args.auto_search else "Auto-search triggered.")
        print(f"Waiting for FlightsFrontendService session request; will save to {args.out}")

        try:
            template = await asyncio.wait_for(captured, timeout=args.timeout_seconds)
        except TimeoutError as exc:
            await write_debug_artifacts(page, args.debug_dir, seen_requests)
            raise TimeoutError(
                "Timed out waiting for a FlightsFrontendService session request. In headless mode, try --auto-search; "
                f"if that still fails, run without --headless and perform a search manually. Debug saved to {args.debug_dir}."
            ) from exc
        finally:
            await context.close()
            await browser.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(template, indent=2))
    print(f"wrote session template to {args.out}")
    return 0


async def trigger_explore_search(page: Any) -> None:
    await page.wait_for_timeout(2000)
    selectors = [
        'button[aria-label="Explore destinations"]',
        'button:has-text("Explore")',
        'text="Explore destinations"',
    ]
    for selector in selectors:
        try:
            await page.locator(selector).first.click(timeout=3000)
            await page.wait_for_timeout(3000)
        except Exception:
            continue


async def write_debug_artifacts(page: Any, debug_dir: Path, seen_requests: list[str]) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=debug_dir / "screenshot.png", full_page=True)
    (debug_dir / "page.html").write_text(await page.content())
    (debug_dir / "requests.log").write_text("\n".join(seen_requests) + "\n")


def main() -> int:
    try:
        return asyncio.run(main_async())
    except TimeoutError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

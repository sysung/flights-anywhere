#!/usr/bin/env python3
"""Probe Google Flights route-details RPCs with normal Playwright automation."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Request, Response, async_playwright


SERVICE_MARKER = "/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/"


def rpc_name(url: str) -> str | None:
    parsed = urlparse(url)
    if SERVICE_MARKER not in parsed.path:
        return None
    return parsed.path.rstrip("/").split("/")[-1]


def summarize_request(request: Request) -> dict[str, Any]:
    form = parse_qs(request.post_data or "")
    parsed = urlparse(request.url)
    query = parse_qs(parsed.query)
    f_req = form.get("f.req", [""])[0]
    return {
        "method": request.method,
        "rpc": rpc_name(request.url),
        "url": request.url,
        "f_sid": query.get("f.sid", [None])[0],
        "bl": query.get("bl", [None])[0],
        "has_at": bool(form.get("at", [""])[0]),
        "f_req_prefix": f_req[:500],
        "f_req_len": len(f_req),
    }


async def main_async() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/google_flights_route_probe.json"))
    parser.add_argument("--screenshot", type=Path, default=Path("/tmp/google_flights_route_probe.png"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    events: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(locale="en-US", viewport={"width": 1400, "height": 950})
        page = await context.new_page()

        async def on_request(request: Request) -> None:
            name = rpc_name(request.url)
            if request.method == "POST" and name:
                events.append({"kind": "request", **summarize_request(request)})

        async def on_response(response: Response) -> None:
            name = rpc_name(response.url)
            if name:
                event: dict[str, Any] = {
                    "kind": "response",
                    "rpc": name,
                    "status": response.status,
                    "url": response.url,
                }
                if name == "GetExploreDestinationFlightDetails":
                    try:
                        text = await response.text()
                        event["body_prefix"] = text[:5000]
                        event["body_len"] = len(text)
                    except Exception as exc:
                        event["body_error"] = str(exc)
                events.append(event)

        page.on("request", lambda request: asyncio.create_task(on_request(request)))
        page.on("response", lambda response: asyncio.create_task(on_response(response)))

        await page.goto("https://www.google.com/travel/explore", wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        await click_first(page, ['button[aria-label="Explore destinations"]', 'button:has-text("Explore")'])
        await page.wait_for_timeout(7000)
        await page.screenshot(path=args.screenshot, full_page=True)

        clicked = await click_first(
            page,
            [
                'text="Los Angeles"',
                'text="New York"',
                'text="San Diego"',
                '[role="button"]:has-text("$")',
                'a:has-text("$")',
                'div:has-text("$")',
            ],
        )
        if not clicked:
            await page.mouse.click(210, 405)
            clicked = True
        if clicked:
            await page.wait_for_timeout(4000)
            if not await click_first(page, ['text="View flights"', 'button:has-text("View flights")']):
                await page.mouse.click(199, 736)
            await page.wait_for_timeout(args.timeout_seconds * 1000)
            await page.screenshot(path=args.screenshot.with_name(f"{args.screenshot.stem}_after.png"), full_page=True)
        else:
            events.append({"kind": "probe", "message": "No visible fare result could be clicked."})

        await context.close()
        await browser.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(events, indent=2))
    print(f"wrote {len(events)} events to {args.out}")
    print(f"wrote screenshot to {args.screenshot}")
    return 0


async def click_first(page: Any, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first()
            if await locator.count() > 0:
                await locator.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())

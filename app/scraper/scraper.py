import os
import time
import json
import logging
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from app.scraper.stream_parser import WizStreamParser

logger = logging.getLogger(__name__)

def run_flight_scrape(origin, destination, departure_date, return_date):
    """
    Launches browser via Playwright, navigates to Google Flights, inputs search dates,
    origin, and destination, intercepts the GetShoppingResults Wiz stream, and returns the parsed chunks.
    """
    with sync_playwright() as p:
        logger.info("Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Apply stealth profile to prevent anti-bot blocking
        Stealth().apply_stealth_sync(page)

        # Intercept Wiz stream
        stream_parser = WizStreamParser()
        stream_finished = [False]

        def on_chunk_received(url, chunk_text, is_finished=False):
            if "GetShoppingResults" in url:
                if chunk_text:
                    stream_parser.feed(chunk_text, is_finished=False)
                if is_finished:
                    stream_finished[0] = True
                    # Flush the parser buffer
                    stream_parser.feed("", is_finished=True)

        # Expose python callback to browser Javascript runtime
        page.expose_function("onChunkReceived", on_chunk_received)

        # Inject script hooks for fetch and XHR interception
        js_hook = """
        (function() {
            const origOpen = XMLHttpRequest.prototype.open;
            const origSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url, ...args) {
                this._url = url;
                return origOpen.apply(this, [method, url, ...args]);
            };

            XMLHttpRequest.prototype.send = function(...args) {
                let lastLength = 0;
                const handleProgress = (isFinished) => {
                    try {
                        const url = this._url || '';
                        if (url.includes('GetShoppingResults')) {
                            const text = this.responseText;
                            if (text && text.length > lastLength) {
                                const newChunk = text.slice(lastLength);
                                lastLength = text.length;
                                if (window.onChunkReceived) {
                                    window.onChunkReceived(url, newChunk, isFinished);
                                }
                            } else if (isFinished && window.onChunkReceived) {
                                window.onChunkReceived(url, "", true);
                            }
                        }
                    } catch (e) {}
                };

                this.addEventListener('progress', () => handleProgress(false));
                this.addEventListener('readystatechange', () => {
                    if (this.readyState === 3) {
                        handleProgress(false);
                    } else if (this.readyState === 4) {
                        handleProgress(true);
                    }
                });

                return origSend.apply(this, args);
            };

            const originalFetch = window.fetch;
            window.fetch = async function(...args) {
                const response = await originalFetch(...args);
                const url = response.url;
                if (url.includes('GetShoppingResults')) {
                    const cloned = response.clone();
                    (async () => {
                        try {
                            const reader = cloned.body.getReader();
                            const decoder = new TextDecoder('utf-8');
                            while (true) {
                                const { done, value } = await reader.read();
                                if (done) {
                                    if (window.onChunkReceived) {
                                        window.onChunkReceived(url, "", true);
                                    }
                                    break;
                                }
                                const chunkText = decoder.decode(value, { stream: true });
                                if (window.onChunkReceived) {
                                    window.onChunkReceived(url, chunkText, false);
                                }
                            }
                        } catch (err) {
                            console.error(err);
                        }
                    })();
                }
                return response;
            };
        })();
        """
        page.add_init_script(js_hook)

        try:
            logger.info("Navigating to Google Flights...")
            page.goto("https://www.google.com/travel/flights")
            
            # Origin search
            logger.info(f"Entering origin: {origin}...")
            origin_selectors = [
                "input[aria-label='Where from?']",
                "input[placeholder='Where from?']",
                "[placeholder='Where from?']"
            ]
            origin_input = None
            for selector in origin_selectors:
                loc = page.locator(selector).first
                try:
                    if loc.is_visible(timeout=2000):
                        origin_input = loc
                        break
                except Exception:
                    pass
            
            if origin_input is None:
                origin_input = page.locator("input[aria-label='Where from?']").first
                
            origin_input.click()
            page.wait_for_timeout(1000)
            
            page.keyboard.press("Control+A")
            page.wait_for_timeout(200)
            page.keyboard.press("Backspace")
            page.wait_for_timeout(200)
            
            page.keyboard.type(origin, delay=100)
            page.wait_for_timeout(1500)
            
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            
            # Destination search
            logger.info(f"Entering destination: {destination}...")
            page.get_by_placeholder("Where to?").first.fill(destination)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)

            # Close dates calendar if open
            done_btn = page.get_by_role("button", name="Done").last
            if done_btn.is_visible():
                done_btn.click()
                page.wait_for_timeout(1000)

            # Dates input
            logger.info(f"Entering departure date: {departure_date}...")
            page.get_by_placeholder("Departure").first.fill(departure_date)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)

            logger.info(f"Entering return date: {return_date}...")
            page.get_by_placeholder("Return").first.fill(return_date)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)

            if done_btn.is_visible():
                done_btn.click()
                page.wait_for_timeout(1000)

            # Execution
            search_btn = page.get_by_role("button", name="Search")
            logger.info("Clicking search button...")
            search_btn.click()

            logger.info("Waiting for flight results to load and stream (max 30s)...")
            start_time = time.time()
            has_flights = False
            while (time.time() - start_time) < 30:
                page.wait_for_timeout(500)
                
                # Check if we have successfully parsed stream chunks
                if len(stream_parser.parsed_chunks) > 0 or stream_finished[0]:
                    logger.info(f"Stopping wait. Chunks parsed: {len(stream_parser.parsed_chunks)}, Stream finished: {stream_finished[0]}")
                    has_flights = True
                    break
            
            if not has_flights:
                logger.warning("Scraper finished waiting without capturing any chunks.")
                
        except Exception as e:
            logger.error(f"Execution error encountered during scraping SFO to {destination}: {e}")
        
        # Flush the parser final time
        stream_parser.feed("", is_finished=True)
        browser.close()
        
        return stream_parser.parsed_chunks

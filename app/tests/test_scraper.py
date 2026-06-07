import pytest
from unittest.mock import patch
from app.scraper.scraper import run_flight_scrape

def test_scraper_runs_with_mocked_network():
    """
    Verify that the scraper function launches the browser, navigates, and attempts to interact with dates.
    We patch the sync_playwright function to mock browser operations so no actual network connections are made.
    """
    with patch('app.scraper.scraper.sync_playwright') as mock_playwright:
        mock_browser = mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value
        mock_context = mock_browser.new_context.return_value
        mock_page = mock_context.new_page.return_value

        # Mock the done button check
        mock_page.get_by_role.return_value.last.is_visible.return_value = False

        # Run the scraper
        run_flight_scrape(
            origin="SFO", 
            destination="JFK", 
            departure_date="2026-06-20", 
            return_date="2026-06-27"
        )

        # Verify browser was launched and page was opened
        mock_playwright.return_value.__enter__.return_value.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.goto.assert_called_with("https://www.google.com/travel/flights")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

def test_get_flights_endpoint():
    """
    Tests the GET /api/flights endpoint.
    """
    # Mock database query results
    mock_flights = [
        MagicMock(
            id=1, 
            origin="SFO", 
            destination="LAX", 
            departure_date="2026-06-20", 
            return_date="2026-06-27",
            price=150.00,
            airline="United",
            stops=0,
            delete_indicator=0
        )
    ]
    
    with patch('app.main.get_db'), \
         patch('sqlalchemy.orm.Session.query') as mock_query:
        
        # Configure mock query to return our list
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_flights
        
        response = client.get("/api/flights")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["destination"] == "LAX"
        assert "booking_url" in data[0]

def test_scraper_status_endpoint():
    """
    Tests the GET /api/scraper/status endpoint.
    """
    with patch('app.main.get_db'), \
         patch('sqlalchemy.orm.Session.query') as mock_query:
        
        mock_query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        response = client.get("/api/scraper/status")
        assert response.status_code == 200
        assert response.json() == []

def test_manual_scraper_trigger():
    """
    Tests the POST /api/scraper/run endpoint.
    """
    with patch('app.main.run_full_extraction_job'):
        response = client.post("/api/scraper/run")
        assert response.status_code == 200
        assert response.json()["message"] == "Scraper job started in background."

from unittest.mock import MagicMock

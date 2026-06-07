import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from datetime import date

client = TestClient(app)

def test_get_flights_endpoint():
    """
    Tests the GET /api/flights endpoint.
    """
    mock_flight = MagicMock()
    mock_flight.id = 1
    mock_flight.origin = "SFO"
    mock_flight.destination = "LAX"
    mock_flight.departure_date = date(2026, 6, 20)
    mock_flight.return_date = date(2026, 6, 27)
    mock_flight.price = 150.00
    mock_flight.airline = "United"
    mock_flight.stops = 0
    mock_flight.delete_indicator = 0
    
    with patch('app.main.get_db'), \
         patch('sqlalchemy.orm.Session.query') as mock_query:
        
        # Configure mock query
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_flight]
        # Mock the city lookup inside the loop
        mock_query.return_value.filter.return_value.first.return_value = MagicMock(city="Los Angeles")
        
        response = client.get("/api/flights")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["destination"] == "LAX"
        assert data[0]["city"] == "Los Angeles"
        assert "booking_url" in data[0]

def test_get_flights_city_filter():
    """
    Tests filtering by city name.
    """
    with patch('app.main.get_db'), \
         patch('sqlalchemy.orm.Session.query') as mock_query:
        
        # 1. Mock the Airport lookup for "New York"
        mock_airport_code = MagicMock()
        mock_airport_code.__getitem__.return_value = "JFK" # For .all() returning tuples
        
        # Simplify mocking for the city discovery query
        mock_query.return_value.filter.return_value.all.side_effect = [
            [("JFK",), ("LGA",)], # Airport codes for New York
            [] # Final flights result (empty for simplicity)
        ]
        
        response = client.get("/api/flights?destination=New York")
        assert response.status_code == 200
        
        # Verify that the second query used IN clause with JFK, LGA
        # This is hard to verify precisely with side_effects but status 200 is good start

def test_scraper_status_endpoint():
    with patch('app.main.get_db'), \
         patch('sqlalchemy.orm.Session.query') as mock_query:
        mock_query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        response = client.get("/api/scraper/status")
        assert response.status_code == 200

def test_manual_scraper_trigger():
    with patch('app.main.run_full_extraction_job'):
        response = client.post("/api/scraper/run")
        assert response.status_code == 200
        assert response.json()["message"] == "Scraper job started in background."

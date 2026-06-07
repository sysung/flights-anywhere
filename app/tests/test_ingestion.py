import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.db.database import SessionLocal, Base, engine
from app.db.models import Flight, ScraperLog
from app.scraper.extractor import run_full_extraction_job

def test_full_ingestion_flow():
    """
    Tests the high-level ingestion job by mocking the scraper and extractor.
    Verifies that records are correctly inserted into the test database.
    """
    # 1. Setup: Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Clear existing data for isolation
    db.query(Flight).delete()
    db.query(ScraperLog).delete()
    db.commit()

    # 2. Mocking
    # Mock run_flight_scrape to return dummy chunks
    # Mock extract_flights_info to return a list of flight dicts
    mock_flight_data = [
        {
            "arrival_airport": "LAX",
            "airline": "Test Airways",
            "price": 99.99,
            "duration": "1 stop"
        }
    ]

    with patch('app.scraper.extractor.run_flight_scrape', return_value=[{"mock": "chunk"}]), \
         patch('app.scraper.extractor.extract_flights_info', return_value=mock_flight_data):
        
        # 3. Execution: Run the ingestion job
        # We only test one target to keep it fast
        run_full_extraction_job(targets=["LAX"])

    # 4. Verification
    # Check if Flight was inserted
    flights = db.query(Flight).all()
    assert len(flights) == 1
    assert flights[0].destination == "LAX"
    assert flights[0].price == Decimal("99.99")
    assert flights[0].airline == "Test Airways"
    assert flights[0].stops == 1

    # Check if ScraperLog was created and marked SUCCESS
    logs = db.query(ScraperLog).all()
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].records_inserted == 1

    db.close()

def test_ingestion_soft_delete():
    """
    Tests that the ingestion job correctly soft-deletes obsolete records.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. Create an existing "old" flight record
    old_flight = Flight(
        origin="SFO",
        destination="JFK",
        departure_date=date.today() + timedelta(days=14),
        airline="Legacy Air",
        price=Decimal("500.00"),
        last_seen=date.today() - timedelta(days=1), # Older than current run
        delete_indicator=0
    )
    db.add(old_flight)
    db.commit()

    # 2. Run ingestion with NO new data returned for JFK
    with patch('app.scraper.extractor.run_flight_scrape', return_value=[]), \
         patch('app.scraper.extractor.extract_flights_info', return_value=[]):
        
        run_full_extraction_job(targets=["JFK"])

    # 3. Verify that the old flight is now soft-deleted
    updated_flight = db.query(Flight).filter(Flight.airline == "Legacy Air").first()
    assert updated_flight.delete_indicator == 1
    
    db.close()

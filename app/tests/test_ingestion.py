import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from db.database import SessionLocal, Base, engine
from db.models import Flight, ScraperLog, Airport
from app.scraper.extractor import run_full_extraction_job

def test_full_ingestion_job_submission():
    """
    Tests that the parallel ingestion job correctly submits tasks and logs the run.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(ScraperLog).delete()
    db.commit()

    # Mock run_flight_scrape to return a chunk, and Producer to avoid actual Kafka calls
    with patch('app.scraper.extractor.run_flight_scrape', return_value=[{"mock": "chunk"}]), \
         patch('app.scraper.extractor.FlightKafkaProducer') as mock_producer_class:
        
        mock_producer_instance = MagicMock()
        mock_producer_class.return_value = mock_producer_instance
        
        # Run job with small parameters
        run_full_extraction_job(targets=["LAX"], days_ahead=1, trip_lengths=[3])

    # Verify ScraperLog
    logs = db.query(ScraperLog).all()
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].records_inserted >= 0

    # Verify Producer was called
    assert mock_producer_instance.send_raw_chunk.called
    
    db.close()

def test_kafka_consumer_upsert():
    """
    Tests the ingestion logic inside the Kafka consumer.
    """
    from app.scraper.kafka_consumer import FlightKafkaConsumer
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Flight).delete()
    db.query(Airport).delete()
    db.commit()

    mock_flights = [
        {
            "arrival_airport": "LAX",
            "airline": "Test Airways",
            "price": 99.99,
            "duration": "1h 30m",
            "duration_minutes": 90,
            "booking_url": "http://test.com"
        }
    ]

    consumer = FlightKafkaConsumer()
    consumer.upsert_flights(mock_flights, "SFO", "2026-06-20", "2026-06-27")

    # Verify DB
    flight = db.query(Flight).filter(Flight.destination == "LAX").first()
    assert flight is not None
    from decimal import Decimal
    assert flight.price == Decimal("99.99")
    assert flight.duration_minutes == 90
    assert flight.booking_url == "http://test.com"

    airport = db.query(Airport).filter(Airport.code == "LAX").first()
    assert airport is not None
    
    db.close()

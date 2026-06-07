import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.database import SessionLocal
from app.db.models import Flight, Airport, ScraperLog
from app.scraper.scraper import run_flight_scrape
from app.scraper.date_utils import generate_date_matrix
from app.scraper.kafka_producer import FlightKafkaProducer

logger = logging.getLogger(__name__)

# Destinations we wish to scrape directly out of SFO
DEFAULT_TARGETS = ["LAX", "JFK", "HNL", "LHR", "CDG", "NRT", "ICN"]

def scrape_task(origin, dest, dep_date, ret_date):
    """
    Individual task for scraping a single route and date.
    Produces results to Kafka.
    """
    producer = FlightKafkaProducer()
    try:
        logger.info(f"Scraping {origin} to {dest} (dep: {dep_date}, ret: {ret_date})...")
        chunks = run_flight_scrape(origin, dest, dep_date, ret_date)
        if chunks:
            producer.send_raw_chunk(origin, dest, dep_date, ret_date, chunks)
            producer.flush()
            return True
        return False
    except Exception as e:
        logger.error(f"Error in scrape_task for {dest}: {e}")
        return False

def run_full_extraction_job(targets=None, days_ahead=7, trip_lengths=[3, 7]):
    """
    Ingestion job. Runs Playwright scraping in parallel for multiple destinations and dates.
    Results are streamed through Kafka.
    """
    if targets is None:
        targets = DEFAULT_TARGETS

    logger.info("Starting SFO parallel flight ingestion job...")
    db = SessionLocal()
    log = ScraperLog(status="RUNNING")
    db.add(log)
    db.commit()
    
    date_matrix = generate_date_matrix(days_ahead=days_ahead, trip_lengths=trip_lengths)
    
    tasks = []
    for dest in targets:
        for dep_date, ret_date in date_matrix:
            tasks.append(("SFO", dest, dep_date, ret_date))

    success_count = 0
    # Use a small number of workers for PoC
    max_workers = 3
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(scrape_task, *task): task for task in tasks}
            for future in as_completed(future_to_task):
                if future.result():
                    success_count += 1
        
        log.status = "SUCCESS"
        log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.records_inserted = success_count # In this async model, we track successful scrapes
        db.commit()
        logger.info(f"Ingestion pipeline tasks submitted: {success_count} successful scrapes.")
        
    except Exception as e:
        db.rollback()
        log.status = "FAILED"
        log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.error_message = str(e)
        db.commit()
        logger.error(f"Ingestion pipeline encountered critical error: {e}")
        raise e
    finally:
        db.close()


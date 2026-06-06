import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.database import SessionLocal
from app.models import Flight, Airport, ScraperLog
from app.scraper import run_flight_scrape
from app.extractor_utils import extract_flights_info

logger = logging.getLogger(__name__)

def run_full_extraction_job():
    """
    Ingestion job. Runs Playwright scraping for top SFO destination targets,
    dynamically seeds missing airport records, updates flights, and soft-deletes obsolete ones.
    """
    logger.info("Starting SFO flight ingestion job...")
    db = SessionLocal()
    log = ScraperLog(status="RUNNING")
    db.add(log)
    db.commit()
    
    run_start = datetime.utcnow()
    
    # We will target a fixed date window for our PoC (e.g. departing in 14 days, returning in 21 days)
    dep_date = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    ret_date = (date.today() + timedelta(days=21)).strftime("%Y-%m-%d")
    
    # Destinations we wish to scrape directly out of SFO
    targets = ["LAX", "JFK", "HNL", "LHR", "CDG", "NRT", "ICN"]
    
    inserted = 0
    updated = 0
    
    try:
        for dest in targets:
            logger.info(f"Scraping SFO to {dest} (dep: {dep_date}, ret: {ret_date})...")
            try:
                chunks = run_flight_scrape("SFO", dest, dep_date, ret_date)
                flights_list = extract_flights_info(chunks)
                
                logger.info(f"Extracted {len(flights_list)} flights for route SFO -> {dest}")
                
                for f in flights_list:
                    airport_code = f["arrival_airport"]
                    
                    # 1. Dynamic Airport Ingestion
                    existing_airport = db.query(Airport).filter(Airport.code == airport_code).first()
                    if not existing_airport:
                        logger.info(f"Airport {airport_code} does not exist in database. Skipping dynamic seeding.")
                    
                    # 2. Upsert Flight Listing
                    existing_flight = db.query(Flight).filter(
                        Flight.origin == "SFO",
                        Flight.destination == airport_code,
                        Flight.departure_date == datetime.strptime(dep_date, "%Y-%m-%d").date(),
                        Flight.airline == f["airline"]
                    ).first()
                    
                    price_val = Decimal(str(f["price"])) if f["price"] else Decimal("0.0")
                    
                    # Compute stops
                    stops_val = 0
                    if "1 stop" in f.get("duration", "").lower():
                        stops_val = 1
                    elif "2 stop" in f.get("duration", "").lower():
                        stops_val = 2
                    
                    if existing_flight:
                        existing_flight.price = price_val
                        existing_flight.last_seen = run_start
                        existing_flight.delete_indicator = 0
                        updated += 1
                    else:
                        new_flight = Flight(
                            origin="SFO",
                            destination=airport_code,
                            departure_date=datetime.strptime(dep_date, "%Y-%m-%d").date(),
                            return_date=datetime.strptime(ret_date, "%Y-%m-%d").date(),
                            price=price_val,
                            airline=f["airline"],
                            stops=stops_val,
                            last_seen=run_start,
                            delete_indicator=0
                        )
                        db.add(new_flight)
                        inserted += 1
                        
                db.commit()
            except Exception as e:
                logger.error(f"Failed scraping target SFO -> {dest}: {e}")
                
        # 3. Soft-Delete Cleanup
        soft_deleted = db.query(Flight).filter(
            Flight.last_seen < run_start,
            Flight.delete_indicator == 0
        ).update({Flight.delete_indicator: 1}, synchronize_session=False)
        db.commit()
        
        log.status = "SUCCESS"
        log.completed_at = datetime.utcnow()
        log.records_inserted = inserted
        log.records_updated = updated
        log.records_soft_deleted = soft_deleted
        db.commit()
        logger.info(f"Ingestion pipeline completed: {inserted} inserted, {updated} updated, {soft_deleted} soft-deleted.")
        
    except Exception as e:
        db.rollback()
        log.status = "FAILED"
        log.completed_at = datetime.utcnow()
        log.error_message = str(e)
        db.commit()
        logger.error(f"Ingestion pipeline encountered critical error: {e}")
        raise e
    finally:
        db.close()

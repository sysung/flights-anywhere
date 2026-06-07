from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import logging

from db.database import get_db, Base, engine
from db.models import Flight, ScraperLog
from app.core.config import settings
from db.schemas import FlightOut, ScraperLogOut
from app.scraper.extractor import run_full_extraction_job

logger = logging.getLogger(__name__)

# Start background scheduler
scheduler = None
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(run_full_extraction_job, 'interval', hours=12)
except Exception as e:
    logger.error(f"Failed to initialize background scheduler: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # Initial Seed
        from app.scraper.seed_airports import seed_airports
        seed_airports()
        
    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize database tables: {e}")

    # Startup: Start scheduler
    if scheduler:
        try:
            scheduler.start()
            logger.info(f"Background flight scheduler started successfully with timezone: {settings.timezone}")
        except Exception as e:
            logger.error(f"Failed to start background scheduler: {e}")

    # Startup: Initial scrape run in a background thread to prevent blocking startup
    import threading
    threading.Thread(target=run_full_extraction_job, daemon=True).start()

    yield

    # Shutdown: Stop scheduler
    if scheduler:
        try:
            scheduler.shutdown()
            logger.info("Background scheduler shut down successfully.")
        except Exception as e:
            logger.error(f"Failed to shut down background scheduler: {e}")

app = FastAPI(title="SFO Anywhere Flights Search API", lifespan=lifespan)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
]
if os.getenv("RAILWAY_PUBLIC_DOMAIN"):
    allowed_origins.append(f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/flights", response_model=List[FlightOut])
def get_flights(
    max_price: Optional[float] = None,
    airlines: Optional[str] = None,
    trip_lengths: Optional[str] = None,
    destination: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns active SFO flight options matching filter criteria.
    """
    from db.models import Airport
    from sqlalchemy.orm import joinedload
    
    # We use a join to get the city name from the airports table
    query = db.query(Flight).filter(Flight.delete_indicator == 0)
    
    if max_price is not None:
        query = query.filter(Flight.price <= max_price)
        
    if airlines:
        airline_list = [a.strip() for a in airlines.split(",") if a.strip()]
        if airline_list:
            query = query.filter(Flight.airline.in_(airline_list))

    if destination:
        # Check if the destination is a city name or an airport code
        related_airports = db.query(Airport.code).filter(
            (Airport.city.ilike(f"%{destination}%")) | 
            (Airport.city_code.ilike(destination)) |
            (Airport.code.ilike(destination))
        ).all()
        
        if related_airports:
            codes = [r[0] for r in related_airports]
            query = query.filter(Flight.destination.in_(codes))
        else:
            query = query.filter(Flight.destination == destination.upper())

    if trip_lengths:
        try:
            lengths = [int(l.strip()) for l in trip_lengths.split(",") if l.strip()]
            if lengths:
                from sqlalchemy import func
                if "sqlite" in str(db.get_bind().url):
                    query = query.filter((func.julianday(Flight.return_date) - func.julianday(Flight.departure_date)).in_(lengths))
                else:
                    query = query.filter((Flight.return_date - Flight.departure_date).in_(lengths))
        except Exception as e:
            logger.error(f"Failed to apply trip_lengths filter: {e}")
            
    flights = query.order_by(Flight.price.asc()).all()
    
    # Add city names to the response objects
    # This is a bit manual since we didn't add a formal relationship yet
    for f in flights:
        airport = db.query(Airport).filter(Airport.code == f.destination).first()
        if airport:
            f.city = airport.city
            
    return flights

@app.get("/api/scraper/status", response_model=List[ScraperLogOut])
def get_scraper_status(db: Session = Depends(get_db)):
    """
    Returns execution status logs for pipeline auditing and debugging.
    """
    return db.query(ScraperLog).order_by(ScraperLog.started_at.desc()).limit(10).all()

@app.post("/api/scraper/run")
def trigger_scraper_run(background_tasks: BackgroundTasks):
    """
    Manually triggers the full extraction job in a background task.
    """
    logger.info("Manual scraper run triggered via API.")
    background_tasks.add_task(run_full_extraction_job)
    return {"message": "Scraper job started in background."}

# Chatbot assistant route
from pydantic import BaseModel
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def post_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Processes chat requests using the Gemini AI agent.
    """
    try:
        from app.core.agent import run_chatbot_agent
    except ImportError:
        return {
            "response_text": "Assistant offline. Please wait until Task 5 is completed.",
            "filters": {"max_price": None, "airlines": None}
        }
        
    # Fetch active flights to summarize in LLM prompt context
    flights = db.query(Flight).filter(Flight.delete_indicator == 0).all()
    summary_lines = []
    for f in flights:
        summary_lines.append(f"- To {f.destination} on {f.airline} for ${f.price:.2f} (stops: {f.stops})")
    flights_summary = "\n".join(summary_lines) if summary_lines else "No active flights found in database."
    
    agent_payload = run_chatbot_agent(req.message, flights_summary)
    return agent_payload

# Serve compiled Vite static assets on "/"
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
elif os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

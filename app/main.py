from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import logging

from app.database import get_db, Base, engine
from app.models import Flight, ScraperLog
from app.schemas import FlightOut, ScraperLogOut
from app.extractor import run_full_extraction_job

logger = logging.getLogger(__name__)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SFO Anywhere Flights Search API")

# Enable CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start background scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    # Runs the ingestion job every 12 hours
    scheduler.add_job(run_full_extraction_job, 'interval', hours=12)
    scheduler.start()
    logger.info("Background flight scheduler started successfully.")
except Exception as e:
    logger.error(f"Failed to initialize background scheduler: {e}")

@app.get("/api/flights", response_model=List[FlightOut])
def get_flights(
    max_price: Optional[float] = None,
    airlines: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns active SFO flight options matching filter criteria.
    """
    query = db.query(Flight).filter(Flight.delete_indicator == 0)
    
    if max_price is not None:
        query = query.filter(Flight.price <= max_price)
        
    if airlines:
        airline_list = [a.strip() for a in airlines.split(",") if a.strip()]
        if airline_list:
            query = query.filter(Flight.airline.in_(airline_list))
            
    flights = query.order_by(Flight.price.asc()).all()
    
    # Construct deep-link booking URLs dynamically
    out_flights = []
    for f in flights:
        booking_url = f"https://www.google.com/travel/flights?q=Flights%20from%20{f.origin}%20to%20{f.destination}%20on%20{f.departure_date}"
        if f.return_date:
            booking_url += f"%20returning%20{f.return_date}"
            
        f_dict = f.__dict__.copy()
        f_dict["booking_url"] = booking_url
        out_flights.append(FlightOut(**f_dict))
        
    return out_flights

@app.get("/api/scraper/status", response_model=List[ScraperLogOut])
def get_scraper_status(db: Session = Depends(get_db)):
    """
    Returns execution status logs for pipeline auditing and debugging.
    """
    return db.query(ScraperLog).order_by(ScraperLog.started_at.desc()).limit(10).all()

# Chatbot placeholder endpoint (Task 5 will define the agent, but main router is set up here)
from pydantic import BaseModel
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def post_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Processes chat requests using the Gemini AI agent.
    """
    try:
        from app.agent import run_chatbot_agent
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

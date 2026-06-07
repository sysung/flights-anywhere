from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal

class FlightOut(BaseModel):
    id: int
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date]
    price: Decimal
    airline: str
    stops: int
    booking_url: str
    
    model_config = {
        "from_attributes": True
    }

class ScraperLogOut(BaseModel):
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    records_inserted: int
    records_updated: int
    records_soft_deleted: int
    error_message: Optional[str]

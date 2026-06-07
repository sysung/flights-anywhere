from pydantic import BaseModel, computed_field
from datetime import date, datetime
from typing import Optional
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
    city: Optional[str] = None

    @computed_field
    @property
    def booking_url(self) -> str:
        url = f"https://www.google.com/travel/flights?q=Flights%20from%20{self.origin}%20to%20{self.destination}%20on%20{self.departure_date}"
        if self.return_date:
            url += f"%20returning%20{self.return_date}"
        return url
    
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

    model_config = {
        "from_attributes": True
    }

from sqlalchemy import Column, String, Boolean, Numeric, Integer, Date, DateTime, Text, Index
from datetime import datetime, timezone
from db.database import Base

class Airport(Base):
    __tablename__ = "airports"
    code = Column(String(3), primary_key=True)
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    city_code = Column(String(10))
    country = Column(String(100), nullable=False)
    is_international = Column(Boolean, default=True)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    origin = Column(String(3), default="SFO", nullable=False)
    destination = Column(String(3), nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date)
    price = Column(Numeric(10, 2), nullable=False)
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(20))
    stops = Column(Integer, default=0)
    duration_minutes = Column(Integer)
    booking_url = Column(Text)
    delete_indicator = Column(Integer, default=0)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# Index setup
Index('idx_flights_search', Flight.origin, Flight.departure_date, Flight.price, postgresql_where=(Flight.delete_indicator == 0))
Index('idx_flights_dest', Flight.destination, Flight.delete_indicator)
Index('idx_flights_full_search', Flight.origin, Flight.destination, Flight.departure_date, Flight.return_date)

class ScraperLog(Base):
    __tablename__ = "scraper_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False)  # 'RUNNING', 'SUCCESS', 'FAILED'
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_soft_deleted = Column(Integer, default=0)
    error_message = Column(Text)

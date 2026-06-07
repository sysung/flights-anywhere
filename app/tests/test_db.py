import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.database import Base
from app.db.models import Airport, Flight, ScraperLog

# Configure a test database session
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_database_connection_and_schema():
    # 1. Bind and create all tables in Postgres
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # 2. Verify dynamic insert of an Airport
        test_airport = Airport(
            code="TST",
            name="Test International",
            city="Test City",
            country="Test Country",
            is_international=True
        )
        db.add(test_airport)
        db.commit()
        
        db_airport = db.query(Airport).filter(Airport.code == "TST").first()
        assert db_airport is not None
        assert db_airport.city == "Test City"
        
        # 3. Clean up the test airport
        db.delete(db_airport)
        db.commit()
        
        # 4. Verify clean deletion
        deleted_airport = db.query(Airport).filter(Airport.code == "TST").first()
        assert deleted_airport is None
        
    finally:
        db.close()

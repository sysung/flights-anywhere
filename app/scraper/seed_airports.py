import logging
from app.db.database import SessionLocal
from app.db.models import Airport
from sqlalchemy import text

logger = logging.getLogger(__name__)

# major airport-to-city mappings
SEED_AIRPORTS = [
    # New York Area
    {"code": "JFK", "name": "John F. Kennedy International Airport", "city": "New York", "city_code": "NYC", "country": "USA"},
    {"code": "LGA", "name": "LaGuardia Airport", "city": "New York", "city_code": "NYC", "country": "USA"},
    {"code": "EWR", "name": "Newark Liberty International Airport", "city": "New York", "city_code": "NYC", "country": "USA"},
    
    # London Area
    {"code": "LHR", "name": "London Heathrow Airport", "city": "London", "city_code": "LON", "country": "United Kingdom"},
    {"code": "LGW", "name": "London Gatwick Airport", "city": "London", "city_code": "LON", "country": "United Kingdom"},
    {"code": "STN", "name": "London Stansted Airport", "city": "London", "city_code": "LON", "country": "United Kingdom"},
    
    # Bay Area
    {"code": "SFO", "name": "San Francisco International Airport", "city": "San Francisco", "city_code": "SFO", "country": "USA"},
    {"code": "OAK", "name": "Oakland International Airport", "city": "San Francisco", "city_code": "SFO", "country": "USA"},
    {"code": "SJC", "name": "San Jose International Airport", "city": "San Francisco", "city_code": "SFO", "country": "USA"},
    
    # Tokyo Area
    {"code": "NRT", "name": "Narita International Airport", "city": "Tokyo", "city_code": "TYO", "country": "Japan"},
    {"code": "HND", "name": "Haneda Airport", "city": "Tokyo", "city_code": "TYO", "country": "Japan"},
    
    # Paris Area
    {"code": "CDG", "name": "Charles de Gaulle Airport", "city": "Paris", "city_code": "PAR", "country": "France"},
    {"code": "ORY", "name": "Orly Airport", "city": "Paris", "city_code": "PAR", "country": "France"},
    
    # Others
    {"code": "LAX", "name": "Los Angeles International Airport", "city": "Los Angeles", "city_code": "LAX", "country": "USA"},
    {"code": "HNL", "name": "Daniel K. Inouye International Airport", "city": "Honolulu", "city_code": "HNL", "country": "USA"},
    {"code": "ICN", "name": "Incheon International Airport", "city": "Seoul", "city_code": "SEL", "country": "South Korea"},
]

def seed_airports():
    db = SessionLocal()
    try:
        logger.info("Seeding static airport data...")
        for data in SEED_AIRPORTS:
            existing = db.query(Airport).filter(Airport.code == data["code"]).first()
            if existing:
                existing.name = data["name"]
                existing.city = data["city"]
                existing.city_code = data["city_code"]
                existing.country = data["country"]
            else:
                new_airport = Airport(**data)
                db.add(new_airport)
        db.commit()
        logger.info(f"Successfully seeded {len(SEED_AIRPORTS)} airports.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding airports: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_airports()

import json
import logging
import os
from confluent_kafka import Consumer, KafkaError
from app.scraper.extractor_utils import extract_flights_info
from db.database import SessionLocal
from db.models import Flight, Airport
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class FlightKafkaConsumer:
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.topic = "raw-flight-data"
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': 'flight-extractor-group',
            'auto.offset.reset': 'earliest'
        })

    def start(self):
        self.consumer.subscribe([self.topic])
        logger.info(f"Kafka Consumer started on topic {self.topic}...")
        
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                self.process_message(msg)
        finally:
            self.consumer.close()

    def process_message(self, msg):
        try:
            data = json.loads(msg.value().decode('utf-8'))
            origin = data['origin']
            dest = data['destination']
            dep_date = data['departure_date']
            ret_date = data['return_date']
            chunks = data['chunks']

            logger.info(f"Processing flight data for {origin} -> {dest} ({dep_date})")
            
            flights_list = extract_flights_info(chunks, origin=origin, dest=dest, dep_date=dep_date, ret_date=ret_date)
            self.upsert_flights(flights_list, origin, dep_date, ret_date)
            
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")

    def upsert_flights(self, flights_list, origin, dep_date, ret_date):
        db = SessionLocal()
        run_start = datetime.now()
        try:
            for f in flights_list:
                airport_code = f["arrival_airport"]
                
                # Dynamic Airport Ingestion
                existing_airport = db.query(Airport).filter(Airport.code == airport_code).first()
                if not existing_airport:
                    new_airport = Airport(
                        code=airport_code,
                        name=f"{airport_code} International Airport",
                        city=airport_code,
                        country="Unknown",
                        is_international=True
                    )
                    db.add(new_airport)
                    db.commit()
                
                # Upsert Flight Listing
                existing_flight = db.query(Flight).filter(
                    Flight.origin == origin,
                    Flight.destination == airport_code,
                    Flight.departure_date == datetime.strptime(dep_date, "%Y-%m-%d").date(),
                    Flight.airline == f["airline"]
                ).first()
                
                price_val = Decimal(str(f["price"])) if f["price"] else Decimal("0.0")
                
                if existing_flight:
                    existing_flight.price = price_val
                    existing_flight.duration_minutes = f.get("duration_minutes", 0)
                    existing_flight.booking_url = f.get("booking_url")
                    existing_flight.last_seen = run_start
                    existing_flight.delete_indicator = 0
                else:
                    new_flight = Flight(
                        origin=origin,
                        destination=airport_code,
                        departure_date=datetime.strptime(dep_date, "%Y-%m-%d").date(),
                        return_date=datetime.strptime(ret_date, "%Y-%m-%d").date() if ret_date else None,
                        price=price_val,
                        airline=f["airline"],
                        duration_minutes=f.get("duration_minutes", 0),
                        booking_url=f.get("booking_url"),
                        last_seen=run_start,
                        delete_indicator=0
                    )
                    db.add(new_flight)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error upserting flights from Kafka: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    consumer = FlightKafkaConsumer()
    consumer.start()

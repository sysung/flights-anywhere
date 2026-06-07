import json
import logging
from confluent_kafka import Producer
import os

logger = logging.getLogger(__name__)

class FlightKafkaProducer:
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.topic = "raw-flight-data"
        self.producer = Producer({
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'flight-scraper-producer'
        })

    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def send_raw_chunk(self, origin, dest, dep_date, ret_date, chunks):
        """
        Sends raw scraped chunks to Kafka.
        """
        payload = {
            "origin": origin,
            "destination": dest,
            "departure_date": dep_date,
            "return_date": ret_date,
            "chunks": chunks
        }
        try:
            self.producer.produce(
                self.topic, 
                json.dumps(payload).encode('utf-8'), 
                callback=self.delivery_report
            )
            # Flush to ensure messages are sent
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Error producing to Kafka: {e}")

    def flush(self):
        self.producer.flush()

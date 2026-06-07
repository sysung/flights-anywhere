import unittest
from unittest.mock import MagicMock, patch
from app.scraper.kafka_producer import FlightKafkaProducer

class TestKafkaProducer(unittest.TestCase):
    @patch('app.scraper.kafka_producer.Producer')
    def test_send_raw_chunk(self, mock_producer_class):
        mock_producer_instance = MagicMock()
        mock_producer_class.return_value = mock_producer_instance
        
        producer = FlightKafkaProducer()
        producer.send_raw_chunk("SFO", "LAX", "2026-06-20", "2026-06-27", [{"raw": "data"}])
        
        # Verify producer.produce was called
        assert mock_producer_instance.produce.called
        args, kwargs = mock_producer_instance.produce.call_args
        assert args[0] == "raw-flight-data"
        assert b"SFO" in args[1]
        assert b"LAX" in args[1]

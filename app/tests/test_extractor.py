from app.extractor_utils import format_time_array, find_price_in_flight

def test_format_time_array():
    assert format_time_array([14, 30]) == "14:30"
    assert format_time_array([8, 5]) == "08:05"
    assert format_time_array([]) == "Unknown"
    assert format_time_array(None) == "Unknown"

def test_find_price_in_flight():
    # Test protobuf structure Case 1: USD price in details
    mock_flight_1 = {
        "some_key": {
            "_type": "protobuf",
            "data": {
                "3": {
                    "1": 55000,
                    "3": "USD"
                }
            }
        }
    }
    assert find_price_in_flight(mock_flight_1) == 550.00
    
    # Test protobuf structure Case 2
    mock_flight_2 = [
        {
            "_type": "protobuf",
            "data": {
                "2": "USD",
                "3": {
                    "1": 120000
                }
            }
        }
    ]
    assert find_price_in_flight(mock_flight_2) == 1200.00

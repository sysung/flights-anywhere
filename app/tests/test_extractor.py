from app.scraper.extractor_utils import format_time_array, find_price_in_flight, extract_flights_info

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

def test_extract_flights_info():
    # details[0] must be length 2 string (airline code)
    # details[1] must be a list containing the airline name
    details_1 = [
        "UA",              # details[0]
        ["United Airlines"], # details[1]
        "ignored",         # details[2]
        "SFO",             # details[3]
        "ignored",         # details[4]
        [10, 30],          # details[5]
        "LAX",             # details[6]
        "ignored",         # details[7]
        [12, 0],           # details[8]
        90                 # details[9]
    ]
    
    details_2 = [
        "DL",
        ["Delta"],
        "ignored",
        "SFO",
        "ignored",
        [15, 0],
        "JFK",
        "ignored",
        [21, 30],
        330
    ]
    
    # Each flight is a list where index 0 is the details list.
    # The signature check requires first_item (candidate[0]) to have length >= 3.
    flight_1 = [details_1, "ignored", "ignored"]
    flight_2 = [details_2, "ignored", "ignored"]
    
    candidate = [flight_1, flight_2]
    
    # Add price protobuf to flight 1
    flight_1.append({
        "_type": "protobuf",
        "data": {
            "3": {
                "1": 15000,
                "3": "USD"
            }
        }
    })
    
    # Signature path: chunk[0][2][3][0]
    level_3 = [candidate]
    level_2 = [None, None, None, level_3]
    level_1 = [None, None, level_2]
    
    chunk = [level_1]
    mock_chunks = [chunk]
    
    flights = extract_flights_info(mock_chunks, origin="SFO", dep_date="2026-06-20", ret_date="2026-06-27")
    assert len(flights) == 2
    assert flights[0]["airline"] == "United Airlines"
    assert flights[0]["price"] == 150.00
    assert flights[0]["duration"] == "1h 30m"
    assert flights[0]["duration_minutes"] == 90
    assert "https://www.google.com/travel/flights?q=Flights%20to%20LAX%20from%20SFO%20on%202026-06-20%20returning%202026-06-27" in flights[0]["booking_url"]
    assert flights[1]["airline"] == "Delta"
    assert flights[1]["arrival_airport"] == "JFK"
    assert flights[1]["duration_minutes"] == 330
    assert "https://www.google.com/travel/flights?q=Flights%20to%20JFK%20from%20SFO%20on%202026-06-20%20returning%202026-06-27" in flights[1]["booking_url"]

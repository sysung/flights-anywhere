import os
import json
import logging

logger = logging.getLogger(__name__)

def has_flight_signature(obj):
    """Recursively search for flight list signature in the parsed JSON object."""
    return extract_flights_list([obj]) is not None


def extract_flights_list(data):
    """Find the flights list in the parsed chunks via direct lookup structure."""
    if isinstance(data, list):
        for index, chunk in enumerate(data):
            try:
                candidate = chunk[0][2][3][0]
                if isinstance(candidate, list) and len(candidate) > 0:
                    first_item = candidate[0]
                    if isinstance(first_item, list) and len(first_item) >= 3:
                        if isinstance(first_item[0], list) and len(first_item[0]) >= 2:
                            if isinstance(first_item[0][0], str) and len(first_item[0][0]) == 2:
                                return candidate
            except (IndexError, TypeError):
                # Expected when traversing structure candidates that don't match the signature
                pass
    return None


def format_time_array(arr):
    """Format time array [hour, minute] safely into HH:MM format."""
    if isinstance(arr, list) and len(arr) > 0:
        hour = arr[0]
        minute = arr[1] if len(arr) > 1 else 0
        if hour is not None and minute is not None:
            try:
                return f"{hour:02d}:{minute:02d}"
            except (TypeError, ValueError) as e:
                logger.debug(f"Failed formatting time array {arr}: {e}")
    return "Unknown"


def find_price_in_flight(flight):
    """Search the flight object recursively for currency USD and its associated price."""
    def search(obj):
        if isinstance(obj, dict):
            if obj.get('_type') == 'protobuf':
                data = obj.get('data', {})
                # Case 1: {'1': value, '2': ..., '3': {'1': price_val, '2': ..., '3': 'USD'}}
                if isinstance(data.get('3'), dict) and '1' in data['3']:
                    price_val = data['3']['1']
                    if isinstance(price_val, (int, float)):
                        return price_val
                # Case 2: {'1': ..., '2': 'USD', '3': {'1': price_val}}
                if data.get('2') == 'USD' and isinstance(data.get('3'), dict) and '1' in data['3']:
                    price_val = data['3']['1']
                    if isinstance(price_val, (int, float)):
                        return price_val
            for val in obj.values():
                res = search(val)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = search(item)
                if res is not None:
                    return res
        return None
    
    val = search(flight)
    if val is not None:
        return val / 100.0
    return None


def extract_flights_info(parsed_chunks, origin=None, dest=None, dep_date=None, ret_date=None):
    """Extract flight details from parsed stream chunks and return a list of dicts."""
    flights_list = extract_flights_list(parsed_chunks)
    if not flights_list:
        logger.warning("Could not find the flights list in the captured data.")
        return []
        
    logger.info(f"Found flights list containing {len(flights_list)} flights.")
    extracted_flights = []
    
    for idx, flight in enumerate(flights_list):
        try:
            details = flight[0]
            airline_code = details[0]
            airline_name = details[1][0] if (isinstance(details[1], list) and len(details[1]) > 0) else airline_code
            dep_airport = details[3]
            dep_time = format_time_array(details[5])
            arr_airport = details[6]
            arr_time = format_time_array(details[8])
            duration = details[9] # Total travel time in minutes
            duration_str = f"{duration // 60}h {duration % 60}m" if isinstance(duration, int) else "Unknown"
            price = find_price_in_flight(flight)
            
            # Generate fallback booking URL
            booking_url = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest or arr_airport}%20from%20{origin or dep_airport}%20on%20{dep_date or ''}"
            if ret_date:
                booking_url += f"%20returning%20{ret_date}"

            extracted_flights.append({
                "index": idx + 1,
                "airline": airline_name,
                "airline_code": airline_code,
                "departure_airport": dep_airport,
                "departure_time": dep_time,
                "arrival_airport": arr_airport,
                "arrival_time": arr_time,
                "duration": duration_str,
                "duration_minutes": duration if isinstance(duration, int) else 0,
                "price": price,
                "booking_url": booking_url
            })
        except Exception as e:
            logger.debug(f"Failed extracting item at index {idx}: {e}")
            pass
            
    return extracted_flights

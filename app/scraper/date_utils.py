from datetime import date, timedelta

def generate_date_matrix(days_ahead=30, trip_lengths=[3, 7, 14]):
    """
    Generates a list of (departure_date, return_date) tuples.
    
    Args:
        days_ahead (int): How many days into the future to start searching.
        trip_lengths (list): List of integers representing trip durations in days.
        
    Returns:
        list: A list of (dep_date_str, ret_date_str) tuples.
    """
    date_matrix = []
    start_date = date.today() + timedelta(days=2) # Start 2 days from now to avoid immediate bookings
    
    for day_offset in range(days_ahead):
        dep_date = start_date + timedelta(days=day_offset)
        for length in trip_lengths:
            ret_date = dep_date + timedelta(days=length)
            date_matrix.append((
                dep_date.strftime("%Y-%m-%d"),
                ret_date.strftime("%Y-%m-%d")
            ))
            
    return date_matrix

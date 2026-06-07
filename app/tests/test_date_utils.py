from app.scraper.date_utils import generate_date_matrix
from datetime import date, timedelta

def test_generate_date_matrix():
    days_ahead = 5
    trip_lengths = [3, 7]
    matrix = generate_date_matrix(days_ahead=days_ahead, trip_lengths=trip_lengths)
    
    # Total combinations should be days_ahead * len(trip_lengths)
    assert len(matrix) == 10
    
    # Check first combination
    start_date = date.today() + timedelta(days=2)
    first_dep, first_ret = matrix[0]
    assert first_dep == start_date.strftime("%Y-%m-%d")
    assert first_ret == (start_date + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Check last combination
    last_dep, last_ret = matrix[-1]
    expected_last_dep = start_date + timedelta(days=4)
    assert last_dep == expected_last_dep.strftime("%Y-%m-%d")
    assert last_ret == (expected_last_dep + timedelta(days=7)).strftime("%Y-%m-%d")

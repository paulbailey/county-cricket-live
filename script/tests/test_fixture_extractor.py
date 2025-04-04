from datetime import date, time
from script.fixture_extractor import (
    parse_date_range,
    parse_start_time_gmt,
    extract_venue,
    clean_team_name
)

def test_parse_date_range():
    # Test single date
    start, end = parse_date_range("May 1, 2024")
    assert start == date(2024, 5, 1)
    assert end == date(2024, 5, 1)
    
    # Test date range
    start, end = parse_date_range("May 1-3, 2024")
    assert start == date(2024, 5, 1)
    assert end == date(2024, 5, 3)
    
    # Test invalid input
    start, end = parse_date_range("invalid date")
    assert start is None
    assert end is None

def test_parse_start_time_gmt():
    # Test valid time format
    time_obj = parse_start_time_gmt("(10:30 local | 09:30 GMT)")
    assert time_obj == time(9, 30)
    
    # Test invalid format
    time_obj = parse_start_time_gmt("invalid time")
    assert time_obj is None

def test_extract_venue():
    # Test with venue
    venue = extract_venue("Essex vs Kent at Chelmsford")
    assert venue == "Chelmsford"
    
    # Test without venue
    venue = extract_venue("Essex vs Kent")
    assert venue is None

def test_clean_team_name():
    # Test with score
    team = clean_team_name("Essex 56/0 (15.1 ov)")
    assert team == "Essex"
    
    # Test with score without overs
    team = clean_team_name("Kent Spitfires 156/3")
    assert team == "Kent Spitfires"
    
    # Test without score
    team = clean_team_name("Essex")
    assert team == "Essex" 
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
from cricapi_client import CricAPIClient

def group_fixtures_by_day(fixtures: List[Dict]) -> Dict[str, List[Dict]]:
    """Group fixtures by day."""
    grouped = {}
    
    for fixture in fixtures:
        start_date = datetime.strptime(fixture["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(fixture["end_date"], "%Y-%m-%d").date()
        
        current_date = start_date
        day = 1
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in grouped:
                grouped[date_str] = []
            
            # Create a copy of the fixture with the day information
            fixture_copy = fixture.copy()
            fixture_copy["day"] = f"Day {day} of 4"
            
            grouped[date_str].append(fixture_copy)
            
            current_date += timedelta(days=1)
            day += 1
    
    return grouped

def write_fixtures_to_json(grouped_fixtures: Dict[str, List[Dict]], output_dir: str):
    """Write fixtures to JSON files grouped by date."""
    os.makedirs(output_dir, exist_ok=True)
    
    for date, fixtures in grouped_fixtures.items():
        output_file = os.path.join(output_dir, f"{date}.json")
        with open(output_file, "w") as f:
            json.dump(fixtures, f, indent=2)

def extract_fixtures():
    """Extract fixtures using CricAPI."""
    client = CricAPIClient()
    fixtures = client.get_county_fixtures()
    return group_fixtures_by_day(fixtures)

if __name__ == "__main__":
    grouped = extract_fixtures()
    write_fixtures_to_json(grouped, output_dir="public/data/fixtures")

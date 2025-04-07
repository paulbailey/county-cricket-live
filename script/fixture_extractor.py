import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
from cricapi_client import CricAPIClient
from models import Fixture, CompetitionType

def group_fixtures_by_day(fixtures: List[Fixture]) -> Dict[str, List[Dict]]:
    """Group fixtures by day, adding day information to each fixture."""
    grouped = {}
    today = datetime.now().date()
    
    for fixture in fixtures:
        # Skip fixtures that have already ended
        if fixture.end_date < today:
            continue
            
        # For County Championship matches, create entries for each day
        if fixture.competition in [CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE, CompetitionType.COUNTY_CHAMPIONSHIP_DIV_TWO]:
            current_date = fixture.start_date
            day_number = 1
            while current_date <= fixture.end_date and current_date >= today:
                date_str = current_date.strftime("%Y-%m-%d")
                if date_str not in grouped:
                    grouped[date_str] = []
                fixture_dict = fixture.model_dump()
                fixture_dict["day"] = f"Day {day_number} of 4"
                grouped[date_str].append(fixture_dict)
                current_date = current_date + timedelta(days=1)
                day_number += 1
        else:
            # For all other competitions (One Day Cup), they are single-day matches
            if fixture.start_date >= today:
                date_str = fixture.start_date.strftime("%Y-%m-%d")
                if date_str not in grouped:
                    grouped[date_str] = []
                fixture_dict = fixture.model_dump()
                fixture_dict["day"] = "One Day Match"
                grouped[date_str].append(fixture_dict)
    
    return grouped

def write_fixtures_to_json(grouped_fixtures: Dict[str, List[Dict]], output_dir: str):
    """Write fixtures to JSON files grouped by date."""
    os.makedirs(output_dir, exist_ok=True)
    
    for date, fixtures in grouped_fixtures.items():
        output_file = os.path.join(output_dir, f"{date}.json")
        # Convert date objects to strings before JSON serialization
        serializable_fixtures = []
        for fixture in fixtures:
            serializable_fixture = fixture.copy()
            serializable_fixture["start_date"] = serializable_fixture["start_date"].strftime("%Y-%m-%d")
            serializable_fixture["end_date"] = serializable_fixture["end_date"].strftime("%Y-%m-%d")
            serializable_fixtures.append(serializable_fixture)
        
        with open(output_file, "w") as f:
            json.dump(serializable_fixtures, f, indent=2)

def extract_fixtures() -> Dict[str, List[Dict]]:
    """Extract fixtures using CricAPI."""
    client = CricAPIClient()
    fixtures = client.get_county_fixtures()
    return group_fixtures_by_day(fixtures)

if __name__ == "__main__":
    grouped = extract_fixtures()
    write_fixtures_to_json(grouped, output_dir="public/data/fixtures")

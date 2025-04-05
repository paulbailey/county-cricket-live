import os
import sys
import json
from datetime import datetime
from unittest.mock import patch

# Add the script directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixture_extractor import (
    group_fixtures_by_day,
    write_fixtures_to_json
)

def test_group_fixtures_by_day():
    """Test that fixtures are correctly grouped by day."""
    # Mock today's date to be 2025-04-03
    with patch('fixture_extractor.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 4, 3)
        mock_datetime.date.today.return_value = datetime(2025, 4, 3).date()
        mock_datetime.strptime.side_effect = lambda date_str, _: datetime.strptime(date_str, "%Y-%m-%d")
        
        fixtures = [
            {
                "match_id": "1",
                "competition": "County Championship Division One",
                "home_team": "Essex",
                "away_team": "Surrey",
                "start_date": "2025-04-04",
                "end_date": "2025-04-07",
                "start_time_gmt": "11:00",
                "venue": "County Ground, Chelmsford"
            }
        ]
        
        grouped = group_fixtures_by_day(fixtures)
        
        # Check that we have entries for all days
        assert "2025-04-04" in grouped
        assert "2025-04-05" in grouped
        assert "2025-04-06" in grouped
        assert "2025-04-07" in grouped
        
        # Check that each day has the correct fixture with day information
        for i, date in enumerate(["2025-04-04", "2025-04-05", "2025-04-06", "2025-04-07"]):
            day_fixtures = grouped[date]
            assert len(day_fixtures) == 1
            assert day_fixtures[0]["day"] == f"Day {i+1} of 4"

def test_write_fixtures_to_json(tmp_path):
    """Test that fixtures are correctly written to JSON files."""
    fixtures = {
        "2025-04-04": [
            {
                "match_id": "1",
                "competition": "County Championship Division One",
                "home_team": "Essex",
                "away_team": "Surrey",
                "start_date": "2025-04-04",
                "end_date": "2025-04-07",
                "start_time_gmt": "11:00",
                "venue": "County Ground, Chelmsford",
                "day": "Day 1 of 4"
            }
        ]
    }
    
    output_dir = tmp_path / "fixtures"
    write_fixtures_to_json(fixtures, str(output_dir))
    
    # Check that the file was created
    assert (output_dir / "2025-04-04.json").exists()
    
    # Check the contents
    with open(output_dir / "2025-04-04.json") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["match_id"] == "1"
        assert data[0]["day"] == "Day 1 of 4" 
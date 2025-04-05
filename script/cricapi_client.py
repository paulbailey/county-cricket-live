import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict

class CricAPIClient:
    def __init__(self):
        self.api_key = os.getenv("CRICKET_API_KEY")
        if not self.api_key:
            raise ValueError("CRICKET_API_KEY environment variable is not set")
        self.base_url = "https://api.cricapi.com/v1"
        
    def get_county_fixtures(self) -> List[Dict]:
        """Get all County Championship fixtures from CricAPI."""
        # Series IDs for County Championship competitions
        series_ids = {
            "County Championship Division One": "9362b075-d007-478c-b4a9-e08b9306caef",
            "County Championship Division Two": "4cdcd4af-0d19-439d-afc3-c2e75d8a8e53"
        }
        
        fixtures = []
        for competition, series_id in series_ids.items():
            response = requests.get(
                f"{self.base_url}/series_info",
                params={
                    "apikey": self.api_key,
                    "id": series_id
                }
            )
            data = response.json()
            
            if data["status"] == "success":
                for match in data["data"]["matchList"]:
                    # Parse the full datetime
                    full_datetime = datetime.strptime(match["dateTimeGMT"], "%Y-%m-%dT%H:%M:%S")
                    # Extract just the time in HH:MM format
                    start_time = full_datetime.strftime("%H:%M")
                    start_date = full_datetime.date()
                    
                    # Set end date based on competition type
                    if "County Championship" in competition:
                        end_date = start_date + timedelta(days=3)  # 4-day matches
                    else:
                        end_date = start_date  # One-day matches
                    
                    # Extract home team from match name (first team mentioned)
                    home_team = match["teams"][0]
                    away_team = match["teams"][1]
                    
                    fixtures.append({
                        "match_id": match["id"],
                        "competition": competition,
                        "home_team": home_team,
                        "away_team": away_team,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "start_time_gmt": start_time,
                        "venue": match["venue"]
                    })
        
        return fixtures 
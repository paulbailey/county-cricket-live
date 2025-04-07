import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
from models import Fixture, CompetitionType

# Load environment variables from .env file
load_dotenv()

class CricAPIClient:
    def __init__(self):
        self.api_key = os.getenv("CRICKET_API_KEY")
        if not self.api_key:
            raise ValueError("CRICKET_API_KEY environment variable is not set")
        self.base_url = "https://api.cricapi.com/v1"
        
    def get_county_fixtures(self) -> list[Fixture]:
        """Get all County Championship fixtures from CricAPI."""
        # Series IDs for County Championship competitions
        series_ids = {
            CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE: "9362b075-d007-478c-b4a9-e08b9306caef",
            CompetitionType.COUNTY_CHAMPIONSHIP_DIV_TWO: "4cdcd4af-0d19-439d-afc3-c2e75d8a8e53",
            # CompetitionType.ONE_DAY_CUP: "475eb151-5521-46fd-8490-ef9704138cb"
        }
        
        fixtures = []
        for competition, series_id in series_ids.items():
            try:
                response = requests.get(
                    f"{self.base_url}/series_info",
                    params={
                        "apikey": self.api_key,
                        "id": series_id
                    }
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                data = response.json()
                
                if data["status"] == "success":
                    for match in data["data"]["matchList"]:
                        # Parse the full datetime
                        full_datetime = datetime.strptime(match["dateTimeGMT"], "%Y-%m-%dT%H:%M:%S")
                        # Extract just the time in HH:MM format
                        start_time = full_datetime.strftime("%H:%M")
                        start_date = full_datetime.date()
                        
                        # Set end date based on competition type
                        if competition in [CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE, CompetitionType.COUNTY_CHAMPIONSHIP_DIV_TWO]:
                            end_date = start_date + timedelta(days=3)  # 4-day matches
                        else:
                            end_date = start_date  # One-day matches
                        
                        fixture = Fixture(
                            match_id=match["id"],
                            competition=competition,
                            home_team=match["teams"][0],
                            away_team=match["teams"][1],
                            start_date=start_date,
                            end_date=end_date,
                            start_time_gmt=start_time,
                            venue=match["venue"]
                        )
                        fixtures.append(fixture)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching fixtures for {competition}: {str(e)}")
                continue
            except (KeyError, ValueError) as e:
                print(f"Error processing data for {competition}: {str(e)}")
                continue
        
        return fixtures 
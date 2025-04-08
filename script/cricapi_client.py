import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
from models import (
    Fixture, CompetitionType, MatchDetails, MatchData, CompetitionMatches,
    MatchesData, StreamsData, MatchScore, InningsScore
)

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
                response.raise_for_status()
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

    def get_match_details(self, match_id: str) -> MatchDetails:
        """Get detailed information about a specific match."""
        try:
            response = requests.get(
                f"{self.base_url}/match_info",
                params={
                    "apikey": self.api_key,
                    "id": match_id
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data["status"] == "success":
                match_data = data["data"]
                score = None
                if "score" in match_data and match_data["score"]:
                    innings_scores = []
                    for innings in match_data["score"]:
                        innings_scores.append(InningsScore(
                            innings_name=innings.get("inning", ""),
                            runs_scored=innings.get("r", 0),
                            wickets_fallen=innings.get("w", 0),
                            overs_bowled=innings.get("o", 0.0)
                        ))
                    score = MatchScore(innings_list=innings_scores)
                
                return MatchDetails(
                    match_id=match_id,
                    status=match_data.get("status", "upcoming"),
                    match_started=match_data.get("matchStarted"),
                    match_ended=match_data.get("matchEnded"),
                    score=score
                )
            return MatchDetails(match_id=match_id, status="error")
        except Exception as e:
            print(f"Error fetching match details for {match_id}: {str(e)}")
            return MatchDetails(match_id=match_id, status="error")

    def generate_matches_data(self, streams_data: StreamsData) -> MatchesData:
        """Generate matches data from streams and fixtures."""
        try:
            # Read fixtures for today
            today = datetime.now().strftime('%Y-%m-%d')
            fixtures_file = Path(__file__).parent.parent / 'public' / 'data' / 'fixtures' / f'{today}.json'
            
            # Return empty matches data if no fixtures file exists
            if not fixtures_file.exists():
                print(f'No fixtures file found for {today}, skipping score generation')
                return MatchesData(
                    last_updated=datetime.now(),
                    competitions={}
                )
            
            with open(fixtures_file, 'r', encoding='utf-8') as f:
                fixtures = [Fixture(**fixture) for fixture in json.load(f)]

            # Initialize matches structure
            matches = MatchesData(
                last_updated=datetime.now(),
                competitions={}
            )

            # Process all streams
            for match_id, stream in streams_data.streams.items():
                # Find corresponding fixture
                fixture = next((f for f in fixtures if f.match_id == match_id), None)
                if not fixture:
                    print(f'No fixture found for match {match_id}')
                    continue

                # Get match details from API
                match_details = self.get_match_details(match_id)

                # Create match entry
                match_data = MatchData(
                    match_id=match_id,
                    venue=fixture.venue,
                    start_time=fixture.start_time_gmt,
                    home_team=fixture.home_team,
                    away_team=fixture.away_team,
                    scores=match_details.score.model_dump() if match_details.score else None,
                    status=match_details.status,
                    stream=stream.model_dump(),
                    match_started=match_details.match_started,
                    match_ended=match_details.match_ended
                )

                # Add to competition group
                competition = fixture.competition.value
                if competition not in matches.competitions:
                    matches.competitions[competition] = CompetitionMatches(
                        competition_name=competition,
                        matches_list=[]
                    )
                matches.competitions[competition].matches_list.append(match_data)

            # Sort matches within each competition by home team
            for competition in matches.competitions.values():
                competition.matches_list.sort(key=lambda x: x.home_team)

            # Sort competitions alphabetically
            matches.competitions = dict(sorted(matches.competitions.items()))

            return matches
        except Exception as e:
            print(f"Error generating matches data: {str(e)}")
            raise 
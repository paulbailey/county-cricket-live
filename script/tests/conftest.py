import pytest
import os
import sys
from pathlib import Path
from .fixtures import (
    MOCK_EXISTING_STREAMS,
    MOCK_YOUTUBE_RESPONSE
)
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from script.models import (
    Channel, Fixture, StreamInfo, StreamsData, CompetitionType,
    MatchDetails, MatchScore, InningsScore
)

# Add the script directory to the Python path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

# Import the modules after adding to path

@pytest.fixture(autouse=True)
def setup_test_environment():
    # Set up test environment variables
    os.environ["GOOGLE_API_KEY"] = "test_api_key"
    os.environ["BLUESKY_USERNAME"] = "test_username"
    os.environ["BLUESKY_PASSWORD"] = "test_password"
    
    # Create necessary directories if they don't exist
    test_dirs = [
        "public/data/fixtures",
        "public/data"
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Clean up after tests if needed
    pass

@pytest.fixture
def mock_env():
    with patch.dict('os.environ', {'CRICKET_API_KEY': 'test_key'}):
        yield

@pytest.fixture
def mock_channels():
    """Fixture providing mock channel data."""
    return {
        "team1": Channel(
            name="Team A",
            youtubeChannelId="channel1",
            nicknames=["Team A Nickname"]
        ),
        "team2": Channel(
            name="Team B",
            youtubeChannelId="channel2",
            nicknames=["Team B Nickname"]
        )
    }

@pytest.fixture
def mock_fixtures():
    """Fixture providing mock fixture data."""
    now = datetime.now(timezone.utc)
    return [
        Fixture(
            match_id="match1",
            competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
            home_team="Team A",
            away_team="Team B",
            start_date=now.date(),
            end_date=now.date() + timedelta(days=3),
            start_time_gmt="11:00",
            venue="Ground 1"
        ),
        Fixture(
            match_id="match2",
            competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
            home_team="Team B",
            away_team="Team C",
            start_date=now.date(),
            end_date=now.date() + timedelta(days=3),
            start_time_gmt="11:00",
            venue="Ground 2"
        )
    ]

@pytest.fixture
def mock_streams_data():
    """Fixture providing mock streams data."""
    return StreamsData(
        lastUpdated=datetime.now(timezone.utc),
        streams={
            "match1": StreamInfo(
                videoId="video1",
                title="Team A vs Team B",
                channelId="channel1",
                standardTitle="Team A vs Team B",
                isPlaceholder=False
            )
        }
    )

@pytest.fixture
def mock_youtube_response():
    """Fixture providing mock YouTube API response."""
    return {
        "items": [{
            "id": "video1",
            "snippet": {
                "title": "Team A vs Team B",
                "channelId": "channel1",
                "liveBroadcastContent": "live"
            }
        }]
    }

@pytest.fixture
def mock_match_details():
    return MatchDetails(
        id="match1",
        status="live",
        matchStarted=True,
        matchEnded=False,
        score=MatchScore(innings=[
            InningsScore(innings="1st Innings", runs=150, wickets=3, overs=25.2)
        ])
    )

@pytest.fixture
def mock_existing_streams():
    return MOCK_EXISTING_STREAMS

@pytest.fixture
def mock_youtube_response():
    return MOCK_YOUTUBE_RESPONSE 
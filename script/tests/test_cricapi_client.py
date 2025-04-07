import pytest
from datetime import datetime, date
from unittest.mock import patch
from script.cricapi_client import CricAPIClient
from script.models import (
    Fixture, CompetitionType, StreamsData, StreamInfo
)

@pytest.fixture
def mock_env():
    with patch.dict('os.environ', {'CRICKET_API_KEY': 'test_key'}):
        yield

@pytest.fixture
def client(mock_env):
    return CricAPIClient()

@pytest.fixture
def mock_fixture():
    return Fixture(
        match_id="test_match_1",
        competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
        home_team="Team A",
        away_team="Team B",
        start_date=date(2024, 4, 7),
        end_date=date(2024, 4, 10),
        start_time_gmt="11:00",
        venue="Test Ground"
    )

@pytest.fixture
def mock_stream_info():
    return StreamInfo(
        videoId="test_video_1",
        title="Test Match Stream",
        channelId="test_channel_1",
        standardTitle="Team A vs Team B"
    )

@pytest.fixture
def mock_streams_data(mock_stream_info):
    return StreamsData(
        lastUpdated=datetime.now(),
        streams={"test_match_1": mock_stream_info}
    )

def test_client_initialization():
    """Test that the client initializes correctly with API key."""
    with patch.dict('os.environ', {'CRICKET_API_KEY': 'test_key'}):
        client = CricAPIClient()
        assert client.api_key == 'test_key'
        assert client.base_url == "https://api.cricapi.com/v1" 
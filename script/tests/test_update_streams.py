import pytest
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, mock_open
from script.update_streams import (
    load_channels,
    load_fixtures,
    load_existing_streams,
    get_channel_id_for_team,
    get_new_streams
)

@pytest.fixture
def mock_channels():
    return {
        "essex": {
            "name": "Essex",
            "youtubeChannelId": "channel1",
            "nicknames": ["Essex CCC"]
        },
        "kent": {
            "name": "Kent",
            "youtubeChannelId": "channel2"
        }
    }

@pytest.fixture
def mock_fixtures():
    return [
        {
            "date": "2024-05-01",
            "home": "Essex",
            "away": "Kent",
            "competition": "County Championship"
        }
    ]

@pytest.fixture
def mock_existing_streams():
    return {
        "County Championship": {
            "live": [
                {
                    "title": "Essex vs Kent",
                    "channelId": "channel1",
                    "startTime": "2024-05-01T10:00:00Z",
                    "fixture": {
                        "home_team": "Essex",
                        "away_team": "Kent",
                        "start_date": "2024-05-01",
                        "end_date": "2024-05-01"
                    }
                }
            ]
        }
    }

def test_load_channels(mock_channels):
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_channels))):
        channels = load_channels()
        assert channels == mock_channels

def test_load_fixtures(mock_fixtures):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mock_file_path = Path(f"public/data/fixtures/{today}.json")
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_fixtures))):
        fixtures = load_fixtures()
        assert fixtures == mock_fixtures

def test_load_existing_streams(mock_existing_streams):
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_existing_streams))):
        streams = load_existing_streams()
        assert streams == mock_existing_streams

def test_get_channel_id_for_team(mock_channels):
    # Test exact match
    channel_id = get_channel_id_for_team("Essex", mock_channels)
    assert channel_id == "channel1"
    
    # Test nickname match
    channel_id = get_channel_id_for_team("Essex CCC", mock_channels)
    assert channel_id == "channel1"
    
    # Test no match
    channel_id = get_channel_id_for_team("NotATeam", mock_channels)
    assert channel_id is None

def test_get_new_streams(mock_existing_streams):
    new_streams = {
        "County Championship": {
            "live": [
                mock_existing_streams["County Championship"]["live"][0],  # Existing stream
                {  # New stream
                    "title": "New Match",
                    "channelId": "channel3",
                    "startTime": "2024-05-02T10:00:00Z",
                    "fixture": {
                        "home_team": "Surrey",
                        "away_team": "Hampshire",
                        "start_date": "2024-05-02",
                        "end_date": "2024-05-02"
                    }
                }
            ]
        }
    }
    
    new_only = get_new_streams(mock_existing_streams, new_streams)
    assert len(new_only) == 1
    assert new_only[0]["fixture"]["home_team"] == "Surrey"
    assert new_only[0]["fixture"]["away_team"] == "Hampshire" 
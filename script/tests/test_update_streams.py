from unittest.mock import patch
import json
from script.update_streams import (
    load_channels,
    get_channel_id_for_team,
    get_new_streams
)

@patch('builtins.open')
@patch('json.load')
def test_load_channels(mock_json_load, mock_open, mock_channels):
    """Test loading channels from JSON file."""
    mock_json_load.return_value = {
        id: {
            "name": channel.name,
            "youtube_channel_id": channel.youtube_channel_id,
            "nicknames": channel.nicknames,
            "uploads_playlist_id": channel.uploads_playlist_id
        } for id, channel in mock_channels.items()
    }
    
    channels = load_channels()
    assert len(channels) == 2
    assert channels["team1"].name == "Team A"
    assert channels["team2"].youtube_channel_id == "channel2"

def test_get_channel_id_for_team(mock_channels):
    """Test getting channel ID for a team."""
    channel_id = get_channel_id_for_team("Team A", mock_channels)
    assert channel_id == "channel1"
    
    # Test with nickname
    channel_id = get_channel_id_for_team("Team A Nickname", mock_channels)
    assert channel_id == "channel1"
    
    # Test with unknown team
    channel_id = get_channel_id_for_team("Unknown Team", mock_channels)
    assert channel_id is None

def test_get_new_streams(mock_streams_data):
    """Test finding new streams."""
    existing_streams = {
        "match1": {
            "video_id": "video1",
            "title": "Team A vs Team B",
            "channel_id": "channel1",
            "standard_title": "Team A vs Team B"
        }
    }
    
    new_streams = {
        "match1": {
            "video_id": "video1",
            "title": "Team A vs Team B",
            "channel_id": "channel1",
            "standard_title": "Team A vs Team B"
        },
        "match2": {
            "video_id": "video2",
            "title": "Team B vs Team C",
            "channel_id": "channel2",
            "standard_title": "Team B vs Team C"
        }
    }
    
    new_fixture_streams = get_new_streams(existing_streams, new_streams)
    assert len(new_fixture_streams) == 1
    assert new_fixture_streams[0]["video_id"] == "video2"

@patch('builtins.open')
@patch('json.load')
def test_load_channels_error(mock_json_load, mock_open):
    """Test loading channels handles errors gracefully."""
    mock_open.side_effect = FileNotFoundError()
    channels = load_channels()
    assert channels == {}

    mock_open.side_effect = None
    mock_json_load.side_effect = json.JSONDecodeError("", "", 0)
    channels = load_channels()
    assert channels == {} 
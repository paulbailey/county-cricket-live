import pytest
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, mock_open, MagicMock
from script.update_streams import (
    load_channels,
    load_fixtures,
    load_existing_streams,
    get_channel_id_for_team,
    get_new_streams,
    get_live_streams,
    create_placeholder_streams,
    main,
    post_to_bluesky
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
            "home_team": "Essex",
            "away_team": "Kent",
            "competition": "County Championship",
            "venue": "Chelmsford",
            "start_date": "2024-05-01",
            "end_date": "2024-05-01"
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

@pytest.fixture
def mock_youtube_response():
    return {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Essex vs Kent",
                    "channelId": "channel1",
                    "description": "Test match",
                    "publishedAt": "2024-05-01T10:00:00Z"
                },
                "liveStreamingDetails": {
                    "actualStartTime": "2024-05-01T10:00:00Z"
                }
            }
        ]
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

def test_load_fixtures_error_handling():
    # Test directory doesn't exist
    with patch("pathlib.Path.exists", return_value=False):
        fixtures = load_fixtures()
        assert fixtures == []

    # Test file doesn't exist
    with patch("pathlib.Path.exists", side_effect=[True, False]):
        fixtures = load_fixtures()
        assert fixtures == []

    # Test JSON decode error
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="invalid json")):
        fixtures = load_fixtures()
        assert fixtures == []

def test_load_existing_streams(mock_existing_streams):
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_existing_streams))):
        streams = load_existing_streams()
        assert streams == mock_existing_streams

def test_load_existing_streams_error_handling():
    # Test file doesn't exist
    with patch("pathlib.Path.exists", return_value=False):
        streams = load_existing_streams()
        assert streams == {}

    # Test JSON decode error
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="invalid json")):
        streams = load_existing_streams()
        assert streams == {}

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

def test_get_live_streams(mock_fixtures, mock_channels, mock_youtube_response):
    # Mock YouTube API responses
    mock_youtube = MagicMock()
    mock_youtube.channels.return_value.list.return_value.execute.return_value = {
        "items": [{
            "contentDetails": {
                "relatedPlaylists": {
                    "uploads": "playlist1"
                }
            }
        }]
    }
    mock_youtube.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [{
            "contentDetails": {
                "videoId": "video1"
            }
        }]
    }
    mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_youtube_response

    with patch("script.update_streams.youtube", mock_youtube):
        live_streams, upcoming_matches = get_live_streams(mock_fixtures, mock_channels)
        assert len(live_streams) == 1
        assert len(upcoming_matches) == 0
        assert live_streams[0]["videoId"] == "video1"

def test_get_live_streams_error_handling(mock_fixtures, mock_channels):
    # Test YouTube API error
    mock_youtube = MagicMock()
    mock_youtube.channels.return_value.list.return_value.execute.side_effect = Exception("API Error")
    
    with patch("script.update_streams.youtube", mock_youtube):
        live_streams, upcoming_matches = get_live_streams(mock_fixtures, mock_channels)
        assert len(live_streams) == 0
        assert len(upcoming_matches) == 0

def test_create_placeholder_streams(mock_fixtures, mock_channels):
    live_streams = []
    upcoming_matches = []
    
    placeholders = create_placeholder_streams(mock_fixtures, mock_channels, live_streams, upcoming_matches)
    assert len(placeholders) == 1
    assert placeholders[0]["isPlaceholder"] is True
    assert placeholders[0]["title"] == "Essex vs Kent"

def test_create_placeholder_streams_no_channel(mock_fixtures):
    # Test with no matching channel
    channels = {
        "not_essex": {
            "name": "Not Essex",
            "youtubeChannelId": "channel3"
        }
    }
    live_streams = []
    upcoming_matches = []
    
    placeholders = create_placeholder_streams(mock_fixtures, channels, live_streams, upcoming_matches)
    assert len(placeholders) == 0

def test_main_no_fixtures(mock_channels):
    with patch("script.update_streams.load_channels", return_value=mock_channels), \
         patch("script.update_streams.load_fixtures", return_value=[]), \
         patch("script.update_streams.load_existing_streams", return_value={}), \
         patch("script.update_streams.get_live_streams", return_value=([], [])), \
         patch("script.update_streams.create_placeholder_streams", return_value=[]), \
         patch("builtins.open", mock_open()), \
         patch("pathlib.Path.mkdir"):
        main()

def test_main_with_fixtures(mock_channels, mock_fixtures, mock_existing_streams):
    with patch("script.update_streams.load_channels", return_value=mock_channels), \
         patch("script.update_streams.load_fixtures", return_value=mock_fixtures), \
         patch("script.update_streams.load_existing_streams", return_value=mock_existing_streams), \
         patch("script.update_streams.get_live_streams", return_value=([], [])), \
         patch("script.update_streams.create_placeholder_streams", return_value=[]), \
         patch("script.update_streams.get_new_streams", return_value=[]), \
         patch("builtins.open", mock_open()), \
         patch("pathlib.Path.mkdir"):
        main()

def test_error_handling():
    # Test file not found error
    with patch("builtins.open", side_effect=FileNotFoundError):
        channels = load_channels()
        assert channels == {}

    # Test JSON decode error
    with patch("builtins.open", mock_open(read_data="invalid json")):
        channels = load_channels()
        assert channels == {}

    # Test successful load
    mock_channels = {
        "essex": {
            "name": "Essex",
            "youtubeChannelId": "channel1"
        }
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_channels))):
        channels = load_channels()
        assert channels == mock_channels

def test_post_to_bluesky_skip():
    # Test skipping Bluesky post
    with patch.dict("os.environ", {"SKIP_BLUESKY_POSTING": "true"}), \
         patch("script.update_streams.Client") as mock_client:
        post_to_bluesky({})  # Should not raise any errors
        mock_client.assert_not_called()

def test_post_to_bluesky_empty():
    # Test with empty streams data
    with patch("script.update_streams.Client") as mock_client:
        post_to_bluesky({})  # Should not raise any errors
        mock_client.assert_not_called() 
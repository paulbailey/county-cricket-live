import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
from contextlib import contextmanager
import script.update_streams as update_streams
from script.update_streams import (
    get_channel_id_for_team,
    get_new_streams,
    get_live_streams,
    create_placeholder_streams,
    main
)

class TestData:
    """Test data constants and helpers."""
    
    FIXTURE_TEMPLATE = {
        "competition": "County Championship",
        "home_team": "Essex",
        "away_team": "Kent",
        "start_date": "2024-04-05",
        "end_date": "2024-04-08",
        "venue": "Essex Ground"
    }
    
    CHANNEL_TEMPLATE = {
        "name": "Essex Cricket",
        "youtubeChannelId": "channel1",
        "nicknames": ["Essex", "Essex CCC"]
    }
    
    @classmethod
    def make_fixture(cls, **overrides):
        """Create a fixture with optional overrides."""
        return {**cls.FIXTURE_TEMPLATE, **overrides}
    
    @classmethod
    def make_channel(cls, **overrides):
        """Create a channel with optional overrides."""
        return {**cls.CHANNEL_TEMPLATE, **overrides}

class BaseTest:
    """Base class for all tests with common functionality.
    
    Provides helper methods for mocking file operations, error cases, and API responses.
    These helpers ensure consistent test behavior across all test classes.
    """
    
    @contextmanager
    def _mock_file_load(self, mock_data=None):
        """Mock file loading operations.
        
        Args:
            mock_data: Data to return when reading files. Defaults to empty dict.
            
        Mocks:
            - File open operations
            - Directory listing
            - Path existence checks
        """
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data or {}))), \
             patch("os.listdir", return_value=["test.json"]), \
             patch("os.path.exists", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):
            yield
    
    @contextmanager
    def _mock_error_case(self, error, expected_data):
        """Helper to mock different types of errors."""
        if isinstance(error, json.JSONDecodeError):
            with patch("builtins.open", mock_open(read_data="invalid json")), \
                 patch("json.loads", side_effect=error), \
                 patch("os.path.exists", return_value=True), \
                 patch("pathlib.Path.exists", return_value=True):
                yield
        elif isinstance(error, FileNotFoundError):
            with patch("builtins.open", side_effect=error), \
                 patch("os.path.exists", return_value=False), \
                 patch("pathlib.Path.exists", return_value=False):
                yield
        elif isinstance(error, NotADirectoryError):
            with patch("os.listdir", side_effect=error), \
                 patch("os.path.exists", return_value=False), \
                 patch("pathlib.Path.exists", return_value=False):
                yield
        else:
            with self._mock_file_load(expected_data):
                yield
    
    def _mock_youtube_api(self, response=None, error=None):
        """Helper to mock YouTube API responses."""
        mock_youtube = MagicMock()
        
        # Mock the method chains
        mock_channels = MagicMock()
        mock_channels.list.return_value.execute.return_value = {
            "items": [{
                "contentDetails": {
                    "relatedPlaylists": {
                        "uploads": "playlist1"
                    }
                }
            }]
        }
        mock_youtube.channels.return_value = mock_channels
        
        mock_playlist_items = MagicMock()
        mock_playlist_items.list.return_value.execute.return_value = {
            "items": [{
                "contentDetails": {
                    "videoId": "video1"
                }
            }]
        }
        mock_youtube.playlistItems.return_value = mock_playlist_items
        
        mock_videos = MagicMock()
        mock_videos.list.return_value.execute.return_value = response or {
            "items": [{
                "id": "video1",
                "snippet": {
                    "title": "Live: Essex vs Kent",
                    "liveBroadcastContent": "live",
                    "channelId": "channel1",
                    "channelTitle": "Essex Cricket"
                }
            }]
        }
        mock_youtube.videos.return_value = mock_videos
        
        if error:
            mock_channels.list.return_value.execute.side_effect = error
            mock_playlist_items.list.return_value.execute.side_effect = error
            mock_videos.list.return_value.execute.side_effect = error
        
        return mock_youtube

    @contextmanager
    def _mock_main_dependencies(self):
        """Mock dependencies for the main function."""
        mock_open_obj = mock_open()
        with patch("script.update_streams.load_channels") as mock_load_channels, \
             patch("script.update_streams.load_fixtures") as mock_load_fixtures, \
             patch("script.update_streams.load_existing_streams") as mock_load_existing, \
             patch("script.update_streams.get_live_streams") as mock_get_streams, \
             patch("script.update_streams.post_to_bluesky") as mock_post, \
             patch("pathlib.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open_obj):
            yield {
                "load_channels": mock_load_channels,
                "load_fixtures": mock_load_fixtures,
                "load_existing_streams": mock_load_existing,
                "get_live_streams": mock_get_streams,
                "post_to_bluesky": mock_post,
                "mkdir": mock_mkdir,
                "open": mock_open_obj
            }

class TestErrorHandling(BaseTest):
    """Tests for error handling scenarios."""
    
    EMPTY_RESULTS = {
        "load_channels": {},
        "load_fixtures": [],
        "load_existing_streams": {}
    }
    
    @pytest.mark.parametrize("func_name,error_type", [
        ("load_channels", FileNotFoundError),
        ("load_channels", json.JSONDecodeError),
        ("load_fixtures", FileNotFoundError),
        ("load_fixtures", json.JSONDecodeError),
        ("load_fixtures", NotADirectoryError),
        ("load_existing_streams", FileNotFoundError),
        ("load_existing_streams", json.JSONDecodeError),
        ("load_existing_streams", NotADirectoryError)
    ])
    def test_error_handling(self, func_name, error_type):
        """Test error handling for various scenarios."""
        func = getattr(update_streams, func_name)
        if error_type == json.JSONDecodeError:
            error = error_type("test error", "invalid json", 0)
        else:
            error = error_type("test error")
        with self._mock_error_case(error, self.EMPTY_RESULTS[func_name]):
            result = func()
            assert result == self.EMPTY_RESULTS[func_name]

class TestStreamProcessing(BaseTest):
    """Tests for stream processing functions.
    
    Tests the core functionality for processing YouTube streams and matching them to fixtures:
    - Channel ID lookup for teams
    - New stream detection
    - Live stream processing
    - Placeholder stream creation
    """
    
    def test_get_channel_id_for_team(self):
        """Test channel ID lookup for team names.
        
        Verifies that:
        - Exact team name matches return correct channel ID
        - Team nickname matches return correct channel ID
        - Unknown teams return None
        """
        channels = {"channel1": TestData.make_channel()}
        test_cases = [
            ("Essex", "channel1"),
            ("Essex CCC", "channel1"),
            ("NotATeam", None)
        ]
        for team, expected in test_cases:
            assert get_channel_id_for_team(team, channels) == expected

    def test_get_new_streams(self, mock_existing_streams):
        new_stream = {
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
        new_streams = {"County Championship": {"live": [mock_existing_streams["County Championship"]["live"][0], new_stream]}}
        new_only = get_new_streams(mock_existing_streams, new_streams)
        assert len(new_only) == 1
        assert new_only[0]["fixture"]["home_team"] == "Surrey"
        assert new_only[0]["fixture"]["away_team"] == "Hampshire"

    def test_get_live_streams(self, mock_youtube_response):
        """Test live stream detection and processing.
        
        Verifies that:
        - Live streams are correctly identified from YouTube API response
        - Streams are matched to correct fixtures
        - Stream details are properly extracted
        - Upcoming matches are separated from live streams
        """
        fixtures = [TestData.make_fixture()]
        channels = {"channel1": TestData.make_channel()}
        mock_youtube = self._mock_youtube_api(response=mock_youtube_response)
        
        with patch("script.update_streams.youtube", mock_youtube):
            live_streams, upcoming_matches = get_live_streams(fixtures, channels)
            assert len(live_streams) == 1
            assert len(upcoming_matches) == 0
            assert live_streams[0]["videoId"] == "video1"

    def test_create_placeholder_streams(self):
        """Test placeholder stream creation."""
        fixtures = [TestData.make_fixture()]
        channels = {"channel1": TestData.make_channel()}
        
        placeholders = create_placeholder_streams(fixtures, channels, [], [])
        assert len(placeholders) == 1
        assert placeholders[0]["isPlaceholder"] is True
        assert placeholders[0]["title"] == "Essex vs Kent"
        assert placeholders[0]["description"] == "County Championship - Essex Ground"

    def test_create_placeholder_streams_no_channel(self, mock_fixtures):
        channels = {"not_essex": {"name": "Not Essex", "youtubeChannelId": "channel3"}}
        placeholders = create_placeholder_streams(mock_fixtures, channels, [], [])
        assert len(placeholders) == 0

class TestMainFunction(BaseTest):
    """Tests for the main orchestration function.
    
    Tests the main function that coordinates the entire stream processing workflow:
    - Loading configuration and data
    - Processing live streams
    - Handling existing streams
    - Posting updates to Bluesky
    
    Test cases:
    - no_new_streams: No fixtures available
    - new_streams: New fixtures with streams
    - mixed_streams: Mix of existing and new streams
    """
    
    def _make_test_data(self, has_fixtures=True, has_streams=True):
        """Create test data with optional flags."""
        fixture = TestData.make_fixture()
        fixture["match_id"] = "match1"  # Add match_id to fixture
        fixtures = [fixture] if has_fixtures else []
        streams = ([{
            "fixture": fixture,
            "videoId": "stream1",
            "channelId": "channel1",
            "title": "Live: Essex vs Kent",
            "description": "Live stream"
        }], []) if has_streams else ([], [])
        
        # For mixed_streams case, include some existing streams
        existing = {"County Championship": {"live": [], "upcoming": []}}
        if has_streams and has_fixtures:
            existing["County Championship"]["live"] = [{
                "fixture": fixture,
                "videoId": "existing_stream",
                "channelId": "channel1",
                "title": "Existing Stream",
                "description": "Existing stream"
            }]
        
        return {
            "channels": {"channel1": TestData.make_channel()} if has_fixtures else {},
            "fixtures": fixtures,
            "existing": existing
        }, streams

    def _setup_mocks(self, mocks, data, expected):
        """Set up mock return values."""
        mocks["load_channels"].return_value = data["channels"]
        mocks["load_fixtures"].return_value = data["fixtures"]
        mocks["load_existing_streams"].return_value = data["existing"]
        mocks["get_live_streams"].return_value = expected

    def _verify_calls(self, mocks, data, expected):
        """Verify mock calls."""
        mocks["load_channels"].assert_called_once()
        mocks["load_fixtures"].assert_called_once()
        
        if data["fixtures"]:
            mocks["get_live_streams"].assert_called_once_with(data["fixtures"], data["channels"])
            mocks["load_existing_streams"].assert_called_once()
            live_streams, _ = expected
            
            # Only verify post_to_bluesky if there are new streams to write
            if live_streams and live_streams != data["existing"].get("County Championship", {}).get("live", []):
                # Format the expected data to match the new format
                expected_data = {
                    "lastUpdated": mocks["post_to_bluesky"].call_args[0][0]["lastUpdated"],  # Use actual timestamp
                    "streams": {
                        "match1": {
                            "videoId": "stream1",
                            "title": "Live: Essex vs Kent",
                            "channelId": "channel1",
                            "standardTitle": "Essex vs Kent"
                        }
                    }
                }
                mocks["post_to_bluesky"].assert_called_once_with(expected_data)
            else:
                mocks["post_to_bluesky"].assert_not_called()
        else:
            mocks["get_live_streams"].assert_not_called()
            mocks["post_to_bluesky"].assert_not_called()

    @pytest.mark.parametrize("test_case", [
        ("no_new_streams", False, False),
        ("new_streams", True, True),
        ("mixed_streams", True, True)
    ])
    def test_main(self, test_case):
        """Test main function scenarios."""
        case_name, has_fixtures, has_streams = test_case
        data, expected = self._make_test_data(has_fixtures, has_streams)
        
        with self._mock_main_dependencies() as mocks:
            self._setup_mocks(mocks, data, expected)
            main()
            self._verify_calls(mocks, data, expected)

@pytest.fixture
def mock_youtube_response():
    """Provide mock YouTube API response."""
    return {
        "items": [{
            "id": "video1",
            "snippet": {
                "title": "Live: Essex vs Kent",
                "liveBroadcastContent": "live",
                "channelId": "channel1",
                "channelTitle": "Essex Cricket",
                "description": "Live stream",
                "publishedAt": "2024-04-05T10:00:00Z"
            },
            "liveStreamingDetails": {
                "actualStartTime": "2024-04-05T10:00:00Z"
            }
        }]
    } 
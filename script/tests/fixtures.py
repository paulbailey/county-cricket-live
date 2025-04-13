"""Mock data fixtures for testing."""

from datetime import datetime, timezone, timedelta
from script.models import Channel, Fixture, StreamInfo, StreamsData, CompetitionType

# Mock channel data
MOCK_CHANNELS = {
    "team1": Channel(
        name="Team A",
        youtubeChannelId="channel1",
        nicknames=["Team A Nickname"],
        uploadsPlaylistId="playlist1"
    ),
    "team2": Channel(
        name="Team B",
        youtubeChannelId="channel2",
        nicknames=["Team B Nickname"],
        uploadsPlaylistId="playlist2"
    )
}

# Mock fixture data
today = datetime.now(timezone.utc).date()
MOCK_FIXTURES = [
    Fixture(
        match_id="match1",
        competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
        home_team="Team A",
        away_team="Team C",
        start_date=today,
        end_date=today + timedelta(days=3),
        start_time_gmt="11:00",
        venue="Test Ground"
    ),
    Fixture(
        match_id="match2",
        competition=CompetitionType.COUNTY_CHAMPIONSHIP_DIV_ONE,
        home_team="Team B",
        away_team="Team D",
        start_date=today,
        end_date=today + timedelta(days=3),
        start_time_gmt="11:00",
        venue="Test Ground 2"
    )
]

# Mock streams data
MOCK_EXISTING_STREAMS = StreamsData(
    lastUpdated=datetime.now(timezone.utc),
    streams={
        "match1": StreamInfo(
            videoId="video1",
            title="Team A vs Team C",
            channelId="channel1",
            standardTitle="Team A vs Team C"
        )
    }
)

# Mock YouTube API response
MOCK_YOUTUBE_RESPONSE = {
    "items": [{
        "id": "video1",
        "snippet": {
            "title": "Team A vs Team C",
            "channelId": "channel1",
            "description": "Test match",
            "publishedAt": "2024-04-07T10:00:00Z"
        },
        "liveStreamingDetails": {
            "actualStartTime": "2024-04-07T11:00:00Z"
        }
    }]
} 
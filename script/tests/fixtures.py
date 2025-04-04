"""Mock data fixtures for testing."""

MOCK_CHANNELS = {
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

MOCK_FIXTURES = [
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

MOCK_EXISTING_STREAMS = {
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

MOCK_YOUTUBE_RESPONSE = {
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
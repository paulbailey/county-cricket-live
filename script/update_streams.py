import os
import json
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API setup
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)


def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def get_live_streams(channels):
    live_streams = []
    upcoming_matches = []

    for channel in channels:
        try:
            # Get channel's live streams
            request = youtube.search().list(
                part="snippet",
                channelId=channel["youtubeChannelId"],
                eventType="live",
                type="video",
                maxResults=5,
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                stream_data = {
                    "videoId": video_id,
                    "title": snippet["title"],
                    "channelName": channel["name"],
                    "description": snippet["description"],
                    "publishedAt": snippet["publishedAt"],
                }
                live_streams.append(stream_data)

            # Get channel's upcoming streams
            request = youtube.search().list(
                part="snippet",
                channelId=channel["youtubeChannelId"],
                eventType="upcoming",
                type="video",
                maxResults=5,
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                # Get video details to get scheduled start time
                video_request = youtube.videos().list(
                    part="liveStreamingDetails", id=video_id
                )
                video_response = video_request.execute()

                if video_response["items"]:
                    live_details = video_response["items"][0].get(
                        "liveStreamingDetails", {}
                    )
                    scheduled_start = live_details.get("scheduledStartTime")

                    if scheduled_start:
                        match_data = {
                            "videoId": video_id,
                            "title": snippet["title"],
                            "channelName": channel["name"],
                            "description": snippet["description"],
                            "scheduledStartTime": scheduled_start,
                        }
                        upcoming_matches.append(match_data)

        except HttpError as e:
            print(f'Error fetching data for {channel["name"]}: {e}')
            continue

    return live_streams, upcoming_matches


def main():
    channels = load_channels()
    live_streams, upcoming_matches = get_live_streams(channels)

    # Sort upcoming matches by scheduled start time
    upcoming_matches.sort(key=lambda x: x["scheduledStartTime"])

    # Create output data
    output_data = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "liveStreams": live_streams,
        "upcomingMatches": upcoming_matches,
    }

    # Write to file
    with open("data/streams.json", "w") as f:
        json.dump(output_data, f, indent=2)


if __name__ == "__main__":
    main()

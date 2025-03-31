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
    all_video_ids = []

    # Get live and upcoming streams for each channel
    for channel in channels:
        try:
            print(
                f"\nChecking channel: {channel['name']} ({channel['youtubeChannelId']})"
            )

            # First get the channel's uploads playlist ID
            channel_request = youtube.channels().list(
                part="contentDetails", id=channel["youtubeChannelId"]
            )
            channel_response = channel_request.execute()

            if not channel_response.get("items"):
                print(f"No channel found for {channel['name']}")
                continue

            uploads_playlist_id = channel_response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]
            print(f"Found uploads playlist ID: {uploads_playlist_id}")

            # Get videos from uploads playlist
            playlist_request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,  # Maximum allowed
            )
            playlist_response = playlist_request.execute()

            for item in playlist_response.get("items", []):
                all_video_ids.append(item["contentDetails"]["videoId"])
            print(
                f"Found {len(playlist_response.get('items', []))} videos in uploads playlist"
            )
            if playlist_response.get("items"):
                print(
                    "Video IDs:",
                    [
                        item["contentDetails"]["videoId"]
                        for item in playlist_response["items"]
                    ],
                )

        except HttpError as e:
            print(f'Error fetching data for {channel["name"]}: {e}')
            continue

    print(f"\nTotal videos found: {len(all_video_ids)}")

    # Get video details in batches of 50 (YouTube API limit)
    for i in range(0, len(all_video_ids), 50):
        batch = all_video_ids[i : i + 50]
        try:
            video_request = youtube.videos().list(
                part="snippet,liveStreamingDetails", id=",".join(batch)
            )
            video_response = video_request.execute()

            for item in video_response.get("items", []):
                video_id = item["id"]
                snippet = item["snippet"]
                live_details = item.get("liveStreamingDetails", {})

                print(f"\nChecking video: {snippet['title']}")
                print(f"Video ID: {video_id}")
                print(f"Published at: {snippet['publishedAt']}")
                print(f"Live details: {json.dumps(live_details, indent=2)}")

                if live_details.get("actualStartTime"):  # Live stream
                    print(f"Found live stream: {snippet['title']}")
                    stream_data = {
                        "videoId": video_id,
                        "title": snippet["title"],
                        "channelName": next(
                            ch["name"]
                            for ch in channels
                            if ch["youtubeChannelId"] == snippet["channelId"]
                        ),
                        "description": snippet["description"],
                        "publishedAt": snippet["publishedAt"],
                    }
                    live_streams.append(stream_data)
                elif live_details.get("scheduledStartTime"):  # Upcoming stream
                    print(f"Found upcoming stream: {snippet['title']}")
                    match_data = {
                        "videoId": video_id,
                        "title": snippet["title"],
                        "channelName": next(
                            ch["name"]
                            for ch in channels
                            if ch["youtubeChannelId"] == snippet["channelId"]
                        ),
                        "description": snippet["description"],
                        "scheduledStartTime": live_details["scheduledStartTime"],
                    }
                    upcoming_matches.append(match_data)

        except HttpError as e:
            print(f"Error fetching video details: {e}")
            continue

    print(f"\nTotal live streams found: {len(live_streams)}")
    print(f"Total upcoming streams found: {len(upcoming_matches)}")
    return live_streams, upcoming_matches


def main():
    channels = load_channels()
    live_streams, upcoming_matches = get_live_streams(channels)

    # Sort upcoming matches by scheduled start time
    upcoming_matches.sort(key=lambda x: x["scheduledStartTime"])

    # Load existing data to check for changes
    try:
        with open("data/streams.json", "r") as f:
            existing_data = json.load(f)
            existing_live = existing_data.get("liveStreams", [])
            existing_upcoming = existing_data.get("upcomingMatches", [])
            last_changed = existing_data.get("lastChanged")
    except (FileNotFoundError, json.JSONDecodeError):
        existing_live = []
        existing_upcoming = []
        last_changed = None

    # Check if there are any changes
    has_changes = json.dumps(live_streams, sort_keys=True) != json.dumps(
        existing_live, sort_keys=True
    ) or json.dumps(upcoming_matches, sort_keys=True) != json.dumps(
        existing_upcoming, sort_keys=True
    )

    # Create output data
    output_data = {
        "liveStreams": live_streams,
        "upcomingMatches": upcoming_matches,
    }

    # Only update lastChanged if there are actual changes
    if has_changes:
        output_data["lastChanged"] = datetime.now(timezone.utc).isoformat()
    elif last_changed:
        output_data["lastChanged"] = last_changed

    # Write to file
    with open("data/streams.json", "w") as f:
        json.dump(output_data, f, indent=2)


if __name__ == "__main__":
    main()

import os
import json
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from atproto import Client, client_utils

# YouTube API setup
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)

# Bluesky setup
BLUESKY_USERNAME = os.environ.get("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.environ.get("BLUESKY_PASSWORD")


def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def load_existing_streams():
    try:
        with open("data/streams.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"liveStreams": [], "upcomingMatches": [], "lastChanged": None}


def get_live_streams(channels):
    live_streams = []
    upcoming_matches = []
    all_video_ids = []
    current_time = datetime.now(timezone.utc)

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

        except HttpError as e:
            print(f'Error fetching data for {channel["name"]}: {e}')
            continue

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

                # Check for live stream (must have actualStartTime but no actualEndTime)
                if live_details.get("actualStartTime") and not live_details.get(
                    "actualEndTime"
                ):
                    stream_data = {
                        "videoId": video_id,
                        "title": snippet["title"],
                        "channelName": next(
                            ch["name"]
                            for ch in channels
                            if ch["youtubeChannelId"] == snippet["channelId"]
                        ),
                        "channelId": snippet["channelId"],
                        "description": snippet["description"],
                        "publishedAt": snippet["publishedAt"],
                    }
                    live_streams.append(stream_data)
                # Check for upcoming stream (must have scheduledStartTime in the future)
                elif live_details.get("scheduledStartTime"):
                    scheduled_time = datetime.fromisoformat(
                        live_details["scheduledStartTime"].replace("Z", "+00:00")
                    )
                    if scheduled_time > current_time:
                        match_data = {
                            "videoId": video_id,
                            "title": snippet["title"],
                            "channelName": next(
                                ch["name"]
                                for ch in channels
                                if ch["youtubeChannelId"] == snippet["channelId"]
                            ),
                            "channelId": snippet["channelId"],
                            "description": snippet["description"],
                            "scheduledStartTime": live_details["scheduledStartTime"],
                        }
                        upcoming_matches.append(match_data)

        except HttpError as e:
            print(f"Error fetching video details: {e}")
            continue

    return live_streams, upcoming_matches


def format_stream_message(streams):
    print(f"Formatting stream message for {len(streams)} streams")
    if not streams:
        return None

    # Bluesky has a 300 character limit per post
    MAX_POST_LENGTH = 300
    BASE_MESSAGE = "🔴 New live streams detected:\n\n"
    URL = "https://countycricket.live"
    URL_MESSAGE = f"\nWatch all streams at: {URL}"

    # Calculate how many streams we can fit in one post
    available_space = MAX_POST_LENGTH - len(BASE_MESSAGE) - len(URL_MESSAGE) - 10
    streams_per_post = max(
        1, available_space // 75
    )  # Estimate 75 chars per stream entry

    messages = []
    for i in range(0, len(streams), streams_per_post):
        chunk = streams[i : i + streams_per_post]

        # Create text builder for this message
        text_builder = client_utils.TextBuilder()
        text_builder.text(BASE_MESSAGE)

        for stream in chunk:
            text_builder.text(f"• {stream['channelName']}: {stream['title']}\n")

        # Add URL only to the last message
        if i + streams_per_post >= len(streams):
            text_builder.text("\n")
            # Add URL as a link facet
            text_builder.link(URL_MESSAGE, URL)

        messages.append(text_builder)

    return messages


def post_to_bluesky(messages):
    if not messages:
        return

    client = Client()
    client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

    # Create the posts in sequence, threading them together
    previous_post = None
    for text_builder in messages:
        if previous_post:
            # Create a reply to the previous post
            previous_post = client.send_post(text=text_builder, reply_to=previous_post)
        else:
            # Create the first post in the thread
            previous_post = client.send_post(text=text_builder)


def main():
    # Load existing data
    existing_data = load_existing_streams()
    existing_live = existing_data.get("liveStreams", [])
    existing_upcoming = existing_data.get("upcomingMatches", [])

    # Get new data
    channels = load_channels()
    live_streams, upcoming_matches = get_live_streams(channels)

    # Sort upcoming matches by scheduled start time
    upcoming_matches.sort(key=lambda x: x["scheduledStartTime"])

    # Check for changes
    has_changes = json.dumps(live_streams, sort_keys=True) != json.dumps(
        existing_live, sort_keys=True
    ) or json.dumps(upcoming_matches, sort_keys=True) != json.dumps(
        existing_upcoming, sort_keys=True
    )

    # Check for new live streams
    new_live_streams = [
        stream
        for stream in live_streams
        if not any(
            existing["videoId"] == stream["videoId"] for existing in existing_live
        )
    ]

    # Create output data
    output_data = {
        "liveStreams": live_streams,
        "upcomingMatches": upcoming_matches,
        "lastChanged": (
            datetime.now(timezone.utc).isoformat()
            if has_changes
            else existing_data.get("lastChanged")
        ),
    }

    # Write to file if there are changes
    if has_changes:
        with open("data/streams.json", "w") as f:
            json.dump(output_data, f, indent=2)
        print("Updated streams.json with new data")

    # Post to Bluesky if there are new live streams
    if new_live_streams:
        messages = format_stream_message(new_live_streams)
        if messages:
            post_to_bluesky(messages)
            print("Posted new streams to Bluesky")

    # Return status for GitHub Actions
    print(f"has_changes={str(has_changes).lower()}")
    print(f"has_new_streams={str(bool(new_live_streams)).lower()}")


if __name__ == "__main__":
    main()

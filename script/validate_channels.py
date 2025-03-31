import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API setup
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)


def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def search_channel(name):
    try:
        print(f"\nSearching for: {name}")
        request = youtube.search().list(
            part="snippet", q=name, type="channel", maxResults=5
        )
        response = request.execute()

        if not response.get("items"):
            print("❌ No channels found!")
            return None

        print("\nFound channels:")
        for i, item in enumerate(response["items"], 1):
            channel_id = item["snippet"]["channelId"]
            channel_title = item["snippet"]["title"]
            print(f"{i}. {channel_title}")
            print(f"   ID: {channel_id}")
            print(f"   URL: https://www.youtube.com/channel/{channel_id}")

        return response["items"]

    except HttpError as e:
        print(f"❌ Error searching for {name}: {e}")
        return None


def validate_channels():
    channels = load_channels()

    for channel in channels:
        try:
            print(f"\nValidating: {channel['name']}")
            print(f"Current ID: {channel['youtubeChannelId']}")

            # Get channel details
            request = youtube.channels().list(
                part="snippet", id=channel["youtubeChannelId"]
            )
            response = request.execute()

            if not response.get("items"):
                print("❌ Channel not found!")
                print("Searching for correct channel...")
                search_channel(channel["name"])
                continue

            channel_info = response["items"][0]["snippet"]
            print(f"Found channel: {channel_info['title']}")
            print(
                f"Channel URL: https://www.youtube.com/channel/{channel['youtubeChannelId']}"
            )

            # Check if the found title matches our expected name
            if channel_info["title"].lower() != channel["name"].lower():
                print("⚠️ Warning: Channel name mismatch!")
                print(f"Expected: {channel['name']}")
                print(f"Found: {channel_info['title']}")
                print("Searching for correct channel...")
                search_channel(channel["name"])
            else:
                print("✅ Channel name matches")

        except HttpError as e:
            print(f"❌ Error: {e}")
            continue


if __name__ == "__main__":
    validate_channels()

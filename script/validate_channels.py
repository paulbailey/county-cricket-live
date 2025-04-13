import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables from .env file
load_dotenv()

# YouTube API setup
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)


def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def save_channels(channels):
    with open("channels.json", "w") as f:
        json.dump(channels, f, indent=2)


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
    updated = False

    for county, channel in channels.items():
        try:
            print(f"\nValidating: {channel['name']}")
            print(f"Current ID: {channel['youtubeChannelId']}")

            # Get channel details including contentDetails to get uploads playlist
            request = youtube.channels().list(
                part="snippet,contentDetails", id=channel["youtubeChannelId"]
            )
            response = request.execute()

            if not response.get("items"):
                print("❌ Channel not found!")
                print("Searching for correct channel...")
                search_channel(channel["name"])
                continue

            channel_info = response["items"][0]["snippet"]
            content_details = response["items"][0]["contentDetails"]
            uploads_playlist_id = content_details["relatedPlaylists"]["uploads"]
            
            print(f"Found channel: {channel_info['title']}")
            print(f"Channel URL: https://www.youtube.com/channel/{channel['youtubeChannelId']}")
            print(f"Uploads Playlist ID: {uploads_playlist_id}")

            # Update the channel with uploads playlist ID if it's not already there
            if "uploadsPlaylistId" not in channel or channel["uploadsPlaylistId"] != uploads_playlist_id:
                channel["uploadsPlaylistId"] = uploads_playlist_id
                updated = True
                print("✅ Added/Updated uploads playlist ID")

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

    if updated:
        save_channels(channels)
        print("\n✅ Updated channels.json with uploads playlist IDs")


if __name__ == "__main__":
    validate_channels()

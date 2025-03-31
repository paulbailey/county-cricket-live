import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def validate_channels():
    youtube = build("youtube", "v3", developerKey=os.environ.get("GOOGLE_API_KEY"))

    for channel in load_channels():
        try:
            request = youtube.channels().list(
                part="snippet,statistics", id=channel["youtubeChannelId"]
            )
            response = request.execute()

            if "items" not in response or not response["items"]:
                print(
                    f"❌ Channel not found: {channel['name']} (ID: {channel['youtubeChannelId']})"
                )
                continue

            channel_info = response["items"][0]
            print(f"✅ Valid channel: {channel['name']}")
            print(f"   Title: {channel_info['snippet']['title']}")
            print(f"   Subscribers: {channel_info['statistics']['subscriberCount']}")
            print(f"   Videos: {channel_info['statistics']['videoCount']}")
            print(f"   Views: {channel_info['statistics']['viewCount']}")
            print()

        except HttpError as e:
            print(f"❌ Error checking channel {channel['name']}: {e}")
            print()
        except KeyError as e:
            print(f"❌ Unexpected API response for {channel['name']}: {e}")
            print(f"   Response: {response}")
            print()


if __name__ == "__main__":
    validate_channels()

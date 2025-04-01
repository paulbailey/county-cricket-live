import os
import json
from datetime import datetime
from atproto import Client


def load_streams():
    with open("data/streams.json", "r") as f:
        return json.load(f)


def format_stream_message(streams):
    if not streams:
        return None

    message = "🔴 New live streams detected:\n\n"
    for stream in streams:
        message += f"• {stream['channelName']}: {stream['title']}\n"

    # Add a link to the website
    message += "\nWatch all streams at: https://countycricket.live"

    return message


def post_to_bluesky(message):
    if not message:
        return

    client = Client()
    client.login(os.environ["BLUESKY_USERNAME"], os.environ["BLUESKY_PASSWORD"])

    # Create the post
    client.send_post(text=message)


def main():
    # Get the current streams
    data = load_streams()
    current_streams = data.get("liveStreams", [])

    # Get the last changed timestamp
    last_changed = datetime.fromisoformat(
        data.get("lastChanged", "2000-01-01T00:00:00+00:00")
    )

    # Only post if the streams were updated in the last 5 minutes
    if (datetime.now(last_changed.tzinfo) - last_changed).total_seconds() < 300:
        message = format_stream_message(current_streams)
        if message:
            post_to_bluesky(message)
            print("Posted to Bluesky successfully")
        else:
            print("No new streams to post")
    else:
        print("Streams not recently updated")


if __name__ == "__main__":
    main()

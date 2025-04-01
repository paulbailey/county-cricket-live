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

    # Bluesky has a 300 character limit per post
    MAX_POST_LENGTH = 300
    BASE_MESSAGE = "🔴 New live streams detected:\n\n"
    URL_MESSAGE = "\nWatch all streams at: https://countycricket.live"

    # Calculate how many streams we can fit in one post
    # Reserve space for the base message, URL message, and some buffer
    available_space = MAX_POST_LENGTH - len(BASE_MESSAGE) - len(URL_MESSAGE) - 10
    streams_per_post = max(
        1, available_space // 50
    )  # Estimate 50 chars per stream entry

    messages = []
    for i in range(0, len(streams), streams_per_post):
        chunk = streams[i : i + streams_per_post]
        message = BASE_MESSAGE

        for stream in chunk:
            message += f"• {stream['channelName']}: {stream['title']}\n"

        # Add URL only to the last message
        if i + streams_per_post >= len(streams):
            message += URL_MESSAGE

        messages.append(message)

    return messages


def post_to_bluesky(messages):
    if not messages:
        return

    client = Client()
    client.login(os.environ["BLUESKY_USERNAME"], os.environ["BLUESKY_PASSWORD"])

    # Create the posts in sequence, threading them together
    previous_post = None
    for message in messages:
        if previous_post:
            # Create a reply to the previous post
            client.send_post(text=message, reply_to=previous_post)
        else:
            # Create the first post in the thread
            previous_post = client.send_post(text=message)


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
        messages = format_stream_message(current_streams)
        if messages:
            post_to_bluesky(messages)
            print("Posted to Bluesky successfully")
        else:
            print("No new streams to post")
    else:
        print("Streams not recently updated")


if __name__ == "__main__":
    main()

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from googleapiclient.discovery import build
from atproto import Client, models
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# YouTube API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)

# Bluesky setup
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

def load_channels():
    with open("channels.json") as f:
        return json.load(f)

def load_fixtures():
    fixtures_dir = Path("public/data/fixtures")
    if not fixtures_dir.exists():
        return []
        
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fixtures_file = fixtures_dir / f"{today}.json"
    
    if not fixtures_file.exists():
        return []
        
    with open(fixtures_file) as f:
        return json.load(f)

def load_existing_streams():
    """Load existing streams from streams.json if it exists."""
    streams_file = Path("public/data/streams.json")
    if not streams_file.exists():
        return {}
        
    with open(streams_file) as f:
        return json.load(f)

def get_channel_id_for_team(team_name, channels):
    for channel in channels.values():
        if team_name == channel["name"] or team_name in channel.get("nicknames", []):
            return channel["youtubeChannelId"]
    return None

def get_live_streams(fixtures, channels):
    live_streams = []
    upcoming_matches = []
    
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture["home_team"], channels)
        if not channel_id:
            continue
            
        # Search for live streams
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            eventType="live",
            type="video",
            maxResults=10,
            order="date"  # Sort by date to get most recent first
        )
        response = request.execute()
        
        # Get the most recent live stream (first item since we sorted by date)
        items = response.get("items", [])
        if items:
            item = items[0]  # Take only the most recent stream
            stream_data = {
                "videoId": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channelName": next(
                    ch["name"]
                    for ch in channels.values()
                    if ch["youtubeChannelId"] == channel_id
                ),
                "channelId": channel_id,
                "description": item["snippet"]["description"],
                "publishedAt": item["snippet"]["publishedAt"],
                "fixture": fixture
            }
            live_streams.append(stream_data)
            
    return live_streams, upcoming_matches

def create_placeholder_streams(fixtures, channels, live_streams, upcoming_matches):
    placeholders = []
    
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture["home_team"], channels)
        if not channel_id:
            continue
            
        # Check if we already have a stream for this fixture
        has_stream = False
        for stream in live_streams + upcoming_matches:
            if stream["channelId"] == channel_id:
                has_stream = True
                break
                
        if not has_stream:
            # Create a placeholder
            placeholder = {
                "videoId": None,
                "title": f"{fixture['home_team']} vs {fixture['away_team']}",
                "channelName": next(
                    ch["name"]
                    for ch in channels.values()
                    if ch["youtubeChannelId"] == channel_id
                ),
                "channelId": channel_id,
                "description": f"{fixture['competition']} - {fixture['venue']}",
                "isPlaceholder": True,
                "fixture": fixture
            }
            placeholders.append(placeholder)
            
    return placeholders

def get_new_streams(existing_streams, new_streams):
    """Compare existing and new streams to find new fixtures that now have streams."""
    new_fixture_streams = []
    
    for comp_name, comp_data in new_streams.items():
        if comp_name not in existing_streams:
            # New competition found - all streams are new
            new_fixture_streams.extend(comp_data.get("live", []))
            continue
            
        existing_comp = existing_streams[comp_name]
        
        # Create a set of existing fixture IDs that have streams
        existing_fixture_ids = set()
        for existing_stream in existing_comp.get("live", []):
            if existing_stream.get("fixture") and not existing_stream.get("isPlaceholder"):
                fixture = existing_stream["fixture"]
                fixture_id = f"{fixture['home_team']}-{fixture['away_team']}-{fixture['start_date']}-{fixture['end_date']}"
                existing_fixture_ids.add(fixture_id)
        
        # Check for new fixtures that now have streams
        for new_stream in comp_data.get("live", []):
            if new_stream.get("isPlaceholder") or not new_stream.get("fixture"):
                continue
                
            fixture = new_stream["fixture"]
            fixture_id = f"{fixture['home_team']}-{fixture['away_team']}-{fixture['start_date']}-{fixture['end_date']}"
            
            # Only add if this is a new fixture getting a stream
            if fixture_id not in existing_fixture_ids:
                new_fixture_streams.append(new_stream)
    
    return new_fixture_streams

def post_to_bluesky(streams_data):
    """Post to Bluesky about the available streams."""
    if not streams_data:
        return
    
    client = Client()
    client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
        
    # Count only actual live streams (excluding placeholders)
    live_count = sum(
        len([s for s in comp["live"] if not s.get("isPlaceholder")])
        for comp in streams_data.values()
        if "live" in comp
    )
    
    # Create the post text
    if live_count == 0:
        text = "No live streams available today."
    else:
        text = f"📺 {live_count} live stream{'s' if live_count != 1 else ''} available:\n\n"
        
        # Add stream details
        for comp_name, comp_data in streams_data.items():
            if "live" in comp_data:
                # Filter out placeholders
                actual_streams = [s for s in comp_data["live"] if not s.get("isPlaceholder")]
                if actual_streams:
                    # Shorten competition name if needed
                    comp_short = comp_name.replace("County Championship ", "")
                    text += f"🏏 {comp_short}\n"
                    for stream in actual_streams:
                        fixture = stream["fixture"]
                        text += f"• {fixture['home_team']} v {fixture['away_team']}\n"
                    text += "\n"
    
    # Split text into chunks if needed
    chunks = []
    current_chunk = ""
    
    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 > 300:  # +1 for newline
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Post to Bluesky
    try:
        if not chunks:
            return
            
        # Post first chunk
        first_post = client.send_post(text=chunks[0])
        print("Posted first chunk to Bluesky successfully")
        
        # Post remaining chunks as replies
        for chunk in chunks[1:]:
            client.send_post(
                text=chunk,
                reply_to=models.AppBskyFeedPost.ReplyRef(
                    parent=models.AppBskyFeedPost.ReplyRefParent(
                        uri=first_post.uri,
                        cid=first_post.cid
                    ),
                    root=models.AppBskyFeedPost.ReplyRefRoot(
                        uri=first_post.uri,
                        cid=first_post.cid
                    )
                )
            )
            print("Posted reply to Bluesky successfully")
            
    except Exception as e:
        print(f"Error posting to Bluesky: {e}")
    
def main():
    channels = load_channels()
    fixtures = load_fixtures()
    
    if not fixtures:
        print("No fixtures found for today")
        return
        
    live_streams, upcoming_matches = get_live_streams(fixtures, channels)
    placeholders = create_placeholder_streams(fixtures, channels, live_streams, upcoming_matches)
    
    # Initialize competitions structure
    competitions = {}
    
    # Get unique competitions from fixtures
    for fixture in fixtures:
        competition = fixture["competition"]
        if competition not in competitions:
            competitions[competition] = {
                "live": [],
                "upcoming": []
            }
    
    # Organize live streams and placeholders by competition
    for stream in live_streams + placeholders:
        if stream["fixture"]:
            competition = stream["fixture"]["competition"]
            competitions[competition]["live"].append(stream)
    
    # Organize upcoming matches by competition
    for match in upcoming_matches:
        if match["fixture"]:
            competition = match["fixture"]["competition"]
            competitions[competition]["upcoming"].append(match)
    
    # Sort streams by home team within each competition
    for competition in competitions:
        # Sort live streams
        competitions[competition]["live"].sort(
            key=lambda x: x["fixture"]["home_team"] if x["fixture"] else ""
        )
        # Sort upcoming matches
        competitions[competition]["upcoming"].sort(
            key=lambda x: x["fixture"]["home_team"] if x["fixture"] else ""
        )
    
    # Load existing streams
    existing_streams = load_existing_streams()
    
    # Check for changes in video IDs
    has_changes = False
    if existing_streams:
        for comp_name, comp_data in competitions.items():
            if comp_name not in existing_streams:
                has_changes = True
                break
                
            existing_comp = existing_streams[comp_name]
            for new_stream in comp_data.get("live", []):
                if new_stream.get("isPlaceholder"):
                    continue
                    
                # Check if this stream is new or changed
                is_new = True
                for existing_stream in existing_comp.get("live", []):
                    if existing_stream.get("videoId") == new_stream.get("videoId"):
                        is_new = False
                        break
                        
                if is_new:
                    has_changes = True
                    break
                    
            if has_changes:
                break
    else:
        # No existing streams, so this is definitely a change
        has_changes = True
    
    # Combine all streams
    all_streams = {
        **competitions,
        "lastUpdated": datetime.now(timezone.utc).isoformat()
    }
    
    # Write to file
    output_dir = Path("public/data")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "streams.json", "w") as f:
        json.dump(all_streams, f, indent=2)
    
    print(f"Found {len(live_streams)} live streams, {len(upcoming_matches)} upcoming matches, and {len(placeholders)} placeholders")
    
    # Only post to Bluesky if there are new streams
    new_streams = get_new_streams(existing_streams, competitions)
    if new_streams:
        print(f"Found {len(new_streams)} new streams, posting to Bluesky")
        post_to_bluesky(competitions)
    else:
        print("No new streams found, skipping Bluesky post")

    print(f"has_changes={str(has_changes).lower()}")

if __name__ == "__main__":
    main() 
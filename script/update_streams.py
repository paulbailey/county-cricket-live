import os
import json
from pathlib import Path
from datetime import datetime, timezone
from googleapiclient.discovery import build
from atproto import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# YouTube API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)

# Bluesky setup
BSKY_USERNAME = os.getenv("BSKY_USERNAME")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")
client = Client()
client.login(BSKY_USERNAME, BSKY_PASSWORD)

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
            maxResults=10
        )
        response = request.execute()
        
        for item in response.get("items", []):
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

def post_to_bluesky(streams_data):
    """Post to Bluesky about the available streams."""
    if not streams_data:
        return
        
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
                    text += f"🏏 {comp_name}\n"
                    for stream in actual_streams:
                        fixture = stream["fixture"]
                        text += f"• {fixture['home_team']} vs {fixture['away_team']} at {fixture['venue']}\n"
                    text += "\n"
    
    # Post to Bluesky
    try:
        client.send_post(
            text=text,
            created_at=datetime.now(timezone.utc)
        )
        print("Posted to Bluesky successfully")
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
    
    # Post to Bluesky
    post_to_bluesky(competitions)

if __name__ == "__main__":
    main() 
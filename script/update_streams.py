import os
import json
from datetime import datetime, timezone
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API setup
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)

def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)

def load_fixtures():
    fixtures_dir = Path("public/data/fixtures")
    today = datetime.now(timezone.utc).date().isoformat()
    fixtures_file = fixtures_dir / f"{today}.json"
    
    if not fixtures_file.exists():
        return []
        
    with open(fixtures_file, "r") as f:
        return json.load(f)

def get_channel_id_for_team(team_name, channels):
    # First try exact match
    if team_name in channels:
        return channels[team_name]["youtubeChannelId"]
        
    # Then try nicknames
    for county, data in channels.items():
        if team_name in data.get("nicknames", []):
            return data["youtubeChannelId"]
            
    return None

def get_live_streams(fixtures, channels):
    live_streams = []
    upcoming_matches = []
    current_time = datetime.now(timezone.utc)
    
    # Get unique channel IDs from today's fixtures
    channel_ids = set()
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture["home_team"], channels)
        if channel_id:
            channel_ids.add(channel_id)
    
    # Get live and upcoming streams for each channel
    for channel_id in channel_ids:
        try:
            # Get channel's uploads playlist
            channel_request = youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            channel_response = channel_request.execute()
            
            if not channel_response.get("items"):
                continue
                
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get recent videos
            playlist_request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=10  # Only need recent videos
            )
            playlist_response = playlist_request.execute()
            
            video_ids = [item["contentDetails"]["videoId"] for item in playlist_response.get("items", [])]
            
            if not video_ids:
                continue
                
            # Get video details
            video_request = youtube.videos().list(
                part="snippet,liveStreamingDetails",
                id=",".join(video_ids)
            )
            video_response = video_request.execute()
            
            for item in video_response.get("items", []):
                video_id = item["id"]
                snippet = item["snippet"]
                live_details = item.get("liveStreamingDetails", {})
                
                # Find matching fixture for this channel
                matching_fixture = next(
                    (f for f in fixtures if get_channel_id_for_team(f["home_team"], channels) == channel_id),
                    None
                )
                
                # Check for live stream
                if live_details.get("actualStartTime") and not live_details.get("actualEndTime"):
                    stream_data = {
                        "videoId": video_id,
                        "title": snippet["title"],
                        "channelName": next(
                            ch["name"]
                            for ch in channels.values()
                            if ch["youtubeChannelId"] == snippet["channelId"]
                        ),
                        "channelId": snippet["channelId"],
                        "description": snippet["description"],
                        "publishedAt": snippet["publishedAt"],
                        "fixture": matching_fixture
                    }
                    live_streams.append(stream_data)
                    
                # Check for upcoming stream
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
                                for ch in channels.values()
                                if ch["youtubeChannelId"] == snippet["channelId"]
                            ),
                            "channelId": snippet["channelId"],
                            "description": snippet["description"],
                            "scheduledStartTime": live_details["scheduledStartTime"],
                            "fixture": matching_fixture
                        }
                        upcoming_matches.append(match_data)
                        
        except HttpError as e:
            print(f"Error fetching data for channel {channel_id}: {e}")
            continue
            
    return live_streams, upcoming_matches

def create_placeholder_streams(fixtures, channels, live_streams, upcoming_matches):
    placeholders = []
    current_time = datetime.now(timezone.utc)
    
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

if __name__ == "__main__":
    main() 
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
    """Load channels from channels.json file."""
    try:
        with open("channels.json") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_fixtures():
    fixtures_dir = Path("public/data/fixtures")
    if not fixtures_dir.exists():
        return []
        
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fixtures_file = fixtures_dir / f"{today}.json"
    
    if not fixtures_file.exists():
        return []
        
    try:
        with open(fixtures_file) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def load_existing_streams():
    """Load existing streams from streams.json if it exists."""
    streams_file = Path("public/data/streams.json")
    if not streams_file.exists():
        return {}
        
    try:
        with open(streams_file) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def get_channel_id_for_team(team_name, channels):
    for channel in channels.values():
        if team_name == channel["name"] or team_name in channel.get("nicknames", []):
            return channel["youtubeChannelId"]
    return None

def get_live_streams(fixtures, channels):
    live_streams = []
    upcoming_matches = []
    all_video_ids = []
    current_time = datetime.now(timezone.utc)
    
    # Create a set of channels that are actually playing today
    active_channels = set()
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture["home_team"], channels)
        if channel_id:
            active_channels.add(channel_id)
    
    # Keep track of matches we've already processed
    processed_match_ids = set()
    
    # For each active channel, get their uploads playlist
    for channel_id in active_channels:
        try:
            # Get the channel's uploads playlist ID
            channel_request = youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            channel_response = channel_request.execute()
            
            if not channel_response.get("items"):
                print(f"No channel found for ID {channel_id}")
                continue
                
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from uploads playlist
            playlist_request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50  # Maximum allowed
            )
            playlist_response = playlist_request.execute()
            
            for item in playlist_response.get("items", []):
                all_video_ids.append(item["contentDetails"]["videoId"])
                
        except Exception as e:
            print(f"Error getting playlist for channel {channel_id}: {str(e)}")
            if "quotaExceeded" in str(e):
                print("YouTube API quota exceeded. Some streams may be missing.")
                break
    
    # Get video details in batches of 50 (YouTube API limit)
    for i in range(0, len(all_video_ids), 50):
        batch = all_video_ids[i:i + 50]
        try:
            video_request = youtube.videos().list(
                part="snippet,liveStreamingDetails",
                id=",".join(batch)
            )
            video_response = video_request.execute()
            
            for item in video_response.get("items", []):
                video_id = item["id"]
                snippet = item["snippet"]
                live_details = item.get("liveStreamingDetails", {})
                
                # Find the matching fixture for this channel
                matching_fixture = next(
                    (f for f in fixtures if get_channel_id_for_team(f["home_team"], channels) == snippet["channelId"]),
                    None
                )
                
                if not matching_fixture:
                    continue

                # Skip if we've already processed this match
                match_id = matching_fixture.get("match_id")
                if match_id in processed_match_ids:
                    continue
                
                # Check for live stream (must have actualStartTime but no actualEndTime)
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
                    processed_match_ids.add(match_id)
                
                # Only check for upcoming if not already live
                elif match_id not in processed_match_ids and live_details.get("scheduledStartTime"):
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
                        processed_match_ids.add(match_id)
                            
        except Exception as e:
            print(f"Error fetching video details: {str(e)}")
            if "quotaExceeded" in str(e):
                print("YouTube API quota exceeded. Some streams may be missing.")
                break
            
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
    """Post to Bluesky about newly added streams."""
    if not streams_data:
        print("No streams_data provided, skipping Bluesky post")
        return
        
    # Skip posting if SKIP_BLUESKY_POSTING is set
    if os.getenv("SKIP_BLUESKY_POSTING", "false").lower() == "true":
        print("Skipping Bluesky post due to SKIP_BLUESKY_POSTING environment variable")
        return
    
    # Load existing streams to compare against
    existing_streams = load_existing_streams()
    
    # Get only the new streams
    new_streams = get_new_streams(existing_streams, streams_data)
    
    if not new_streams:
        print("No new streams found after comparison, skipping Bluesky post")
        return  # No new streams to post about
        
    # Verify Bluesky credentials are set
    if not BLUESKY_USERNAME or not BLUESKY_PASSWORD:
        print("ERROR: Bluesky credentials not properly set")
        return
        
    print(f"Attempting to post about {len(new_streams)} new streams to Bluesky")
    
    client = Client()
    try:
        print("Attempting to login to Bluesky...")
        client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
        print("Successfully logged in to Bluesky")
    except Exception as e:
        print(f"ERROR: Failed to login to Bluesky: {str(e)}")
        return
    
    # Create the post text
    text = "📺 New streams started:\n\n"
    
    # Group new streams by competition
    streams_by_comp = {}
    for stream in new_streams:
        comp_name = stream["fixture"]["competition"]
        if comp_name not in streams_by_comp:
            streams_by_comp[comp_name] = []
        streams_by_comp[comp_name].append(stream)
    
    # Add stream details
    for comp_name, streams in streams_by_comp.items():
        # Shorten competition name if needed
        comp_short = comp_name.replace("County Championship ", "")
        text += f"🏏 {comp_short}\n"
        for stream in streams:
            fixture = stream["fixture"]
            text += f"• {fixture['home_team']} v {fixture['away_team']}\n"
        text += "\n"
    
    print(f"Prepared post text:\n{text}")
    
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
    
    print(f"Split post into {len(chunks)} chunks")
    
    # Post to Bluesky
    try:
        if not chunks:
            print("No chunks to post")
            return
            
        # Post first chunk
        print("Posting first chunk...")
        first_post = client.send_post(text=chunks[0])
        print("Posted first chunk to Bluesky successfully")
        
        # Post remaining chunks as replies
        for i, chunk in enumerate(chunks[1:]):
            print(f"Posting chunk {i+2}...")
            # Add CTA link to the last chunk
            if i == len(chunks[1:]) - 1:
                # Create faceted link for the CTA
                cta_text = "\n\n🔗 Watch all streams at countycricket.live"
                facets = [models.AppBskyRichtext.Facet(
                    index=models.AppBskyRichtext.ByteSlice(
                        byteStart=len(chunk) + len("\n\n🔗 Watch all streams at "),
                        byteEnd=len(chunk) + len(cta_text)
                    ),
                    features=[models.AppBskyRichtext.FacetLink(uri="https://countycricket.live")]
                )]
                chunk += cta_text
            
            reply = models.AppBskyFeedPost.Reply(
                parent=models.AppBskyFeedPost.ReplyRef(
                    uri=first_post.uri,
                    cid=first_post.cid
                ),
                root=models.AppBskyFeedPost.ReplyRef(
                    uri=first_post.uri,
                    cid=first_post.cid
                )
            )
            client.send_post(text=chunk, reply_to=reply, facets=facets if i == len(chunks[1:]) - 1 else None)
            print(f"Posted chunk {i+2} successfully")
            
    except Exception as e:
        print(f"ERROR: Failed to post to Bluesky: {str(e)}")
        print(f"Error type: {type(e)}")
        if hasattr(e, '__dict__'):
            print(f"Error attributes: {e.__dict__}")

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
        "lastUpdated": datetime.now(timezone.utc).isoformat() if has_changes else existing_streams.get("lastUpdated", datetime.now(timezone.utc).isoformat())
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
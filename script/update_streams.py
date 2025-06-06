import os
import json
from pathlib import Path
from datetime import datetime, timezone
from googleapiclient.discovery import build
from atproto import Client, client_utils
from dotenv import load_dotenv
from models import Channel, VideoStream, StreamsData, Fixture, StreamInfo
from typing import Optional

# Load environment variables
load_dotenv()

# YouTube API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)

# Bluesky setup
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

def load_channels() -> dict[str, Channel]:
    """Load channels from channels.json file."""
    try:
        with open("channels.json") as f:
            data = json.load(f)
            return {id: Channel(**channel) for id, channel in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_fixtures() -> list[Fixture]:
    """Load fixtures from today's fixtures file."""
    fixtures_dir = Path("public/data/fixtures")
    if not fixtures_dir.exists():
        return []
        
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fixtures_file = fixtures_dir / f"{today}.json"
    
    if not fixtures_file.exists():
        return []
        
    try:
        with open(fixtures_file) as f:
            data = json.load(f)
            return [Fixture(**fixture) for fixture in data]
    except json.JSONDecodeError:
        return []

def load_existing_streams() -> StreamsData:
    """Load existing streams from streams.json if it exists."""
    streams_file = Path("public/data/streams.json")
    if not streams_file.exists():
        return StreamsData(
            last_updated=datetime.now(timezone.utc),
            streams={}
        )
        
    try:
        with open(streams_file) as f:
            data = json.load(f)
            return StreamsData(**data)
    except json.JSONDecodeError:
        return StreamsData(
            last_updated=datetime.now(timezone.utc),
            streams={}
        )

def get_channel_id_for_team(team_name: str, channels: dict[str, Channel]) -> Optional[str]:
    for channel in channels.values():
        if team_name == channel.name or team_name in channel.nicknames:
            return channel.youtube_channel_id
    return None

def get_live_streams(fixtures: list[Fixture], channels: dict[str, Channel]) -> tuple[list[VideoStream], list[VideoStream]]:
    live_streams = []
    upcoming_matches = []
    all_video_ids = []
    current_time = datetime.now(timezone.utc)
    
    # Create a set of channels that are actually playing today
    active_channels = set()
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture.home_team, channels)
        if channel_id:
            active_channels.add(channel_id)
    
    # Keep track of matches we've already processed
    processed_match_ids = set()
    
    # For each active channel, get their uploads playlist
    for channel_id in active_channels:
        try:
            # Get the channel's uploads playlist ID from the channel data
            channel = next((ch for ch in channels.values() if ch.youtube_channel_id == channel_id), None)
            if not channel or not channel.uploads_playlist_id:
                print(f"No uploads playlist found for channel {channel_id}")
                continue
                
            uploads_playlist_id = channel.uploads_playlist_id
            
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
                    (f for f in fixtures if get_channel_id_for_team(f.home_team, channels) == snippet["channelId"]),
                    None
                )
                
                if not matching_fixture:
                    continue

                # Skip if we've already processed this match
                match_id = matching_fixture.match_id
                if match_id in processed_match_ids:
                    continue
                
                # Check for live stream (must have actualStartTime but no actualEndTime)
                if live_details.get("actualStartTime") and not live_details.get("actualEndTime"):
                    stream_data = VideoStream(
                        video_id=video_id,
                        title=snippet["title"],
                        channel_name=next(
                            ch.name
                            for ch in channels.values()
                            if ch.youtube_channel_id == snippet["channelId"]
                        ),
                        channel_id=snippet["channelId"],
                        description=snippet["description"],
                        published_at=snippet["publishedAt"],
                        fixture=matching_fixture
                    )
                    live_streams.append(stream_data)
                    processed_match_ids.add(match_id)
                
                # Only check for upcoming if not already live
                elif match_id not in processed_match_ids and live_details.get("scheduledStartTime"):
                    scheduled_time = datetime.fromisoformat(
                        live_details["scheduledStartTime"].replace("Z", "+00:00")
                    )
                    if scheduled_time > current_time:
                        match_data = VideoStream(
                            video_id=video_id,
                            title=snippet["title"],
                            channel_name=next(
                                ch.name
                                for ch in channels.values()
                                if ch.youtube_channel_id == snippet["channelId"]
                            ),
                            channel_id=snippet["channelId"],
                            description=snippet["description"],
                            scheduled_start_time=live_details["scheduledStartTime"],
                            fixture=matching_fixture
                        )
                        upcoming_matches.append(match_data)
                        processed_match_ids.add(match_id)
                            
        except Exception as e:
            print(f"Error fetching video details: {str(e)}")
            if "quotaExceeded" in str(e):
                print("YouTube API quota exceeded. Some streams may be missing.")
                break
            
    return live_streams, upcoming_matches

def create_placeholder_streams(
    fixtures: list[Fixture],
    channels: dict[str, Channel],
    live_streams: list[VideoStream],
    upcoming_matches: list[VideoStream]
) -> list[VideoStream]:
    """Create placeholder streams for fixtures without actual streams."""
    placeholders = []
    
    for fixture in fixtures:
        channel_id = get_channel_id_for_team(fixture.home_team, channels)
        if not channel_id:
            continue
            
        # Check if we already have a stream for this fixture
        has_stream = False
        for stream in live_streams + upcoming_matches:
            if stream.channel_id == channel_id:
                has_stream = True
                break
                
        if not has_stream:
            # Create a placeholder
            placeholder = VideoStream(
                video_id=None,
                title=f"{fixture.home_team} vs {fixture.away_team}",
                channel_name=next(
                    ch.name
                    for ch in channels.values()
                    if ch.youtube_channel_id == channel_id
                ),
                channel_id=channel_id,
                description=f"{fixture.competition} - {fixture.venue}",
                is_placeholder=True,
                fixture=fixture
            )
            placeholders.append(placeholder)
            
    return placeholders

def get_new_streams(existing_streams, new_streams):
    """Compare existing and new streams to find new fixtures that now have streams."""
    new_fixture_streams = []
    
    # Remove last_updated key if it exists
    if "last_updated" in existing_streams:
        existing_streams = {k: v for k, v in existing_streams.items() if k != "last_updated"}
    if "last_updated" in new_streams:
        new_streams = {k: v for k, v in new_streams.items() if k != "last_updated"}
    
    # Compare streams for each fixture
    for fixture_id, new_stream_info in new_streams.items():
        existing_stream_info = existing_streams.get(fixture_id)
        
        # If this is a new fixture with a stream
        if not existing_stream_info and new_stream_info.get("video_id"):
            new_fixture_streams.append(new_stream_info)
            
        # If this fixture had a placeholder and now has a real stream
        elif existing_stream_info and not existing_stream_info.get("video_id") and new_stream_info.get("video_id"):
            new_fixture_streams.append(new_stream_info)
            
    return new_fixture_streams

def post_to_bluesky(match_ids: list[str], output_data: StreamsData):
    """Post to Bluesky about newly added streams."""
    
    # Skip posting if SKIP_BLUESKY_POSTING is set
    if os.getenv("SKIP_BLUESKY_POSTING", "false").lower() == "true":
        print("Skipping Bluesky post due to SKIP_BLUESKY_POSTING environment variable")
        return
    
    # Verify Bluesky credentials are set
    if not BLUESKY_USERNAME or not BLUESKY_PASSWORD:
        print("ERROR: Bluesky credentials not properly set")
        return
        
    print(f"Attempting to post about {len(match_ids)} new streams to Bluesky")
    
    client = Client()
    try:
        print("Attempting to login to Bluesky...")
        client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
        print("Successfully logged in to Bluesky")
    except Exception as e:
        print(f"ERROR: Failed to login to Bluesky: {str(e)}")
        return
    
    # Create the post text using TextBuilder
    text_builder = client_utils.TextBuilder()
    text_builder.text(f"📺 New stream{ 's' if len(match_ids) > 1 else '' } posted:\n\n")

    # Retrieve a list of fixture objects for the given match_ids, using the dict of match_id to fixture
    fixtures = load_fixtures()
    fixtures_dict = {fixture.match_id: fixture for fixture in fixtures}

    fixtures_list = [fixtures_dict[match_id] for match_id in match_ids]

    # Group fixtures by competition from the fixtures list
    fixtures_by_comp = {}
    for fixture in fixtures_list:
        if fixture.competition not in fixtures_by_comp:
            fixtures_by_comp[fixture.competition] = []
        fixtures_by_comp[fixture.competition].append(fixture)

    # Cache for resolved handles to avoid multiple API calls
    resolved_handles = {}
    
    def resolve_handle(handle: str) -> str | None:
        """Resolve a handle to a DID, using cache if available."""
        if handle in resolved_handles:
            return resolved_handles[handle]
        try:
            response = client.resolve_handle(handle)
            did = response.did
            resolved_handles[handle] = did
            print(f"Resolved handle {handle} to {did}")
            return did
        except Exception as e:
            print(f"Error resolving handle {handle}: {str(e)}")
            return None
    
    # Add stream details in alphabetical order by competition
    for comp_name in sorted(fixtures_by_comp.keys()):
        streams = fixtures_by_comp[comp_name]
        # Shorten competition name if needed
        comp_short = comp_name.replace("County Championship ", "")
        text_builder.text(f"🏏 {comp_short}\n")
        # Sort streams by home team name
        for stream_data in sorted(streams, key=lambda x: x.home_team):
            text_builder.text("• ")
            # Add home team with handle if it exists
            if stream_data.home_bluesky_handle:
                did = resolve_handle(stream_data.home_bluesky_handle)
                if did:
                    text_builder.mention(stream_data.home_team, did)
                else:
                    text_builder.text(stream_data.home_team)
            else:
                text_builder.text(stream_data.home_team)
            text_builder.text(" vs ")
            # Add away team with handle if it exists
            if stream_data.away_bluesky_handle:
                did = resolve_handle(stream_data.away_bluesky_handle)
                if did:
                    text_builder.mention(stream_data.away_team, did)
                else:
                    text_builder.text(stream_data.away_team)
            else:
                text_builder.text(stream_data.away_team)
            text_builder.text(" - ")
            video_id = output_data.streams[stream_data.match_id].video_id
            if video_id:
                text_builder.link("YT", f"https://youtube.com/watch?v={video_id}")
            else:
                text_builder.text("No stream available")
            text_builder.text("\n")
        text_builder.text("\n")
    
    # Add link at the end
    text_builder.text("\n🔗 Watch all streams at ")
    text_builder.link("countycricket.live", "https://countycricket.live")

    if len(match_ids) > 0:
        client.send_post(text=text_builder)

def format_streams_for_output(
    live_streams: list[VideoStream],
    upcoming_matches: list[VideoStream],
    placeholders: list[VideoStream]
) -> StreamsData:
    """Format streams into the final output structure."""
    output = StreamsData(
        last_updated=datetime.now(timezone.utc),
        streams={}
    )
    
    # Process all streams and add them to the streams object with match_id as key
    for stream in live_streams + upcoming_matches:
        if stream.fixture and stream.fixture.match_id:
            output.streams[stream.fixture.match_id] = StreamInfo(
                video_id=stream.video_id,
                title=stream.title,
                channel_id=stream.channel_id,
                standard_title=f"{stream.fixture.home_team} vs {stream.fixture.away_team}"
            )
    
    # Add placeholders with null videoId
    for placeholder in placeholders:
        if placeholder.fixture and placeholder.fixture.match_id:
            output.streams[placeholder.fixture.match_id] = StreamInfo(
                video_id=None,
                title=placeholder.title,
                channel_id=placeholder.channel_id,
                standard_title=f"{placeholder.fixture.home_team} vs {placeholder.fixture.away_team}"
            )
    
    # Sort streams by match_id
    output.streams = dict(sorted(output.streams.items()))
    
    return output

def main():
    try:
        # Load required data
        channels = load_channels()
        fixtures = load_fixtures()
        
        if not fixtures:
            print("No fixtures found for today")
            # Check if streams.json exists and is empty
            streams_file = Path("public/data/streams.json")
            if streams_file.exists():
                try:
                    with open(streams_file) as f:
                        data = json.load(f)
                        if not data.get("streams"):  # Check if streams is empty
                            print("Empty streams.json already exists, skipping write")
                            return
                except json.JSONDecodeError:
                    pass  # If file is invalid JSON, we'll overwrite it
            
            # Write empty streams.json
            empty_data = StreamsData(
                last_updated=datetime.now(timezone.utc),
                streams={}
            )
            with open("public/data/streams.json", "w") as f:
                data = empty_data.model_dump(by_alias=True)
                data["lastUpdated"] = data["lastUpdated"].isoformat()
                json.dump(data, f, indent=2)
            print("Successfully wrote empty streams.json")
            return
            
        # Get live and upcoming streams
        live_streams, upcoming_matches = get_live_streams(fixtures, channels)
        
        # Create placeholders for matches without streams
        placeholders = create_placeholder_streams(fixtures, channels, live_streams, upcoming_matches)
        
        # Format streams data for output
        output_data = format_streams_for_output(live_streams, upcoming_matches, placeholders)
        
        # Load existing streams data
        existing_data = load_existing_streams()
        
        # Compare streams data (excluding last_updated)
        output_streams = output_data.streams
        existing_streams = existing_data.streams
        
        if output_streams != existing_streams:
            # Only write if there are actual changes to the streams
            with open("public/data/streams.json", "w") as f:
                # Convert datetime to ISO format string for JSON serialization
                data = output_data.model_dump(by_alias=True)
                data["lastUpdated"] = data["lastUpdated"].isoformat()
                json.dump(data, f, indent=2)
            print("Successfully updated streams.json with changes")
            
            # Post new streams to Bluesky
            # Get list of match IDs with new or changed video IDs
            new_or_changed_stream_match_ids = [
                match_id for match_id, stream in output_data.streams.items()
                if stream.video_id and (
                    match_id not in existing_data.streams or 
                    existing_data.streams[match_id].video_id != stream.video_id
                )]
            # Get list of match IDs with new or changed video IDs
            if len(new_or_changed_stream_match_ids) > 0:
                post_to_bluesky(new_or_changed_stream_match_ids, output_data)
        else:
            print("No changes detected in streams data, skipping write")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 
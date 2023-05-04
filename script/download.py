import json
import os

from googleapiclient.discovery import build

with open("channels.json") as json_counties:
    counties = json.load(json_counties)
    youtube_service = build("youtube", "v3", developerKey=os.environ["GOOGLE_API_KEY"])
    # for county in counties:
    #     channel_id = county["youtubeChannelId"]
    #     print(f"Scanning {county['name']} - {county['youtubeChannelId']}")
    #     playlist_request = youtube_service.channels().list(
    #         part="snippet", id=channel_id
    #     )
    #     playlist_response = playlist_request.execute()
    #     print(playlist_response)
        # playlist_items = playlist_response["items"]
        # live_playlist_id = playlist_items[0]["contentDetails"]["relatedPlaylists"][
        #     "live"
        # ]
        # upcoming_playlist_id = playlist_items[0]["contentDetails"]["relatedPlaylists"][
        #     "upcoming"
        # ]

        # # Retrieve the video IDs of the "Live" videos
        # live_videos_request = youtube_service.playlistItems().list(
        #     part="contentDetails", playlistId=live_playlist_id
        # )
        # live_videos_response = live_videos_request.execute()
        # live_videos = live_videos_response["items"]
        # live_video_ids = [video["contentDetails"]["videoId"] for video in live_videos]

        # # Retrieve the video IDs of the "Upcoming" videos
        # upcoming_videos_request = youtube_service.playlistItems().list(
        #     part="contentDetails", playlistId=upcoming_playlist_id
        # )
        # upcoming_videos_response = upcoming_videos_request.execute()
        # upcoming_videos = upcoming_videos_response["items"]
        # upcoming_video_ids = [
        #     video["contentDetails"]["videoId"] for video in upcoming_videos
        # ]

        # # Print the video IDs of the live and upcoming videos for the current channel
        # print(f"Channel ID: {channel_id}")
        # print(f"Live Video IDs: {live_video_ids}")
        # print(f"Upcoming Video IDs: {upcoming_video_ids}")
    youtube_service.close()

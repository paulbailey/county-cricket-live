import json
import os

from googleapiclient.discovery import build

with open("channels.json") as json_counties:
    counties = json.load(json_counties)
    youtube_service = build("youtube", "v3",developerKey=os.environ["GOOGLE_API_KEY"])
    for county in counties:
        print(f"{county['name']} - {county['youtubeChannelId']}")
    youtube_service.close()

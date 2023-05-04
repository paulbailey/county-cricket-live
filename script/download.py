import os

from googleapiclient.discovery import build

if "GOOGLE_API_KEY" in os.environ and os.environ["GOOGLE_API_KEY"] != "":
    print("API key present")
    youtube_service = build("youtube", "v3",developerKey=os.environ["GOOGLE_API_KEY"])
print("Hello world")


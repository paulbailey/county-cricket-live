from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class CompetitionType(str, Enum):
    COUNTY_CHAMPIONSHIP_DIV_ONE = "County Championship Division One"
    COUNTY_CHAMPIONSHIP_DIV_TWO = "County Championship Division Two"
    ONE_DAY_CUP = "One-Day Cup"

class Fixture(BaseModel):
    match_id: str = Field(description="Unique identifier for the match")
    competition: CompetitionType = Field(description="Type of competition")
    home_team: str = Field(description="Name of the home team")
    away_team: str = Field(description="Name of the away team")
    start_date: date = Field(description="Start date of the match")
    end_date: date = Field(description="End date of the match")
    start_time_gmt: str = Field(description="Start time in GMT (HH:MM format)")
    venue: str = Field(description="Name of the venue where the match is played")

class SeriesInfo(BaseModel):
    id: str = Field(description="Unique identifier for the series")
    name: str = Field(description="Name of the series")
    matches: list[Fixture] = Field(default_factory=list, description="List of fixtures in the series")

class APIResponse(BaseModel):
    status: str = Field(description="API response status")
    data: SeriesInfo = Field(description="Response data containing series information")

class Channel(BaseModel):
    name: str = Field(description="Name of the cricket team/channel")
    youtubeChannelId: str = Field(description="YouTube channel ID")
    nicknames: list[str] = Field(default_factory=list, description="Alternative names for the team")

class VideoStream(BaseModel):
    videoId: Optional[str] = Field(None, description="YouTube video ID")
    title: str = Field(description="Title of the stream")
    channelName: str = Field(description="Name of the channel")
    channelId: str = Field(description="YouTube channel ID")
    description: str = Field(description="Stream description")
    publishedAt: Optional[datetime] = Field(None, description="When the stream was published")
    scheduledStartTime: Optional[datetime] = Field(None, description="When the stream is scheduled to start")
    isPlaceholder: bool = Field(default=False, description="Whether this is a placeholder for an expected stream")
    fixture: Fixture = Field(description="Associated fixture information")

class StreamInfo(BaseModel):
    videoId: Optional[str] = Field(None, description="YouTube video ID")
    title: str = Field(description="Title of the stream")
    channelId: str = Field(description="YouTube channel ID")
    standardTitle: str = Field(description="Standardized title format")

class StreamsData(BaseModel):
    lastUpdated: datetime = Field(description="When the streams data was last updated")
    streams: dict[str, StreamInfo] = Field(description="Streams organized by match ID") 
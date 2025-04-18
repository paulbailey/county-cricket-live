from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CompetitionType(str, Enum):
    COUNTY_CHAMPIONSHIP_DIV_ONE = "County Championship Division One"
    COUNTY_CHAMPIONSHIP_DIV_TWO = "County Championship Division Two"
    ONE_DAY_CUP = "One-Day Cup"

class Fixture(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    match_id: str = Field(description="Unique identifier for the match", alias="matchId")
    competition: CompetitionType = Field(description="Type of competition")
    home_team: str = Field(description="Name of the home team", alias="homeTeam")
    home_bluesky_handle: str | None = Field(description="Bluesky handle of the home team", alias="homeTeamBlueskyHandle", default=None)
    away_team: str = Field(description="Name of the away team", alias="awayTeam")
    away_bluesky_handle: str | None = Field(description="Bluesky handle of the away team", alias="awayTeamBlueskyHandle", default=None)
    start_date: date = Field(description="Start date of the match", alias="startDate")
    end_date: date = Field(description="End date of the match", alias="endDate")
    start_time_gmt: str = Field(description="Start time in GMT (HH:MM format)", alias="startTimeGmt")
    venue: str = Field(description="Name of the venue where the match is played")

class SeriesInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    series_id: str = Field(description="Unique identifier for the series", alias="id")
    series_name: str = Field(description="Name of the series", alias="name")
    matches: list[Fixture] = Field(default_factory=list, description="List of fixtures in the series")

class APIResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    api_status: str = Field(description="API response status", alias="status")
    response_data: SeriesInfo = Field(description="Response data containing series information", alias="data")

class Channel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    name: str = Field(description="Name of the cricket team/channel")
    youtube_channel_id: str = Field(description="YouTube channel ID", alias="youtubeChannelId")
    nicknames: list[str] = Field(default_factory=list, description="Alternative names for the team")
    uploads_playlist_id: str = Field(description="YouTube uploads playlist ID", alias="uploadsPlaylistId")
    bluesky_handle: str | None = Field(description="Bluesky handle of the team", alias="blueskyHandle", default=None)
    
class VideoStream(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    video_id: Optional[str] = Field(None, description="YouTube video ID", alias="videoId")
    title: str = Field(description="Title of the stream")
    channel_name: str = Field(description="Name of the channel", alias="channelName")
    channel_id: str = Field(description="YouTube channel ID", alias="channelId")
    description: str = Field(description="Stream description")
    published_at: Optional[datetime] = Field(None, description="When the stream was published", alias="publishedAt")
    scheduled_start_time: Optional[datetime] = Field(None, description="When the stream is scheduled to start", alias="scheduledStartTime")
    is_placeholder: bool = Field(default=False, description="Whether this is a placeholder for an expected stream", alias="isPlaceholder")
    fixture: Fixture = Field(description="Associated fixture information")

class StreamInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    video_id: Optional[str] = Field(None, description="YouTube video ID", alias="videoId")
    title: str = Field(description="Title of the stream")
    channel_id: str = Field(description="YouTube channel ID", alias="channelId")
    standard_title: str = Field(description="Standardized title format", alias="standardTitle")

class StreamsData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    last_updated: datetime = Field(description="When the streams data was last updated", alias="lastUpdated")
    streams: dict[str, StreamInfo] = Field(description="Streams organized by match ID")

class InningsScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    innings_name: str = Field(description="Name of the innings", alias="innings")
    runs_scored: int = Field(description="Total runs scored", alias="runs")
    wickets_fallen: int = Field(description="Total wickets fallen", alias="wickets")
    overs_bowled: float = Field(description="Overs bowled", alias="overs")

class MatchScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    innings_list: list[InningsScore] = Field(description="List of innings scores", alias="innings")

class MatchDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    match_id: str = Field(description="Unique identifier for the match", alias="id")
    status: str = Field(description="Current status of the match")
    match_started: Optional[bool] = Field(None, description="Whether the match has started", alias="matchStarted")
    match_ended: Optional[bool] = Field(None, description="Whether the match has ended", alias="matchEnded")
    score: Optional[MatchScore] = Field(None, description="Current match score")

class MatchData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    match_id: str = Field(description="Unique identifier for the match", alias="id")
    venue: str = Field(description="Name of the venue")
    start_time: str = Field(description="Start time of the match", alias="startTime")
    home_team: str = Field(description="Name of the home team", alias="homeTeam")
    away_team: str = Field(description="Name of the away team", alias="awayTeam")
    scores: Optional[MatchScore] = Field(None, description="Current match score")
    status: str = Field(description="Current status of the match")
    stream: StreamInfo = Field(description="Stream information")
    match_started: Optional[bool] = Field(None, description="Whether the match has started", alias="matchStarted")
    match_ended: Optional[bool] = Field(None, description="Whether the match has ended", alias="matchEnded")

class CompetitionMatches(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    competition_name: str = Field(description="Name of the competition", alias="name")
    matches_list: list[MatchData] = Field(description="List of matches in the competition", alias="matches")

class MatchesData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    last_updated: datetime = Field(description="When the matches data was last updated", alias="lastUpdated")
    competitions: dict[str, CompetitionMatches] = Field(description="Matches organized by competition") 
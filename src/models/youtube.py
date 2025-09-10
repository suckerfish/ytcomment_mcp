"""Pydantic models for YouTube comment data."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator
import re

class CommentRequest(BaseModel):
    """Request model for downloading YouTube comments."""
    
    video_id: str = Field(
        ..., 
        min_length=11, 
        max_length=20,
        description="YouTube video ID (e.g., 'dQw4w9WgXcQ')"
    )
    limit: Optional[int] = Field(
        default=1000, 
        ge=1, 
        le=10000,
        description="Maximum number of comments to download (1-10000)"
    )
    sort: Optional[int] = Field(
        default=1,
        ge=0,
        le=1, 
        description="Sort order: 0=popular, 1=recent"
    )
    
    @validator('video_id')
    def validate_video_id(cls, v):
        """Validate YouTube video ID format."""
        # YouTube video IDs are typically 11 characters, alphanumeric with - and _
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', v):
            # Also accept longer IDs that might be valid
            if not re.match(r'^[a-zA-Z0-9_-]{11,20}$', v):
                raise ValueError('Invalid YouTube video ID format')
        return v

class YouTubeComment(BaseModel):
    """Model representing a single YouTube comment."""
    
    cid: str = Field(..., description="Comment ID")
    text: str = Field(..., description="Comment text content")
    time: str = Field(..., description="Human-readable time (e.g., '1 day ago')")
    time_parsed: float = Field(..., description="Unix timestamp")
    author: str = Field(..., description="Comment author username")
    channel: str = Field(..., description="Author's channel ID")
    votes: str = Field(..., description="Number of likes (as string)")
    replies: str = Field(..., description="Number of replies (as string)")
    photo: str = Field(..., description="Author's profile picture URL")
    heart: bool = Field(..., description="Whether comment is hearted by creator")
    reply: bool = Field(..., description="Whether this is a reply to another comment")
    
    @property
    def likes_count(self) -> int:
        """Get likes count as integer."""
        try:
            return int(self.votes)
        except ValueError:
            return 0
    
    @property
    def replies_count(self) -> int:
        """Get replies count as integer."""
        try:
            return int(self.replies)
        except ValueError:
            return 0

class SlimYouTubeComment(BaseModel):
    """Optimized comment model with only essential fields (87% size reduction)."""
    
    author: str = Field(..., description="Comment author username")
    text: str = Field(..., description="Comment text content")
    likes: int = Field(..., description="Number of likes (as integer)")
    time: str = Field(..., description="ISO timestamp or human-readable time")
    is_hearted: bool = Field(..., description="Whether comment is hearted by creator")
    
    @classmethod
    def from_full_comment(cls, comment: 'YouTubeComment') -> 'SlimYouTubeComment':
        """Convert a full YouTubeComment to slim format."""
        return cls(
            author=comment.author,
            text=comment.text,
            likes=comment.likes_count,
            time=comment.time,
            is_hearted=comment.heart
        )

class CommentsResponse(BaseModel):
    """Response model for YouTube comments download."""
    
    video_id: str = Field(..., description="YouTube video ID")
    total_comments: int = Field(..., description="Number of comments downloaded")
    comments: List[YouTubeComment] = Field(..., description="List of comments")
    request_params: CommentRequest = Field(..., description="Original request parameters")
    
    @property
    def memory_usage_mb(self) -> float:
        """Estimate memory usage in MB."""
        # Based on analysis: ~1800 bytes per comment
        return (self.total_comments * 1800) / (1024 * 1024)
    
    @property
    def top_level_comments(self) -> List[YouTubeComment]:
        """Get only top-level comments (not replies)."""
        return [c for c in self.comments if not c.reply]
    
    @property
    def replies(self) -> List[YouTubeComment]:
        """Get only reply comments."""
        return [c for c in self.comments if c.reply]

class CommentStats(BaseModel):
    """Statistics about downloaded comments."""
    
    total_comments: int
    top_level_comments: int
    replies: int
    hearted_comments: int
    average_text_length: float
    max_text_length: int
    min_text_length: int
    total_likes: int
    average_likes: float
    max_likes: int
    memory_usage_mb: float

class VideoMetadata(BaseModel):
    """YouTube video metadata from API."""
    
    video_id: str = Field(..., description="YouTube video ID")
    title: Optional[str] = Field(None, description="Video title")
    channel_title: Optional[str] = Field(None, description="Channel name")
    view_count: Optional[int] = Field(None, description="Total view count")
    like_count: Optional[int] = Field(None, description="Total like count")
    comment_count: Optional[int] = Field(None, description="Total comment count")
    published_at: Optional[str] = Field(None, description="Video publish date")
    duration: Optional[str] = Field(None, description="Video duration (ISO 8601 format)")
    description: Optional[str] = Field(None, description="Video description")

class MetadataRequest(BaseModel):
    """Request model for YouTube video metadata."""
    
    video_id: str = Field(
        ..., 
        min_length=11, 
        max_length=20,
        description="YouTube video ID"
    )
    
    @validator('video_id')
    def validate_video_id(cls, v):
        """Validate YouTube video ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]{11,20}$', v):
            raise ValueError('Invalid YouTube video ID format')
        return v

class APICommentRequest(CommentRequest):
    """Request model for API-based comment downloading."""
    
    use_api: bool = Field(
        default=True,
        description="Use YouTube Data API instead of scraper"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="YouTube Data API key (optional if set in environment)"
    )

class APICommentsResponse(CommentsResponse):
    """Response model for API-based comments with additional metadata."""
    
    quota_used: int = Field(..., description="API quota units used for this request")
    next_page_token: Optional[str] = Field(None, description="Token for next page of results")
    total_available: Optional[int] = Field(None, description="Total comments available (if known)")
    api_version: str = Field(default="v3", description="YouTube API version used")

class QuotaStatus(BaseModel):
    """Model for YouTube API quota status."""
    
    daily_usage: int = Field(..., description="Quota units used today")
    daily_limit: int = Field(..., description="Daily quota limit")
    requests_made: int = Field(..., description="Number of API requests made today")
    remaining: int = Field(..., description="Remaining quota units")
    reset_time: float = Field(..., description="Unix timestamp when quota resets")
    
    @property
    def usage_percentage(self) -> float:
        """Get quota usage as percentage."""
        return (self.daily_usage / self.daily_limit) * 100 if self.daily_limit > 0 else 0
    
    @property
    def is_near_limit(self) -> bool:
        """Check if quota usage is near the daily limit (>80%)."""
        return self.usage_percentage > 80

class ChannelSearchRequest(BaseModel):
    """Request model for searching channels by name."""
    
    channel_name: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="Channel name or partial name to search for"
    )
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of channels to return (1-50)"
    )

class ChannelInfo(BaseModel):
    """Model representing basic channel information."""
    
    channel_id: str = Field(..., description="YouTube channel ID")
    title: str = Field(..., description="Channel name/title")
    description: Optional[str] = Field(None, description="Channel description (truncated)")
    subscriber_count: Optional[int] = Field(None, description="Number of subscribers")
    video_count: Optional[int] = Field(None, description="Number of published videos")
    view_count: Optional[int] = Field(None, description="Total channel views")
    thumbnail_url: Optional[str] = Field(None, description="Channel thumbnail/avatar URL")
    custom_url: Optional[str] = Field(None, description="Channel custom URL")
    published_at: Optional[str] = Field(None, description="Channel creation date")

class ChannelSearchResponse(BaseModel):
    """Response model for channel search results."""
    
    search_query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Number of channels found")
    channels: List[ChannelInfo] = Field(..., description="List of matching channels")
    quota_used: int = Field(..., description="API quota units used")

class VideoListRequest(BaseModel):
    """Request model for listing videos from a channel."""
    
    channel_id: str = Field(
        ...,
        min_length=20,
        max_length=30,
        description="YouTube channel ID"
    )
    title_filter: Optional[str] = Field(
        None,
        description="Filter videos by title containing this text (case-insensitive)"
    )
    limit: Optional[int] = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of videos to return (1-200)"
    )
    order: Optional[str] = Field(
        default="date",
        description="Sort order: 'date' (newest first), 'relevance', 'viewCount'"
    )
    
    @validator('channel_id')
    def validate_channel_id(cls, v):
        """Validate YouTube channel ID format."""
        if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', v):
            raise ValueError('Invalid YouTube channel ID format (should start with UC and be 24 chars)')
        return v

class VideoInfo(BaseModel):
    """Model representing basic video information."""
    
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description (truncated)")
    published_at: str = Field(..., description="Video publish date")
    duration: Optional[str] = Field(None, description="Video duration")
    view_count: Optional[int] = Field(None, description="Number of views")
    like_count: Optional[int] = Field(None, description="Number of likes")
    comment_count: Optional[int] = Field(None, description="Number of comments")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail URL")

class VideoListResponse(BaseModel):
    """Response model for channel video listing."""
    
    channel_id: str = Field(..., description="Channel ID that was searched")
    title_filter: Optional[str] = Field(None, description="Title filter applied")
    total_videos_found: int = Field(..., description="Total videos found (before filtering)")
    filtered_videos_count: int = Field(..., description="Number of videos after title filtering")
    videos: List[VideoInfo] = Field(..., description="List of matching videos")
    quota_used: int = Field(..., description="API quota units used")


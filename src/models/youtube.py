"""Pydantic models for YouTube comment data."""

from typing import Optional, List
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
"""YouTube comment downloading tools for MCP server."""

import json
import subprocess
import tempfile
import os
import statistics
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastmcp.exceptions import ToolError
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.youtube import CommentRequest, YouTubeComment, CommentsResponse, CommentStats

class YouTubeCommentDownloader:
    """Handler for downloading YouTube comments."""
    
    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def _download_comments_sync(self, video_id: str, limit: int, sort: int) -> List[dict]:
        """Synchronous comment download (runs in thread pool)."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Run youtube-comment-downloader
            cmd = [
                'python', '-m', 'youtube_comment_downloader',
                '--youtubeid', video_id,
                '--output', tmp_path,
                '--limit', str(limit),
                '--sort', str(sort)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                if "Video unavailable" in error_msg or "Private video" in error_msg:
                    raise ToolError(f"Video {video_id} is unavailable or private")
                elif "No comments" in error_msg:
                    return []  # Empty result for videos with no comments
                else:
                    raise ToolError(f"Failed to download comments: {error_msg}")
                    
            # Read and parse the line-delimited JSON
            comments = []
            if os.path.exists(tmp_path):
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            try:
                                comment = json.loads(line)
                                comments.append(comment)
                            except json.JSONDecodeError as e:
                                # Log but don't fail for individual comment parse errors
                                print(f"Warning: JSON decode error on line {line_num}: {e}")
                                
            return comments
            
        except subprocess.TimeoutExpired:
            raise ToolError(f"Download timeout after {self.timeout} seconds")
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(f"Unexpected error downloading comments: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # Best effort cleanup
    
    async def download_comments(self, request: CommentRequest) -> CommentsResponse:
        """Download comments for a YouTube video."""
        
        # Validate memory usage upfront
        estimated_memory_mb = (request.limit * 1800) / (1024 * 1024)
        if estimated_memory_mb > 50:  # 50MB limit
            raise ToolError(
                f"Request too large. Estimated memory usage: {estimated_memory_mb:.1f}MB. "
                f"Maximum allowed: 50MB. Reduce limit to {int(50 * 1024 * 1024 / 1800)} or less."
            )
        
        # Run download in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        comments_data = await loop.run_in_executor(
            self.executor,
            self._download_comments_sync,
            request.video_id,
            request.limit,
            request.sort
        )
        
        # Convert to Pydantic models
        comments = []
        for comment_data in comments_data:
            try:
                comment = YouTubeComment(**comment_data)
                comments.append(comment)
            except Exception as e:
                # Log but don't fail for individual comment validation errors
                print(f"Warning: Failed to validate comment {comment_data.get('cid', 'unknown')}: {e}")
        
        return CommentsResponse(
            video_id=request.video_id,
            total_comments=len(comments),
            comments=comments,
            request_params=request
        )
    
    def calculate_stats(self, response: CommentsResponse) -> CommentStats:
        """Calculate statistics for downloaded comments."""
        if not response.comments:
            return CommentStats(
                total_comments=0,
                top_level_comments=0,
                replies=0,
                hearted_comments=0,
                average_text_length=0,
                max_text_length=0,
                min_text_length=0,
                total_likes=0,
                average_likes=0,
                max_likes=0,
                memory_usage_mb=0
            )
        
        text_lengths = [len(c.text) for c in response.comments]
        likes_counts = [c.likes_count for c in response.comments]
        
        return CommentStats(
            total_comments=response.total_comments,
            top_level_comments=len(response.top_level_comments),
            replies=len(response.replies),
            hearted_comments=sum(1 for c in response.comments if c.heart),
            average_text_length=statistics.mean(text_lengths),
            max_text_length=max(text_lengths),
            min_text_length=min(text_lengths),
            total_likes=sum(likes_counts),
            average_likes=statistics.mean(likes_counts),
            max_likes=max(likes_counts),
            memory_usage_mb=response.memory_usage_mb
        )
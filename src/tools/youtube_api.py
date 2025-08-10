"""YouTube Data API client for reliable comment retrieval."""

import os
import asyncio
import time
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import json

from fastmcp.exceptions import ToolError
from src.models.youtube import CommentRequest, YouTubeComment, CommentsResponse

# Configure logging
logger = logging.getLogger(__name__)

class QuotaManager:
    """Manages YouTube API quota usage tracking."""
    
    def __init__(self):
        self.daily_usage = 0
        self.requests_made = 0
        self.last_reset = time.time()
        self.daily_limit = 10000  # YouTube API daily quota limit
    
    def reset_if_needed(self):
        """Reset daily counters if 24 hours have passed."""
        current_time = time.time()
        if current_time - self.last_reset >= 86400:  # 24 hours
            self.daily_usage = 0
            self.requests_made = 0
            self.last_reset = current_time
    
    def check_quota(self, estimated_cost: int = 1):
        """Check if we have enough quota remaining."""
        self.reset_if_needed()
        if self.daily_usage + estimated_cost > self.daily_limit:
            raise ToolError(
                f"YouTube API daily quota limit exceeded. "
                f"Used: {self.daily_usage}/{self.daily_limit}. "
                f"Quota resets at midnight Pacific Time."
            )
    
    def record_usage(self, cost: int = 1):
        """Record quota usage."""
        self.daily_usage += cost
        self.requests_made += 1
        logger.info(f"API quota used: {cost} (total today: {self.daily_usage}/{self.daily_limit})")

class YouTubeAPIClient:
    """YouTube Data API client with authentication and error handling."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.service = None
        self.quota_manager = QuotaManager()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        if not self.api_key:
            raise ToolError(
                "YouTube API key not provided. Set YOUTUBE_API_KEY environment variable "
                "or pass api_key parameter. Get a key at: "
                "https://console.developers.google.com/apis/credentials"
            )
    
    def _build_service(self):
        """Build YouTube API service client."""
        if not self.service:
            try:
                self.service = build('youtube', 'v3', developerKey=self.api_key)
            except DefaultCredentialsError as e:
                raise ToolError(f"Invalid YouTube API key: {str(e)}")
            except Exception as e:
                raise ToolError(f"Failed to initialize YouTube API client: {str(e)}")
        return self.service
    
    def _handle_api_error(self, error: HttpError) -> None:
        """Handle YouTube API errors with specific messages."""
        error_content = error.content.decode('utf-8') if error.content else str(error)
        
        if error.resp.status == 400:
            if 'keyInvalid' in error_content:
                raise ToolError(
                    "Invalid YouTube API key. Get a valid key at: "
                    "https://console.developers.google.com/apis/credentials"
                )
            elif 'videoNotFound' in error_content:
                raise ToolError("Video not found or is private/unavailable")
            elif 'commentsDisabled' in error_content:
                raise ToolError("Comments are disabled for this video")
        elif error.resp.status == 403:
            if 'quotaExceeded' in error_content:
                raise ToolError(
                    "YouTube API daily quota exceeded (10,000 units/day). "
                    "Quota resets at midnight Pacific Time."
                )
            elif 'forbidden' in error_content.lower():
                raise ToolError("Access forbidden. Check API key permissions.")
        elif error.resp.status == 404:
            raise ToolError("Video not found")
        else:
            raise ToolError(f"YouTube API error ({error.resp.status}): {error_content}")
    
    def _sync_get_comments_page(
        self, 
        video_id: str, 
        max_results: int = 100,
        page_token: Optional[str] = None,
        order: str = 'relevance'
    ) -> Dict[str, Any]:
        """Synchronously fetch one page of comments."""
        service = self._build_service()
        
        # Check quota before making request
        self.quota_manager.check_quota(1)  # commentThreads.list costs 1 unit
        
        try:
            request = service.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=max_results,
                order=order,
                pageToken=page_token
            )
            response = request.execute()
            
            # Record quota usage
            self.quota_manager.record_usage(1)
            
            return response
            
        except HttpError as e:
            self._handle_api_error(e)
        except Exception as e:
            raise ToolError(f"Unexpected API error: {str(e)}")
    
    async def get_comments_page(
        self, 
        video_id: str, 
        max_results: int = 100,
        page_token: Optional[str] = None,
        order: str = 'relevance'
    ) -> Dict[str, Any]:
        """Asynchronously fetch one page of comments."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_get_comments_page,
            video_id,
            max_results,
            page_token,
            order
        )
    
    def _parse_comment_thread(self, thread: Dict[str, Any]) -> List[YouTubeComment]:
        """Parse a comment thread into YouTubeComment objects."""
        comments = []
        
        # Main comment
        top_comment = thread['snippet']['topLevelComment']['snippet']
        
        # Convert API response to our model format
        comment_data = {
            'cid': thread['snippet']['topLevelComment']['id'],
            'text': top_comment['textDisplay'],
            'time': top_comment['publishedAt'],
            'time_parsed': time.mktime(time.strptime(
                top_comment['publishedAt'][:19], '%Y-%m-%dT%H:%M:%S'
            )),
            'author': top_comment['authorDisplayName'],
            'channel': top_comment.get('authorChannelId', {}).get('value', '') if top_comment.get('authorChannelId') else '',
            'votes': str(top_comment.get('likeCount', 0)),
            'replies': str(thread['snippet'].get('totalReplyCount', 0)),
            'photo': top_comment.get('authorProfileImageUrl', ''),
            'heart': False,  # API doesn't provide this info
            'reply': False
        }
        
        try:
            comments.append(YouTubeComment(**comment_data))
        except Exception as e:
            logger.warning(f"Failed to parse top-level comment {comment_data['cid']}: {e}")
        
        # Replies (if any)
        if 'replies' in thread:
            for reply in thread['replies']['comments']:
                reply_snippet = reply['snippet']
                
                reply_data = {
                    'cid': reply['id'],
                    'text': reply_snippet['textDisplay'],
                    'time': reply_snippet['publishedAt'],
                    'time_parsed': time.mktime(time.strptime(
                        reply_snippet['publishedAt'][:19], '%Y-%m-%dT%H:%M:%S'
                    )),
                    'author': reply_snippet['authorDisplayName'],
                    'channel': reply_snippet.get('authorChannelId', {}).get('value', '') if reply_snippet.get('authorChannelId') else '',
                    'votes': str(reply_snippet.get('likeCount', 0)),
                    'replies': '0',  # Replies to replies aren't included
                    'photo': reply_snippet.get('authorProfileImageUrl', ''),
                    'heart': False,  # API doesn't provide this info
                    'reply': True
                }
                
                try:
                    comments.append(YouTubeComment(**reply_data))
                except Exception as e:
                    logger.warning(f"Failed to parse reply {reply_data['cid']}: {e}")
        
        return comments
    
    async def download_comments(self, request: CommentRequest) -> CommentsResponse:
        """Download comments using YouTube Data API."""
        
        # Validate memory usage upfront (same as scraper)
        estimated_memory_mb = (request.limit * 1800) / (1024 * 1024)
        if estimated_memory_mb > 50:  # 50MB limit
            raise ToolError(
                f"Request too large. Estimated memory usage: {estimated_memory_mb:.1f}MB. "
                f"Maximum allowed: 50MB. Reduce limit to {int(50 * 1024 * 1024 / 1800)} or less."
            )
        
        # Convert sort parameter (0=popular/relevance, 1=recent/time)
        order = 'time' if request.sort == 1 else 'relevance'
        
        all_comments = []
        next_page_token = None
        total_fetched = 0
        
        # Fetch comments in pages of 100 (API maximum)
        while total_fetched < request.limit:
            remaining = min(100, request.limit - total_fetched)
            
            try:
                response = await self.get_comments_page(
                    video_id=request.video_id,
                    max_results=remaining,
                    page_token=next_page_token,
                    order=order
                )
                
                if 'items' not in response or not response['items']:
                    break  # No more comments
                
                # Parse comments from this page
                for thread in response['items']:
                    page_comments = self._parse_comment_thread(thread)
                    all_comments.extend(page_comments)
                    total_fetched += len(page_comments)
                    
                    # Stop if we've reached our limit
                    if total_fetched >= request.limit:
                        break
                
                # Check for next page
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages
                    
            except ToolError:
                raise  # Re-raise our custom errors
            except Exception as e:
                raise ToolError(f"Unexpected error during comment download: {str(e)}")
        
        # Trim to exact limit if needed
        if len(all_comments) > request.limit:
            all_comments = all_comments[:request.limit]
        
        return CommentsResponse(
            video_id=request.video_id,
            total_comments=len(all_comments),
            comments=all_comments,
            request_params=request
        )
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get current quota usage status (session-based tracking only)."""
        self.quota_manager.reset_if_needed()
        return {
            'daily_usage': self.quota_manager.daily_usage,
            'daily_limit': self.quota_manager.daily_limit,
            'requests_made': self.quota_manager.requests_made,
            'remaining': self.quota_manager.daily_limit - self.quota_manager.daily_usage,
            'reset_time': self.quota_manager.last_reset + 86400  # Next reset time
        }
    
    def _try_real_quota_check(self, project_id: str = None, service_account_path: str = None) -> Optional[Dict[str, Any]]:
        """
        Attempt to check real quota usage via Google Service Usage API.
        
        NOTE: This requires:
        1. Service Usage API enabled in your Google Cloud Project
        2. Service account with serviceusage.services.get permissions
        3. Project ID where the YouTube API key was created
        
        Args:
            project_id: Google Cloud project ID (required)
            service_account_path: Path to service account JSON file (optional)
            
        Returns:
            Dict with real quota info or None if not available
        """
        if not project_id:
            return None
            
        try:
            # Try to use service account if provided
            if service_account_path and os.path.exists(service_account_path):
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                service = build('serviceusage', 'v1', credentials=credentials)
            else:
                # Fall back to API key (limited functionality)
                return None
                
            # Query YouTube Data API quotas
            service_name = f'projects/{project_id}/services/youtube.googleapis.com'
            request = service.services().consumerQuotaMetrics().list(parent=service_name)
            response = request.execute()
            
            # Parse quota metrics
            quota_info = {}
            for metric in response.get('metrics', []):
                metric_name = metric.get('displayName', metric.get('name', ''))
                for limit in metric.get('consumerQuotaLimits', []):
                    limit_name = limit.get('name', '')
                    if 'day' in limit_name.lower():  # Daily quotas
                        quota_info[metric_name] = {
                            'limit': limit.get('defaultLimit'),
                            'unit': limit.get('unit'),
                            'name': limit_name
                        }
            
            return quota_info
            
        except Exception as e:
            logger.warning(f"Could not check real quota usage: {e}")
            return None
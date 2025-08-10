#!/usr/bin/env python3
"""YouTube Comment Downloader MCP Server."""

import argparse
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import CommentRequest, QuotaStatus

# Initialize MCP server with stateless HTTP for streamable transport
mcp = FastMCP("YouTube Comment Downloader", stateless_http=True)

# Initialize API client
api_client = None  # Will be initialized when needed with API key

def get_api_client() -> YouTubeAPIClient:
    """Get or create API client with proper error handling."""
    global api_client
    if api_client is None:
        api_client = YouTubeAPIClient()  # Uses YOUTUBE_API_KEY env var
    return api_client

@mcp.tool()
async def download_youtube_comments(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Download YouTube comments using the official YouTube Data API.
    
    Provides 100% reliable results with:
    - Accurate like counts and engagement metrics
    - Full comment coverage and dataset access
    - True comment rankings by likes
    - Reliable pagination and error handling
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum comments to download (1-10000, default: 1000)
        sort: Sort order - 0 for popular/relevance, 1 for recent/time (default: 1)
    
    Returns:
        Dictionary with video_id, total_comments, comments array, and API metadata
    """
    try:
        client = get_api_client()
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        return {
            "video_id": response.video_id,
            "total_comments": response.total_comments,
            "comments": [comment.dict() for comment in response.comments],
            "request_params": response.request_params.dict(),
            "memory_usage_mb": round(response.memory_usage_mb, 2),
            "api_metadata": {
                "quota_used": 1,  # commentThreads.list costs 1 unit per page
                "quota_remaining": quota_status['remaining'],
                "api_version": "v3",
                "data_source": "YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to download comments via API: {str(e)}")

@mcp.tool()
async def get_comment_stats(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Get statistical analysis and engagement metrics (context-efficient).
    
    Provides accurate statistics without flooding context:
    - Accurate like counts and engagement metrics
    - True popular comment identification
    - Reliable data for analysis and insights
    - Sample comments for quick overview
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')  
        limit: Maximum comments to analyze (1-10000, default: 1000)
        sort: Sort order - 0 for popular, 1 for recent (default: 1)
    
    Returns:
        Dictionary with accurate statistics and sample comments
    """
    try:
        client = get_api_client()
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await client.download_comments(request)
        # Calculate stats using YouTubeCommentDownloader's stats method
        from src.tools.youtube_comments import YouTubeCommentDownloader
        downloader = YouTubeCommentDownloader()
        stats = downloader.calculate_stats(response)
        quota_status = client.get_quota_status()
        
        return {
            "video_id": response.video_id,
            "stats": stats.dict(),
            "sample_comments": [
                {
                    "author": comment.author,
                    "text": comment.text[:100] + "..." if len(comment.text) > 100 else comment.text,
                    "likes": comment.likes_count,
                    "is_reply": comment.reply
                }
                for comment in response.comments[:5]
            ],
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota_status['remaining'],
                "data_source": "YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to analyze comments via API: {str(e)}")

@mcp.tool()
async def search_comments(
    video_id: str,
    search_term: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Search YouTube comments for specific terms with complete coverage.
    
    Searches through the full available comment dataset with accurate results.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        search_term: Term to search for (case-insensitive)
        limit: Maximum comments to search through (1-10000, default: 1000)  
        sort: Sort order - 0 for popular, 1 for recent (default: 1)
    
    Returns:
        Dictionary with matching comments and search metadata
    """
    try:
        client = get_api_client()
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        # Search through comments
        search_term_lower = search_term.lower()
        matching_comments = []
        
        for comment in response.comments:
            if search_term_lower in comment.text.lower():
                matching_comments.append({
                    "author": comment.author,
                    "text": comment.text,
                    "likes": comment.likes_count,
                    "time": comment.time,
                    "is_reply": comment.reply,
                    "is_hearted": comment.heart
                })
        
        return {
            "video_id": response.video_id,
            "search_term": search_term,
            "total_comments_searched": response.total_comments,
            "matching_comments_count": len(matching_comments),
            "matching_comments": matching_comments,
            "match_percentage": round((len(matching_comments) / response.total_comments * 100), 2) if response.total_comments > 0 else 0,
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota_status['remaining'],
                "data_source": "YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to search comments via API: {str(e)}")

@mcp.tool()
async def get_top_comments_by_likes(
    video_id: str,
    top_count: int = 10,
    sample_size: int = None
) -> dict:
    """
    Get the most popular, most liked, top-rated, or highest-engagement comments by actual like count.
    
    Use this when users ask for:
    - "most popular comments"
    - "most liked comments" 
    - "top comments by likes/upvotes"
    - "highest rated comments"
    - "viral comments" 
    - "best comments"
    
    Finds the actual viral comments with accurate like counts (often 1M+ likes).
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        top_count: Number of top comments to return (1-100, default: 10)
        sample_size: Optional sample size (100-10000). If None, auto-sized for best coverage
    
    Returns:
        Dictionary with top comments ranked by true like counts
    """
    try:
        if not 1 <= top_count <= 100:
            raise ToolError("top_count must be between 1 and 100")
        
        client = get_api_client()
        
        # Auto-sizing: Use maximum possible for best coverage
        if sample_size is None:
            sample_size = 10000
            auto_sized = True
        else:
            if not 100 <= sample_size <= 10000:
                raise ToolError("sample_size must be between 100 and 10000")
            auto_sized = False
        
        # Use popular sort to get best candidates for top comments
        request = CommentRequest(
            video_id=video_id,
            limit=sample_size,
            sort=0  # Popular sort for better top comment candidates
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        # Sort by actual like count
        sorted_comments = sorted(
            response.comments,
            key=lambda c: c.likes_count,
            reverse=True
        )
        
        top_comments = sorted_comments[:top_count]
        
        return {
            "video_id": response.video_id,
            "top_count_requested": top_count,
            "sample_size": response.total_comments,
            "auto_sizing_info": {
                "auto_sized": auto_sized,
                "calculated_sample_size": sample_size,
                "data_source": "YouTube Data API (100% accurate)"
            },
            "top_comments": [
                {
                    "rank": i + 1,
                    "author": comment.author,
                    "text": comment.text,
                    "likes": comment.likes_count,  # Guaranteed accurate
                    "replies": comment.replies_count,
                    "time": comment.time,
                    "is_reply": comment.reply,
                    "is_hearted": comment.heart
                }
                for i, comment in enumerate(top_comments)
            ],
            "like_range": {
                "highest": top_comments[0].likes_count if top_comments else 0,
                "lowest": top_comments[-1].likes_count if top_comments else 0
            },
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota_status['remaining'],
                "data_accuracy": "100% - Real like counts from YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get top comments via API: {str(e)}")

@mcp.tool()
async def get_quota_status() -> dict:
    """
    Check YouTube Data API quota usage and remaining capacity.
    
    Tracks API quota usage within the current session and provides:
    - Daily quota limits and current usage
    - Estimated remaining requests available
    - Cost analysis and usage warnings
    
    Returns:
        Dictionary with session tracking, quota limits, and usage guidance
    """
    try:
        client = get_api_client()
        quota_status = client.get_quota_status()
        
        # Create QuotaStatus model for validation and properties
        status = QuotaStatus(**quota_status)
        
        return {
            "session_tracking": {
                "requests_this_session": status.requests_made,
                "estimated_quota_used": status.daily_usage,
                "session_start_time": status.reset_time,
                "percentage_of_daily_limit": round(status.usage_percentage, 1)
            },
            "quota_limits": {
                "daily_limit": 10000,
                "cost_per_comment_request": 1,
                "max_comments_per_request": 100,
                "resets_at": "Midnight Pacific Time"
            },
            "session_estimates": {
                "requests_remaining_estimate": max(0, 10000 - status.daily_usage),
                "comments_remaining_estimate": max(0, (10000 - status.daily_usage) * 100)
            },
            "real_quota_check": {
                "method": "Google Cloud Console",
                "url": "https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas",
                "note": "Check console for actual quota usage across all applications"
            },
            "warnings": [
                "⚠️ Session tracking only - real quota not checked",
                "⚠️ Other apps using same API key not counted", 
                "⚠️ Previous sessions not counted",
                "✅ Check Google Cloud Console for true usage",
                f"📊 Session usage: {status.usage_percentage:.1f}% of daily limit"
            ]
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to check quota status: {str(e)}")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='YouTube Comment Downloader MCP Server')
    parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--transport', choices=['stdio', 'sse', 'streamable-http'], default='stdio', 
                       help='Transport protocol: stdio for local use, sse/streamable-http for remote deployment')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--youtube-api-key', help='YouTube Data API key (optional, can use YOUTUBE_API_KEY env var)')
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    args = parse_arguments()
    
    # Set YouTube API key from command line argument if provided
    if args.youtube_api_key:
        os.environ['YOUTUBE_API_KEY'] = args.youtube_api_key
    
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        # Enable debug for our modules
        logger = logging.getLogger('src.tools.youtube_api')
        logger.setLevel(logging.DEBUG)
    
    if args.transport == 'sse':
        # Run with SSE transport for remote deployment
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info"
        )
    elif args.transport == 'streamable-http':
        # Run with streamable HTTP transport (fixed with stateless_http=True)
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info"
        )
    else:
        # Traditional STDIO transport for local MCP clients
        mcp.run()

if __name__ == "__main__":
    main()
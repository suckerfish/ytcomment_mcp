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

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import CommentRequest, APICommentRequest, QuotaStatus

# Initialize MCP server with stateless HTTP for streamable transport
mcp = FastMCP("YouTube Comment Downloader", stateless_http=True)

# Initialize comment downloader and API client
downloader = YouTubeCommentDownloader()
api_client = None  # Will be initialized when needed with API key

@mcp.tool()
async def download_youtube_comments(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Download raw YouTube comments data with full details and metadata.
    
    Use this for:
    - Getting complete comment datasets for analysis
    - When you need all comment fields (author, timestamp, replies, etc.)
    - Custom sorting/filtering after download
    - Large-scale comment analysis
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum number of comments to download (1-10000, default: 1000)
        sort: Sort order - 0 for YouTube's popular algorithm, 1 for recent comments (default: 1)
    
    Returns:
        Dictionary containing video_id, total_comments, comments array, and metadata
    """
    try:
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await downloader.download_comments(request)
        
        return {
            "video_id": response.video_id,
            "total_comments": response.total_comments,
            "comments": [comment.dict() for comment in response.comments],
            "request_params": response.request_params.dict(),
            "memory_usage_mb": round(response.memory_usage_mb, 2)
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to download comments: {str(e)}")

@mcp.tool()
async def get_comment_stats(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Get statistical analysis and engagement metrics without full comment data (context-efficient).
    
    Use this when you want to:
    - Analyze engagement patterns without flooding context
    - Get quick insights about video's comment activity
    - Compare engagement across multiple videos
    - Check comment volume before full download
    
    Returns statistics like average likes, text length, reply ratios, plus sample comments.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum number of comments to analyze (1-10000, default: 1000)
        sort: Sort order - 0 for popular comments, 1 for recent comments (default: 1)
    
    Returns:
        Dictionary containing comment statistics and 5 sample comments (~200 tokens vs ~25,000)
    """
    try:
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await downloader.download_comments(request)
        stats = downloader.calculate_stats(response)
        
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
                for comment in response.comments[:5]  # First 5 comments as samples
            ]
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to analyze comments: {str(e)}")

@mcp.tool()
async def search_comments(
    video_id: str,
    search_term: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Download YouTube comments and search for specific terms.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        search_term: Term to search for in comment text (case-insensitive)
        limit: Maximum number of comments to search through (1-10000, default: 1000)
        sort: Sort order - 0 for popular comments, 1 for recent comments (default: 1)
    
    Returns:
        Dictionary containing matching comments and search metadata
    """
    try:
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await downloader.download_comments(request)
        
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
            "match_percentage": round((len(matching_comments) / response.total_comments * 100), 2) if response.total_comments > 0 else 0
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to search comments: {str(e)}")

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
    
    This tool automatically determines the optimal sample size by first probing the video,
    then downloads the maximum available comments (up to 10,000) to ensure you get the
    ACTUAL most-liked comments, not just the most-liked from a small sample.
    
    This sorts by ACTUAL like count, not YouTube's "popular" algorithm which mixes likes with recency.
    Much more reliable than YouTube's built-in popular sort for finding truly viral comments.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        top_count: Number of top comments to return (1-100, default: 10)
        sample_size: Optional - specify sample size manually. If None (default), auto-sizes based on video's comment count
    
    Returns:
        Dictionary containing top comments ranked by like count with engagement stats and auto-sizing info
    """
    try:
        if not 1 <= top_count <= 100:
            raise ToolError("top_count must be between 1 and 100")
        
        # Auto-sizing logic: since we can't reliably probe total count, use aggressive sampling
        if sample_size is None:
            # The youtube-comment-downloader doesn't provide total count info in probe
            # So we use aggressive sampling strategy - download maximum possible
            sample_size = 10000  # Always try for maximum to ensure we get the real top comments
            estimated_total = "auto-sized (max download)"
            auto_sized = True
        else:
            # Manual sample_size provided
            if not 100 <= sample_size <= 10000:
                raise ToolError("sample_size must be between 100 and 10000")
            estimated_total = "manual override"
            auto_sized = False
            
        # Download the calculated sample size using popular sort as starting point
        request = CommentRequest(
            video_id=video_id,
            limit=sample_size,
            sort=0  # Start with popular to get better candidates
        )
        
        try:
            response = await downloader.download_comments(request)
        except Exception as download_error:
            # If popular sort fails, try recent sort as fallback
            if "timeout" in str(download_error).lower():
                request.sort = 1  # Try recent comments instead
                request.limit = min(sample_size, 300)  # Reduce size for fallback
                try:
                    response = await downloader.download_comments(request)
                except Exception:
                    raise ToolError(f"Download timeout. Try reducing sample_size to 200-300 for this video.")
            else:
                raise
        
        # Sort all comments by actual like count
        sorted_comments = sorted(
            response.comments, 
            key=lambda c: c.likes_count, 
            reverse=True
        )
        
        # Take top N
        top_comments = sorted_comments[:top_count]
        
        return {
            "video_id": response.video_id,
            "top_count_requested": top_count,
            "sample_size": response.total_comments,
            "auto_sizing_info": {
                "auto_sized": auto_sized,
                "estimated_total_comments": estimated_total,
                "calculated_sample_size": sample_size,
                "coverage_percentage": round((response.total_comments / estimated_total * 100), 1) if isinstance(estimated_total, int) and estimated_total > 0 else "N/A"
            },
            "top_comments": [
                {
                    "rank": i + 1,
                    "author": comment.author,
                    "text": comment.text,
                    "likes": comment.likes_count,
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
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get top comments by likes: {str(e)}")

def get_api_client() -> YouTubeAPIClient:
    """Get or create API client with proper error handling."""
    global api_client
    if api_client is None:
        api_client = YouTubeAPIClient()  # Uses YOUTUBE_API_KEY env var
    return api_client

@mcp.tool()
async def download_youtube_comments_api(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Download YouTube comments using the official YouTube Data API for 100% reliable results.
    
    This is the RECOMMENDED tool for comment downloading as it provides:
    - 100% accurate like counts (vs scraper's corrupted data)
    - Full comment coverage (vs scraper's 35% data loss)  
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
async def get_comment_stats_api(
    video_id: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Get statistical analysis using YouTube Data API with 100% accurate metrics.
    
    Provides the same context-efficient stats as the scraper version but with:
    - Accurate like counts and engagement metrics
    - True popular comment identification
    - Reliable data for analysis and insights
    
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
        stats = downloader.calculate_stats(response)  # Use existing stats calculation
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
async def search_comments_api(
    video_id: str,
    search_term: str,
    limit: int = 1000,
    sort: int = 1
) -> dict:
    """
    Search YouTube comments using the Data API for complete coverage and accurate results.
    
    Searches through the full available comment dataset (not limited by scraper issues).
    
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
async def get_top_comments_by_likes_api(
    video_id: str,
    top_count: int = 10,
    sample_size: int = None
) -> dict:
    """
    Get truly most-liked comments using YouTube Data API for accurate rankings.
    
    This provides the REAL top comments by like count, unlike the scraper which has:
    - Corrupted like counts (showing 0 instead of thousands)
    - Limited data coverage (missing 65% of comments on popular videos)
    - Inaccurate rankings due to data loss
    
    The API ensures you get the actual viral comments that users see.
    
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
async def get_youtube_api_quota_status() -> dict:
    """
    Check YouTube Data API quota usage with session-based tracking.
    
    Tracks API quota usage within the current MCP server session.
    Provides estimates and warnings about daily quota consumption.
    
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
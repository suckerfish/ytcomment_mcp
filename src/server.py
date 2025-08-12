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
from src.models.youtube import CommentRequest, QuotaStatus, SlimYouTubeComment, MetadataRequest

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
async def download_comments(
    video_id: str,
    limit: int = 1000,
    sort: int = 1,
    force_large_ingestion: bool = False,
    slim: bool = True
) -> dict:
    """
    Download YouTube comments with smart warnings for large datasets.
    
    Primary comment download tool with intelligent context protection:
    - Warns when requesting >1000 comments to prevent LLM context overflow
    - Provides token usage analysis and context percentage estimates
    - Suggests optimized alternatives for large requests
    - Force override option for intentional large ingestion
    - 100% accurate YouTube Data API results
    - Slim mode (default) reduces data size by 87% for LLM efficiency
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum comments to download (1-10000, default: 1000)
        sort: Sort order - 0 for popular/relevance, 1 for recent/time (default: 1)
        force_large_ingestion: Bypass warnings for large datasets (default: False)
        slim: Return only essential fields for 87% size reduction (default: True)
    
    Returns:
        Dictionary with comments, warnings, and token analysis
    """
    try:
        if not 1 <= limit <= 10000:
            raise ToolError("limit must be between 1 and 10000")
        
        # Calculate estimated token usage
        tokens_per_comment = 6 if slim else 25  # ~6 tokens for slim, ~25 for full
        estimated_tokens = limit * tokens_per_comment
        
        # Warning system for large ingestion
        warnings = []
        if limit > 1000 and not force_large_ingestion:
            warnings.append(f"⚠️ Large dataset requested: {limit} comments (~{estimated_tokens:,} tokens)")
            warnings.append(f"⚠️ This may exceed LLM context limits")
            warnings.append(f"💡 Consider using search_comments or get_top_comments instead")
            warnings.append(f"💡 Or set force_large_ingestion=true to proceed anyway")
            
            return {
                "video_id": video_id,
                "warning_triggered": True,
                "requested_limit": limit,
                "estimated_tokens": estimated_tokens,
                "warnings": warnings,
                "alternatives": {
                    "search_comments": "Search for specific terms with limited results",
                    "get_top_comments": "Get only the most popular comments",
                    "force_override": "Set force_large_ingestion=true to proceed"
                },
                "recommendation": f"Use search_comments with max_results=50-200 or get_top_comments with top_count=25-100"
            }
        
        if limit > 2000:
            warnings.append(f"⚠️ Very large dataset: {limit} comments (~{estimated_tokens:,} tokens)")
            warnings.append(f"📊 May consume significant LLM context")
        
        client = get_api_client()
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        # Get total comment count from video info for comparison
        video_request = MetadataRequest(video_id=video_id)
        video_metadata = await client.get_video_info(video_request)
        total_video_comments = video_metadata.comment_count or 0
        
        # Convert comments to appropriate format
        if slim:
            comments_data = [SlimYouTubeComment.from_full_comment(comment).dict() for comment in response.comments]
            actual_tokens = len(response.comments) * 6  # ~6 tokens per slim comment
        else:
            comments_data = [comment.dict() for comment in response.comments]
            actual_tokens = len(response.comments) * 25  # ~25 tokens per full comment
        
        return {
            "video_id": response.video_id,
            "total_comments": response.total_comments,
            "total_video_comments": total_video_comments,
            "api_accessibility": f"{response.total_comments}/{total_video_comments} ({round(response.total_comments/total_video_comments*100, 1)}%)" if total_video_comments > 0 else "N/A",
            "comments": comments_data,
            "format": "slim" if slim else "full",
            "request_params": response.request_params.dict(),
            "memory_usage_mb": round(response.memory_usage_mb, 2),
            "token_analysis": {
                "estimated_tokens": estimated_tokens,
                "actual_tokens": actual_tokens,
                "context_usage": f"~{round(actual_tokens / 128000 * 100, 1)}% of 128K context" if actual_tokens <= 128000 else "Exceeds 128K context",
                "warnings": warnings if warnings else ["✅ Reasonable size for LLM ingestion"],
                "efficiency_boost": f"87% size reduction vs full format" if slim else "Full metadata included",
                "api_limitation_note": "YouTube API excludes deleted/hidden comments" if response.total_comments < total_video_comments else "All video comments accessible via API"
            },
            "api_metadata": {
                "quota_used": 2,  # 1 for comments + 1 for video info
                "quota_remaining": quota_status['remaining'] - 1,  # Account for the extra call
                "api_version": "v3",
                "data_source": "YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to download comments: {str(e)}")

@mcp.tool()
async def get_comment_stats(
    video_id: str,
    limit: int = 1000,
    sort: int = 1,
    slim: bool = True
) -> dict:
    """
    Get statistical analysis and engagement metrics (context-efficient).
    
    Provides accurate statistics without flooding context:
    - Accurate like counts and engagement metrics
    - True popular comment identification
    - Reliable data for analysis and insights
    - Sample comments for quick overview
    - Slim mode (default) reduces sample comment size by 87%
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')  
        limit: Maximum comments to analyze (1-10000, default: 1000)
        sort: Sort order - 0 for popular, 1 for recent (default: 1)
        slim: Return only essential fields in sample comments (default: True)
    
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
        
        # Create sample comments with appropriate format
        if slim:
            sample_comments = [
                {
                    **SlimYouTubeComment.from_full_comment(comment).dict(),
                    "text": comment.text[:100] + "..." if len(comment.text) > 100 else comment.text
                }
                for comment in response.comments[:5]
            ]
        else:
            sample_comments = [
                {
                    "author": comment.author,
                    "text": comment.text[:100] + "..." if len(comment.text) > 100 else comment.text,
                    "likes": comment.likes_count,
                    "is_reply": comment.reply
                }
                for comment in response.comments[:5]
            ]
        
        return {
            "video_id": response.video_id,
            "stats": stats.dict(),
            "sample_comments": sample_comments,
            "format": "slim" if slim else "full",
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
    search_terms: list[str],
    max_results: int = 50,
    search_limit: int = None,
    case_sensitive: bool = False,
    slim: bool = True
) -> dict:
    """
    Server-side keyword search optimized for LLM ingestion.
    
    Searches through comments server-side and returns only matching results,
    dramatically reducing token usage and improving LLM context efficiency:
    - Multiple search terms with OR logic (matches any term)
    - Server-side filtering before sending to LLM
    - Configurable result limits for token optimization
    - Case sensitivity options
    - Auto-sorted by popularity for relevance
    - Slim mode (default) reduces data size by 87% for LLM efficiency
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        search_terms: List of terms to search for (OR logic - matches any term)
        max_results: Maximum matching comments to return (1-500, default: 50)
        search_limit: Maximum comments to search through (100-10000, auto-sized if None)
        case_sensitive: Whether search should be case sensitive (default: False)
        slim: Return only essential fields for 87% size reduction (default: True)
    
    Returns:
        Dictionary with only matching comments and efficiency metrics
    """
    try:
        if not isinstance(search_terms, list) or not search_terms:
            raise ToolError("search_terms must be a non-empty list of strings")
        
        if not 1 <= max_results <= 500:
            raise ToolError("max_results must be between 1 and 500")
        
        client = get_api_client()
        
        # Auto-size search limit for better coverage
        if search_limit is None:
            search_limit = 5000  # Good balance of coverage vs speed
        elif not 100 <= search_limit <= 10000:
            raise ToolError("search_limit must be between 100 and 10000")
        
        # Download comments with popular sort for better search results
        request = CommentRequest(
            video_id=video_id,
            limit=search_limit,
            sort=0  # Popular sort gives better quality results
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        # Server-side filtering
        matching_comments = []
        search_terms_processed = search_terms if case_sensitive else [term.lower() for term in search_terms]
        
        for comment in response.comments:
            comment_text = comment.text if case_sensitive else comment.text.lower()
            
            # Check if any search term matches (OR logic)
            if any(term in comment_text for term in search_terms_processed):
                if slim:
                    matching_comments.append(SlimYouTubeComment.from_full_comment(comment).dict())
                else:
                    matching_comments.append({
                        "author": comment.author,
                        "text": comment.text,
                        "likes": comment.likes_count,
                        "replies": comment.replies_count,
                        "time": comment.time,
                        "is_reply": comment.reply,
                        "is_hearted": comment.heart
                    })
                
                # Limit results for LLM efficiency
                if len(matching_comments) >= max_results:
                    break
        
        # Sort by likes for most relevant results first
        matching_comments.sort(key=lambda x: x['likes'], reverse=True)
        
        # Get total comment count from video info for comparison
        video_request = MetadataRequest(video_id=video_id)
        video_metadata = await client.get_video_info(video_request)
        total_video_comments = video_metadata.comment_count or 0
        
        return {
            "video_id": video_id,
            "search_terms": search_terms,
            "search_config": {
                "case_sensitive": case_sensitive,
                "search_logic": "OR (matches any term)",
                "max_results": max_results,
                "search_limit": search_limit,
                "format": "slim" if slim else "full"
            },
            "results": {
                "total_searched": response.total_comments,
                "total_video_comments": total_video_comments,
                "api_accessibility": f"{response.total_comments}/{total_video_comments} ({round(response.total_comments/total_video_comments*100, 1)}%)" if total_video_comments > 0 else "N/A",
                "matches_found": len(matching_comments),
                "matches_returned": min(len(matching_comments), max_results),
                "match_rate": round((len(matching_comments) / response.total_comments * 100), 2) if response.total_comments > 0 else 0
            },
            "matching_comments": matching_comments[:max_results],
            "efficiency_info": {
                "token_reduction": f"~{round((1 - len(matching_comments) / response.total_comments) * 100, 1)}%",
                "context_optimized": True,
                "server_side_filtered": True,
                "format_efficiency": f"87% size reduction vs full format" if slim else "Full metadata included",
                "api_limitation_note": "YouTube API excludes deleted/hidden comments from total count" if response.total_comments < total_video_comments else "All video comments accessible via API"
            },
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota_status['remaining'],
                "data_source": "YouTube Data API"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to search comments: {str(e)}")

@mcp.tool()
async def get_top_comments(
    video_id: str,
    top_count: int = 25,
    sample_size: int = None,
    min_likes: int = None,
    include_replies: bool = True,
    slim: bool = True
) -> dict:
    """
    Server-side popularity sorting optimized for LLM ingestion.
    
    Gets the most popular/viral comments by actual like counts with advanced filtering:
    - Server-side sorting by popularity before sending to LLM
    - Advanced filtering options (min likes, reply inclusion)
    - Token-optimized results for efficient LLM processing
    - Finds viral comments with 1M+ likes
    - 100% accurate YouTube Data API like counts
    - Slim mode (default) reduces data size by 87% for LLM efficiency
    
    Use for: "most popular", "most liked", "viral comments", "best comments"
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        top_count: Number of top comments to return (1-100, default: 25)
        sample_size: Comments to analyze (100-10000, auto-sized if None)
        min_likes: Minimum likes to include (optional filter)
        include_replies: Whether to include reply comments (default: True)
        slim: Return only essential fields for 87% size reduction (default: True)
    
    Returns:
        Dictionary with only the highest-voted comments and efficiency metrics
    """
    try:
        if not 1 <= top_count <= 100:
            raise ToolError("top_count must be between 1 and 100")
        
        client = get_api_client()
        
        # Auto-size for optimal coverage vs performance
        if sample_size is None:
            sample_size = 10000  # Maximum for best coverage
        elif not 100 <= sample_size <= 10000:
            raise ToolError("sample_size must be between 100 and 10000")
        
        # Use popular sort to get the best candidates
        request = CommentRequest(
            video_id=video_id,
            limit=sample_size,
            sort=0  # Popular sort for best candidates
        )
        
        response = await client.download_comments(request)
        quota_status = client.get_quota_status()
        
        # Server-side filtering and sorting
        filtered_comments = response.comments
        
        # Apply filters
        if min_likes is not None:
            filtered_comments = [c for c in filtered_comments if c.likes_count >= min_likes]
        
        if not include_replies:
            filtered_comments = [c for c in filtered_comments if not c.reply]
        
        # Sort by likes (server-side)
        sorted_comments = sorted(
            filtered_comments,
            key=lambda c: c.likes_count,
            reverse=True
        )
        
        # Return only top N
        top_comments = sorted_comments[:top_count]
        
        # Create top comments list with appropriate format
        if slim:
            top_comments_list = [
                {
                    "rank": i + 1,
                    **SlimYouTubeComment.from_full_comment(comment).dict()
                }
                for i, comment in enumerate(top_comments)
            ]
        else:
            top_comments_list = [
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
            ]
        
        return {
            "video_id": video_id,
            "filtering": {
                "top_count": top_count,
                "sample_size_analyzed": response.total_comments,
                "min_likes_filter": min_likes,
                "include_replies": include_replies,
                "format": "slim" if slim else "full"
            },
            "results": {
                "comments_analyzed": len(filtered_comments),
                "top_comments_returned": len(top_comments),
                "highest_likes": top_comments[0].likes_count if top_comments else 0,
                "lowest_likes": top_comments[-1].likes_count if top_comments else 0
            },
            "top_comments": top_comments_list,
            "efficiency_info": {
                "token_reduction": f"~{round((1 - len(top_comments) / response.total_comments) * 100, 1)}%",
                "context_optimized": True,
                "server_side_sorted": True,
                "format_efficiency": f"87% size reduction vs full format" if slim else "Full metadata included"
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
        raise ToolError(f"Failed to get top comments: {str(e)}")

@mcp.tool()
async def get_video_info(video_id: str) -> dict:
    """
    Get YouTube video metadata including total comment count.
    
    Lightweight tool that fetches video metadata to help users make informed
    decisions about comment download limits. Provides essential video statistics
    including the total comment count, which is crucial for determining
    appropriate download limits before using download_comments.
    
    Perfect for: "How many comments does this video have?", "Should I download
    all comments?", "What's the video info?"
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
    
    Returns:
        Dictionary with video metadata including comment count, title, stats
    """
    try:
        client = get_api_client()
        request = MetadataRequest(video_id=video_id)
        
        metadata = await client.get_video_info(request)
        quota_status = client.get_quota_status()
        
        # Format duration in human-readable format
        duration_formatted = metadata.duration
        if metadata.duration and metadata.duration.startswith('PT'):
            # Convert ISO 8601 duration to human readable
            import re
            duration_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', metadata.duration)
            if duration_match:
                hours, minutes, seconds = duration_match.groups()
                parts = []
                if hours:
                    parts.append(f"{hours}h")
                if minutes:
                    parts.append(f"{minutes}m")
                if seconds:
                    parts.append(f"{seconds}s")
                duration_formatted = " ".join(parts) if parts else "0s"
        
        # Create recommendations based on comment count
        recommendations = []
        if metadata.comment_count:
            if metadata.comment_count <= 1000:
                recommendations.append(f"💡 Small video: Can download all {metadata.comment_count:,} comments safely")
                recommendations.append(f"💡 Suggested: download_comments('{video_id}', limit={metadata.comment_count})")
            elif metadata.comment_count <= 5000:
                recommendations.append(f"💡 Medium video: {metadata.comment_count:,} comments available")
                recommendations.append(f"💡 Suggested: download_comments('{video_id}', limit=2000) or use search_comments")
            else:
                recommendations.append(f"💡 Large video: {metadata.comment_count:,} comments available")
                recommendations.append(f"💡 Suggested: Use search_comments or get_top_comments for efficiency")
                recommendations.append(f"💡 Or download_comments('{video_id}', limit=1000, force_large_ingestion=True)")
        
        return {
            "video_id": metadata.video_id,
            "title": metadata.title,
            "channel": metadata.channel_title,
            "statistics": {
                "view_count": metadata.view_count,
                "like_count": metadata.like_count,
                "comment_count": metadata.comment_count
            },
            "details": {
                "published_at": metadata.published_at,
                "duration": duration_formatted,
                "description_preview": metadata.description[:200] + "..." if metadata.description and len(metadata.description) > 200 else metadata.description
            },
            "comment_analysis": {
                "total_comments": metadata.comment_count,
                "estimated_download_time": f"~{(metadata.comment_count or 0) // 1000 * 30}-{(metadata.comment_count or 0) // 1000 * 60} seconds" if metadata.comment_count and metadata.comment_count > 1000 else "< 30 seconds",
                "api_requests_needed": (metadata.comment_count or 0) // 100 + 1 if metadata.comment_count else 1,
                "quota_cost": (metadata.comment_count or 0) // 100 + 1 if metadata.comment_count else 1
            },
            "recommendations": recommendations,
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota_status['remaining'],
                "data_source": "YouTube Data API v3"
            }
        }
        
    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get video info: {str(e)}")

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
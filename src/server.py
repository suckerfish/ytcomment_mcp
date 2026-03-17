#!/usr/bin/env python3
"""YouTube Comment Downloader MCP Server."""

import argparse
import re
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.youtube_api import YouTubeAPIClient
from src.tools.token_counter import ClaudeTokenCounter
from src.models.youtube import (
    CommentRequest, QuotaStatus, SlimYouTubeComment, MetadataRequest,
    ChannelSearchRequest, VideoListRequest
)


# Initialize MCP server with stateless HTTP for streamable transport
mcp = FastMCP("YouTube Comment Downloader")


# Global variable to store API key from headers (for HTTP transport)
_runtime_api_key = None

# Initialize API client and token counter
api_client = None  # Will be initialized when needed with API key
token_counter = ClaudeTokenCounter()  # Token counting using Claude patterns

# Quota state keys for session state
QUOTA_DAILY_USAGE = "quota_daily_usage"
QUOTA_REQUESTS_MADE = "quota_requests_made"
QUOTA_LAST_RESET = "quota_last_reset"
QUOTA_DAILY_LIMIT = 10000


def get_api_client() -> YouTubeAPIClient:
    """Get or create API client with proper error handling."""
    global api_client, _runtime_api_key

    # Use runtime API key if available (from HTTP headers), otherwise env var
    api_key = _runtime_api_key or os.getenv('YOUTUBE_API_KEY')

    if api_client is None or (api_key and api_key != getattr(api_client, '_api_key', None)):
        if api_key:
            # Temporarily set env var for YouTubeAPIClient
            original_key = os.getenv('YOUTUBE_API_KEY')
            os.environ['YOUTUBE_API_KEY'] = api_key
            api_client = YouTubeAPIClient()
            api_client._api_key = api_key  # Store for comparison
            if original_key:
                os.environ['YOUTUBE_API_KEY'] = original_key
            elif 'YOUTUBE_API_KEY' in os.environ:
                del os.environ['YOUTUBE_API_KEY']
        else:
            api_client = YouTubeAPIClient()  # Uses YOUTUBE_API_KEY env var
    return api_client


async def get_quota_from_state(ctx: Context) -> dict:
    """Read quota tracking from session state, resetting if 24h elapsed."""
    try:
        daily_usage = await ctx.get_state(QUOTA_DAILY_USAGE) or 0
        requests_made = await ctx.get_state(QUOTA_REQUESTS_MADE) or 0
        last_reset = await ctx.get_state(QUOTA_LAST_RESET) or time.time()
    except Exception:
        daily_usage = 0
        requests_made = 0
        last_reset = time.time()

    # Reset if 24 hours have passed
    if time.time() - last_reset >= 86400:
        daily_usage = 0
        requests_made = 0
        last_reset = time.time()
        await ctx.set_state(QUOTA_DAILY_USAGE, 0)
        await ctx.set_state(QUOTA_REQUESTS_MADE, 0)
        await ctx.set_state(QUOTA_LAST_RESET, last_reset)

    return {
        "daily_usage": daily_usage,
        "requests_made": requests_made,
        "last_reset": last_reset,
        "daily_limit": QUOTA_DAILY_LIMIT,
        "remaining": QUOTA_DAILY_LIMIT - daily_usage,
        "reset_time": last_reset + 86400,
    }


async def record_quota_usage(ctx: Context, cost: int = 1):
    """Record API quota usage in session state."""
    quota = await get_quota_from_state(ctx)
    new_usage = quota["daily_usage"] + cost
    new_requests = quota["requests_made"] + 1

    if new_usage > QUOTA_DAILY_LIMIT:
        await ctx.warning(
            f"YouTube API daily quota limit exceeded. "
            f"Used: {new_usage}/{QUOTA_DAILY_LIMIT}."
        )

    await ctx.set_state(QUOTA_DAILY_USAGE, new_usage)
    await ctx.set_state(QUOTA_REQUESTS_MADE, new_requests)
    await ctx.info(f"API quota used: {cost} (total today: {new_usage}/{QUOTA_DAILY_LIMIT})")


def format_iso_duration(duration: str | None) -> str | None:
    """Convert ISO 8601 duration (e.g. 'PT1H2M3S') to human-readable ('1h 2m 3s')."""
    if not duration or not duration.startswith('PT'):
        return duration
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return duration
    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"


# ---------------------------------------------------------------------------
# Tool annotations (read-only for all data tools, system for health_check)
# ---------------------------------------------------------------------------
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
SYSTEM_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, destructiveHint=False)


@mcp.tool(tags={"system", "read"}, annotations=SYSTEM_ANNOTATIONS)
async def health_check(ctx: Context) -> dict:
    """
    Health check endpoint for Docker deployments.

    Returns server status and basic configuration info.
    """
    try:
        client = get_api_client()
        quota = await get_quota_from_state(ctx)
        await ctx.info("Health check performed")

        return {
            "status": "healthy",
            "server": "YouTube Comment Downloader MCP",
            "api_configured": bool(os.getenv('YOUTUBE_API_KEY') or _runtime_api_key),
            "quota_session_usage": quota["requests_made"],
            "transport": "streamable-http" if hasattr(mcp, '_transport') else "stdio",
        }
    except Exception as e:
        await ctx.warning(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "server": "YouTube Comment Downloader MCP"
        }

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def download_comments(
    video_id: str,
    limit: int = None,
    sort: int = 1,
    slim: bool = True,
    ctx: Context = None
) -> dict:
    """
    Download ALL YouTube comments for CONTEXTUAL ANALYSIS by LLMs.

    BEST FOR CONTEXTUAL ANALYSIS:
    - Sentiment analysis, theme detection, overall reactions
    - Spoiler detection (LLM understands meaning, not just keywords)
    - Toxic content analysis, controversy detection
    - Opinion analysis, mood assessment
    - Any task requiring AI to understand MEANING and CONTEXT

    NOT IDEAL FOR:
    - Finding specific mentions/keywords (use search_comments instead)
    - Looking for particular usernames or exact phrases
    - When you know specific terms to search for

    Primary comment download tool - downloads ALL available comments by default:
    - Downloads ALL comments: No artificial limits or confirmations
    - Slim mode default: 87% size reduction for LLM efficiency
    - 100% accurate: YouTube Data API results with real engagement metrics
    - Token counting: Automatic token analysis with Claude tokenization patterns

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum comments to download (optional - downloads ALL if not specified)
        sort: Sort order - 0 for popular/relevance, 1 for recent/time (default: 1)
        slim: Return only essential fields for 87% size reduction (default: True)

    Returns:
        Dictionary with all comments, token analysis, and metadata
    """
    try:
        client = get_api_client()

        # Fetch video info once — used for auto-sizing and for the response
        await ctx.info(f"Fetching video info for {video_id}")
        video_request = MetadataRequest(video_id=video_id)
        video_metadata = await client.get_video_info(video_request)
        await record_quota_usage(ctx, 1)
        total_video_comments = video_metadata.comment_count or 0

        # Auto-size limit based on video comment count if not specified
        if limit is None:
            limit = total_video_comments or 10000
            await ctx.info(f"Video has {total_video_comments} comments, downloading up to {limit}")

        if not 1 <= limit <= 10000:
            raise ToolError("limit must be between 1 and 10000")

        tokens_per_comment = 6 if slim else 25
        estimated_tokens = limit * tokens_per_comment

        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )

        # Download with progress reporting
        await ctx.info(f"Starting download of up to {limit} comments for {video_id}")

        # Use paginated download with progress
        order = 'time' if sort == 1 else 'relevance'
        all_comments = []
        next_page_token = None
        total_fetched = 0
        pages_fetched = 0

        while total_fetched < limit:
            remaining = min(100, limit - total_fetched)

            response_page = await client.get_comments_page(
                video_id=video_id,
                max_results=remaining,
                page_token=next_page_token,
                order=order
            )
            await record_quota_usage(ctx, 1)
            pages_fetched += 1

            if response_page is None or 'items' not in response_page or not response_page['items']:
                break

            for thread in response_page['items']:
                page_comments = client._parse_comment_thread(thread)
                all_comments.extend(page_comments)
                total_fetched += len(page_comments)
                if total_fetched >= limit:
                    break

            # Report progress after each page
            await ctx.report_progress(
                progress=min(total_fetched, limit),
                total=limit,
                message=f"Downloaded {total_fetched} comments ({pages_fetched} pages)"
            )

            next_page_token = response_page.get('nextPageToken')
            if not next_page_token:
                break

        # Trim to exact limit
        if len(all_comments) > limit:
            all_comments = all_comments[:limit]

        await ctx.info(f"Download complete: {len(all_comments)} comments fetched")

        # Build response object for compatibility
        from src.models.youtube import CommentsResponse
        response = CommentsResponse(
            video_id=video_id,
            total_comments=len(all_comments),
            comments=all_comments,
            request_params=request
        )

        # Convert comments to appropriate format and calculate actual tokens
        if slim:
            comments_data = [SlimYouTubeComment.from_full_comment(comment).model_dump() for comment in response.comments]
        else:
            comments_data = [comment.model_dump() for comment in response.comments]

        # Calculate accurate token count using Claude tokenization patterns
        token_analysis = token_counter.count_comments_tokens(comments_data, slim_mode=slim)
        actual_tokens = token_analysis['total_tokens']

        quota = await get_quota_from_state(ctx)

        return {
            "video_id": response.video_id,
            "total_comments": response.total_comments,
            "total_video_comments": total_video_comments,
            "api_accessibility": f"{response.total_comments}/{total_video_comments} ({round(response.total_comments/total_video_comments*100, 1)}%)" if total_video_comments > 0 else "N/A",
            "comments": comments_data,
            "format": "slim" if slim else "full",
            "request_params": response.request_params.model_dump(),
            "memory_usage_mb": round(response.memory_usage_mb, 2),
            "token_analysis": {
                "estimated_tokens": estimated_tokens,
                "actual_tokens": actual_tokens,
                "token_breakdown": token_analysis['token_breakdown'],
                "average_tokens_per_comment": token_analysis['average_tokens_per_comment'],
                "context_usage": f"~{round(actual_tokens / 128000 * 100, 1)}% of 128K context" if actual_tokens <= 128000 else "Exceeds 128K context",
                "context_analysis": token_counter.get_context_analysis(actual_tokens),
                "efficiency_boost": "87% size reduction vs full format" if slim else "Full metadata included",
                "api_limitation_note": "YouTube API excludes deleted/hidden comments" if response.total_comments < total_video_comments else "All video comments accessible via API",
                "tokenization_method": "Claude tokenization patterns"
            },
            "api_metadata": {
                "quota_used": pages_fetched + 1,
                "quota_remaining": quota["remaining"],
                "api_version": "v3",
                "data_source": "YouTube Data API"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to download comments: {str(e)}")

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def get_comment_stats(
    video_id: str,
    limit: int = 2000,
    sort: int = 1,
    slim: bool = True,
    ctx: Context = None
) -> dict:
    """
    Get statistical analysis and engagement metrics from comments.

    BEST FOR QUANTITATIVE ANALYSIS:
    - Statistical overview of comment patterns
    - Engagement metrics and like distributions
    - Quick sample of comments for overview
    - Understanding video comment demographics
    - Getting metrics without downloading all comments

    FOR DEEPER ANALYSIS: If you need to analyze comment content, themes,
    or sentiment, use download_comments() instead.

    Provides accurate statistics without flooding context:
    - Accurate like counts and engagement metrics
    - True popular comment identification
    - Reliable data for analysis and insights
    - Sample comments for quick overview
    - Slim mode (default) reduces sample comment size by 87%

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        limit: Maximum comments to analyze (1-10000, default: 2000)
        sort: Sort order - 0 for popular, 1 for recent (default: 1)
        slim: Return only essential fields in sample comments (default: True)

    Returns:
        Dictionary with accurate statistics and sample comments
    """
    try:
        if not 1 <= limit <= 10000:
            raise ToolError("limit must be between 1 and 10000")

        client = get_api_client()
        request = CommentRequest(
            video_id=video_id,
            limit=limit,
            sort=sort
        )

        await ctx.info(f"Downloading up to {limit} comments for stats analysis on {video_id}")
        response = await client.download_comments(request)
        await record_quota_usage(ctx, max(1, limit // 100))

        from src.tools.youtube_comments import YouTubeCommentDownloader
        downloader = YouTubeCommentDownloader()
        stats = downloader.calculate_stats(response)

        quota = await get_quota_from_state(ctx)

        # Create sample comments with appropriate format
        if slim:
            sample_comments = [
                {
                    **SlimYouTubeComment.from_full_comment(comment).model_dump(),
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

        sample_token_analysis = token_counter.count_comments_tokens(sample_comments, slim_mode=slim)

        await ctx.info(f"Stats analysis complete: {response.total_comments} comments analyzed")

        return {
            "video_id": response.video_id,
            "stats": stats.model_dump(),
            "sample_comments": sample_comments,
            "sample_token_analysis": {
                "total_tokens": sample_token_analysis['total_tokens'],
                "average_tokens_per_comment": sample_token_analysis['average_tokens_per_comment'],
                "token_breakdown": sample_token_analysis['token_breakdown'],
                "context_analysis": token_counter.get_context_analysis(sample_token_analysis['total_tokens']),
                "tokenization_method": "Claude tokenization patterns"
            },
            "format": "slim" if slim else "full",
            "api_metadata": {
                "quota_used": max(1, limit // 100),
                "quota_remaining": quota["remaining"],
                "data_source": "YouTube Data API"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to analyze comments via API: {str(e)}")

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def search_comments(
    video_id: str,
    search_terms: list[str],
    max_results: int = 50,
    search_limit: int = None,
    case_sensitive: bool = False,
    slim: bool = True,
    ctx: Context = None
) -> dict:
    """
    Search for SPECIFIC KEYWORDS or PHRASES in comments.

    BEST FOR KEYWORD-BASED SEARCH:
    - Finding mentions of specific people, places, products, events
    - Looking for comments containing exact phrases or terms
    - When you know specific keywords to search for
    - Efficient searching in large videos (1000s of comments)
    - Finding references, quotes, or specific topics

    NOT IDEAL FOR:
    - Sentiment analysis, theme detection, mood assessment
    - Spoiler detection (spoilers often avoid obvious keywords)
    - Contextual analysis requiring understanding of meaning
    - When you want AI to analyze overall patterns/themes

    RECOMMENDATION: For analysis tasks like "check for spoilers" or "analyze sentiment",
    use download_comments() instead - it provides contextual understanding rather than
    just keyword matching.

    Server-side keyword search optimized for LLM ingestion:
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

        if search_limit is None:
            search_limit = 3000
        elif not 100 <= search_limit <= 10000:
            raise ToolError("search_limit must be between 100 and 10000")

        await ctx.info(f"Searching {search_limit} comments for terms: {search_terms}")

        request = CommentRequest(
            video_id=video_id,
            limit=search_limit,
            sort=0
        )

        response = await client.download_comments(request)
        await record_quota_usage(ctx, max(1, search_limit // 100))

        # Server-side filtering
        matching_comments = []
        search_terms_processed = search_terms if case_sensitive else [term.lower() for term in search_terms]

        for comment in response.comments:
            comment_text = comment.text if case_sensitive else comment.text.lower()

            if any(term in comment_text for term in search_terms_processed):
                if slim:
                    matching_comments.append(SlimYouTubeComment.from_full_comment(comment).model_dump())
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

                if len(matching_comments) >= max_results:
                    break

        matching_comments.sort(key=lambda x: x['likes'], reverse=True)

        token_analysis = token_counter.count_comments_tokens(matching_comments, slim_mode=slim)

        video_request = MetadataRequest(video_id=video_id)
        video_metadata = await client.get_video_info(video_request)
        await record_quota_usage(ctx, 1)
        total_video_comments = video_metadata.comment_count or 0

        quota = await get_quota_from_state(ctx)

        await ctx.info(f"Search complete: {len(matching_comments)} matches found in {response.total_comments} comments")

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
            "token_analysis": {
                "total_tokens": token_analysis['total_tokens'],
                "average_tokens_per_comment": token_analysis['average_tokens_per_comment'],
                "token_breakdown": token_analysis['token_breakdown'],
                "context_analysis": token_counter.get_context_analysis(token_analysis['total_tokens']),
                "tokenization_method": "Claude tokenization patterns"
            },
            "efficiency_info": {
                "token_reduction": f"~{round((1 - len(matching_comments) / response.total_comments) * 100, 1)}%",
                "context_optimized": True,
                "server_side_filtered": True,
                "format_efficiency": "87% size reduction vs full format" if slim else "Full metadata included",
                "api_limitation_note": "YouTube API excludes deleted/hidden comments from total count" if response.total_comments < total_video_comments else "All video comments accessible via API"
            },
            "api_metadata": {
                "quota_used": max(1, search_limit // 100) + 1,
                "quota_remaining": quota["remaining"],
                "data_source": "YouTube Data API"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to search comments: {str(e)}")

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def get_top_comments(
    video_id: str,
    top_count: int = 25,
    sample_size: int = None,
    min_likes: int = None,
    include_replies: bool = True,
    slim: bool = True,
    ctx: Context = None
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

        if sample_size is None:
            sample_size = 3000
        elif not 100 <= sample_size <= 10000:
            raise ToolError("sample_size must be between 100 and 10000")

        await ctx.info(f"Fetching top {top_count} comments from {sample_size} sample for {video_id}")

        request = CommentRequest(
            video_id=video_id,
            limit=sample_size,
            sort=0
        )

        response = await client.download_comments(request)
        await record_quota_usage(ctx, max(1, sample_size // 100))

        filtered_comments = response.comments

        if min_likes is not None:
            filtered_comments = [c for c in filtered_comments if c.likes_count >= min_likes]

        if not include_replies:
            filtered_comments = [c for c in filtered_comments if not c.reply]

        sorted_comments = sorted(
            filtered_comments,
            key=lambda c: c.likes_count,
            reverse=True
        )

        top_comments = sorted_comments[:top_count]

        if slim:
            top_comments_list = [
                {
                    "rank": i + 1,
                    **SlimYouTubeComment.from_full_comment(comment).model_dump()
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

        token_analysis = token_counter.count_comments_tokens(top_comments_list, slim_mode=slim)
        quota = await get_quota_from_state(ctx)

        await ctx.info(f"Top comments complete: returning {len(top_comments)} of {len(filtered_comments)} filtered")

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
            "token_analysis": {
                "total_tokens": token_analysis['total_tokens'],
                "average_tokens_per_comment": token_analysis['average_tokens_per_comment'],
                "token_breakdown": token_analysis['token_breakdown'],
                "context_analysis": token_counter.get_context_analysis(token_analysis['total_tokens']),
                "tokenization_method": "Claude tokenization patterns"
            },
            "efficiency_info": {
                "token_reduction": f"~{round((1 - len(top_comments) / response.total_comments) * 100, 1)}%",
                "context_optimized": True,
                "server_side_sorted": True,
                "format_efficiency": "87% size reduction vs full format" if slim else "Full metadata included"
            },
            "api_metadata": {
                "quota_used": max(1, sample_size // 100),
                "quota_remaining": quota["remaining"],
                "data_accuracy": "100% - Real like counts from YouTube Data API"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get top comments: {str(e)}")

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def get_video_info(video_id: str, ctx: Context = None) -> dict:
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

        await ctx.info(f"Fetching video info for {video_id}")
        metadata = await client.get_video_info(request)
        await record_quota_usage(ctx, 1)

        quota = await get_quota_from_state(ctx)

        duration_formatted = format_iso_duration(metadata.duration)

        recommendations = []
        if metadata.comment_count:
            if metadata.comment_count <= 1000:
                recommendations.append(f"Small video: {metadata.comment_count:,} comments available")
                recommendations.append(f"Suggested: download_comments('{video_id}') to get all comments")
            elif metadata.comment_count <= 5000:
                recommendations.append(f"Medium video: {metadata.comment_count:,} comments available")
                recommendations.append(f"Suggested: download_comments('{video_id}') or search_comments for specific terms")
            else:
                recommendations.append(f"Large video: {metadata.comment_count:,} comments available")
                recommendations.append(f"Suggested: download_comments('{video_id}') for full analysis")
                recommendations.append(f"Alternative: search_comments or get_top_comments for targeted analysis")

        await ctx.info(f"Video info retrieved: '{metadata.title}' with {metadata.comment_count or 0} comments")

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
                "estimated_download_time": f"~{max(30, (metadata.comment_count or 0) // 1000 * 30)} seconds" if metadata.comment_count and metadata.comment_count > 1000 else "< 30 seconds",
                "api_requests_needed": max(1, (metadata.comment_count or 0) // 100 + 1),
                "quota_cost": max(1, (metadata.comment_count or 0) // 100 + 1)
            },
            "recommendations": recommendations,
            "api_metadata": {
                "quota_used": 1,
                "quota_remaining": quota["remaining"],
                "data_source": "YouTube Data API v3"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get video info: {str(e)}")

@mcp.tool(tags={"read", "system"}, annotations=READ_ONLY)
async def get_quota_status(ctx: Context = None) -> dict:
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
        quota = await get_quota_from_state(ctx)
        status = QuotaStatus(**quota)

        await ctx.info(f"Quota status: {status.daily_usage}/{QUOTA_DAILY_LIMIT} used ({status.usage_percentage:.1f}%)")

        if status.is_near_limit:
            await ctx.warning(f"Quota usage is high: {status.usage_percentage:.1f}% of daily limit")

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
                "Session tracking only - real quota not checked",
                "Other apps using same API key not counted",
                "Previous sessions not counted",
                "Check Google Cloud Console for true usage",
                f"Session usage: {status.usage_percentage:.1f}% of daily limit"
            ]
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to check quota status: {str(e)}")


@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def find_channel(
    channel_name: str,
    max_results: int = 10,
    ctx: Context = None
) -> dict:
    """
    Search for YouTube channels by name or partial name.

    Find channels using partial or complete channel names. Returns channel IDs,
    subscriber counts, and other metadata needed for subsequent video searches.
    This is the first step in the workflow: find channel -> get videos -> search comments.

    Perfect for: "Find channel named...", "Search for channel...", "Get channel ID for..."

    Args:
        channel_name: Channel name or partial name to search for
        max_results: Maximum number of channels to return (1-50, default: 10)

    Returns:
        Dictionary with matching channels and their metadata
    """
    try:
        if not isinstance(channel_name, str) or not channel_name.strip():
            raise ToolError("channel_name must be a non-empty string")

        if not 1 <= max_results <= 50:
            raise ToolError("max_results must be between 1 and 50")

        client = get_api_client()
        request = ChannelSearchRequest(
            channel_name=channel_name.strip(),
            max_results=max_results
        )

        await ctx.info(f"Searching for channels matching '{channel_name}'")
        response = await client.search_channels(request)
        await record_quota_usage(ctx, response.quota_used)

        quota = await get_quota_from_state(ctx)

        formatted_channels = []
        for channel in response.channels:
            formatted_channel = {
                "channel_id": channel.channel_id,
                "title": channel.title,
                "description": channel.description,
                "subscriber_count": channel.subscriber_count,
                "video_count": channel.video_count,
                "view_count": channel.view_count,
                "custom_url": channel.custom_url,
                "thumbnail_url": channel.thumbnail_url,
                "published_at": channel.published_at
            }
            formatted_channels.append(formatted_channel)

        await ctx.info(f"Found {response.total_results} channels matching '{channel_name}'")

        return {
            "search_query": response.search_query,
            "total_results": response.total_results,
            "channels": formatted_channels,
            "usage_info": {
                "quota_used": response.quota_used,
                "quota_remaining": quota["remaining"],
                "high_cost_operation": True,
                "cost_note": "Channel search costs 100 units (1% of daily quota)"
            },
            "next_steps": {
                "get_videos": "Use get_channel_videos(channel_id, title_filter) to list videos",
                "workflow": "1. find_channel -> 2. get_channel_videos -> 3. search_comments"
            },
            "api_metadata": {
                "quota_used": response.quota_used,
                "quota_remaining": quota["remaining"],
                "data_source": "YouTube Data API v3"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to search channels: {str(e)}")

@mcp.tool(tags={"read"}, annotations=READ_ONLY)
async def get_channel_videos(
    channel_id: str,
    title_filter: str = None,
    limit: int = 50,
    order: str = "date",
    ctx: Context = None
) -> dict:
    """
    Get recent videos from a YouTube channel with optional title filtering.

    List videos from a specific channel (found via find_channel) with server-side
    title filtering. Returns video IDs, titles, and metadata needed for comment
    searching. This is the second step: find channel -> get videos -> search comments.

    Perfect for: "Get recent videos from channel...", "Find videos with 'keyword' in title..."

    Args:
        channel_id: YouTube channel ID (from find_channel results)
        title_filter: Filter videos by title containing this text (case-insensitive, optional)
        limit: Maximum number of videos to return (1-200, default: 50)
        order: Sort order - 'date' (newest first), 'relevance', 'viewCount' (default: 'date')

    Returns:
        Dictionary with filtered videos and their metadata
    """
    try:
        if not isinstance(channel_id, str) or not channel_id.strip():
            raise ToolError("channel_id must be a non-empty string")

        if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id.strip()):
            raise ToolError("Invalid YouTube channel ID format (should start with UC and be 24 chars)")

        if not 1 <= limit <= 200:
            raise ToolError("limit must be between 1 and 200")

        if order not in ['date', 'relevance', 'viewCount']:
            raise ToolError("order must be 'date', 'relevance', or 'viewCount'")

        client = get_api_client()
        request = VideoListRequest(
            channel_id=channel_id.strip(),
            title_filter=title_filter.strip() if title_filter else None,
            limit=limit,
            order=order
        )

        filter_msg = f" (filter: '{title_filter}')" if title_filter else ""
        await ctx.info(f"Getting videos for channel {channel_id}{filter_msg}")

        response = await client.get_channel_videos(request)
        await record_quota_usage(ctx, response.quota_used)

        quota = await get_quota_from_state(ctx)

        formatted_videos = []
        for video in response.videos:
            formatted_video = {
                "video_id": video.video_id,
                "title": video.title,
                "description": video.description,
                "published_at": video.published_at,
                "duration": format_iso_duration(video.duration),
                "view_count": video.view_count,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
                "thumbnail_url": video.thumbnail_url
            }
            formatted_videos.append(formatted_video)

        await ctx.info(f"Found {len(formatted_videos)} videos ({response.total_videos_found} total, {response.filtered_videos_count} after filter)")

        return {
            "channel_id": response.channel_id,
            "title_filter_applied": response.title_filter,
            "filter_efficiency": {
                "total_videos_found": response.total_videos_found,
                "after_title_filter": response.filtered_videos_count,
                "filter_rate": round((response.filtered_videos_count / response.total_videos_found * 100), 1) if response.total_videos_found > 0 else 0
            },
            "videos": formatted_videos,
            "usage_info": {
                "quota_used": response.quota_used,
                "quota_remaining": quota["remaining"],
                "high_cost_operation": True,
                "cost_note": "Video listing costs 100 units (1% of daily quota)"
            },
            "next_steps": {
                "search_comments": "Use search_comments(video_id, search_terms) on any video_id from results",
                "workflow": f"Found {len(formatted_videos)} videos ready for comment analysis",
                "example": f"search_comments('{formatted_videos[0]['video_id']}', ['keyword']) for first video" if formatted_videos else "No videos found matching criteria"
            },
            "api_metadata": {
                "quota_used": response.quota_used,
                "quota_remaining": quota["remaining"],
                "data_source": "YouTube Data API v3"
            }
        }

    except Exception as e:
        if isinstance(e, ToolError):
            raise
        raise ToolError(f"Failed to get channel videos: {str(e)}")


# ---------------------------------------------------------------------------
# Resource: Quota status as a readable resource
# ---------------------------------------------------------------------------
@mcp.resource("youtube://quota")
async def quota_resource(ctx: Context = None) -> dict:
    """Current YouTube API quota usage and remaining capacity."""
    try:
        if ctx:
            quota = await get_quota_from_state(ctx)
        else:
            # Fallback when context not available
            quota = {
                "daily_usage": 0,
                "requests_made": 0,
                "daily_limit": QUOTA_DAILY_LIMIT,
                "remaining": QUOTA_DAILY_LIMIT,
                "last_reset": time.time(),
                "reset_time": time.time() + 86400,
            }
        return {
            "daily_usage": quota["daily_usage"],
            "daily_limit": quota["daily_limit"],
            "remaining": quota["remaining"],
            "requests_made": quota["requests_made"],
            "usage_percentage": round((quota["daily_usage"] / quota["daily_limit"]) * 100, 1) if quota["daily_limit"] else 0,
            "resets_at": "Midnight Pacific Time",
            "api_configured": bool(os.getenv('YOUTUBE_API_KEY') or _runtime_api_key),
        }
    except Exception:
        return {
            "daily_usage": 0,
            "daily_limit": QUOTA_DAILY_LIMIT,
            "remaining": QUOTA_DAILY_LIMIT,
            "requests_made": 0,
            "usage_percentage": 0,
            "resets_at": "Midnight Pacific Time",
            "api_configured": bool(os.getenv('YOUTUBE_API_KEY') or _runtime_api_key),
        }


# ---------------------------------------------------------------------------
# Prompt templates for common workflows
# ---------------------------------------------------------------------------
@mcp.prompt
def analyze_video_comments(video_id: str) -> str:
    """Full comment analysis workflow for a YouTube video."""
    return (
        f"Please analyze the comments on YouTube video {video_id}.\n\n"
        "Steps:\n"
        f"1. First call get_video_info('{video_id}') to see how many comments there are\n"
        f"2. Then call download_comments('{video_id}') to get all comments\n"
        "3. Analyze the comments for:\n"
        "   - Overall sentiment (positive/negative/mixed)\n"
        "   - Main themes and topics discussed\n"
        "   - Notable or viral comments\n"
        "   - Any controversies or heated discussions\n"
        "4. Provide a summary of your findings"
    )


@mcp.prompt
def find_channel_comments(channel_name: str, search_keyword: str) -> str:
    """Channel discovery to comment search workflow."""
    return (
        f"Search for comments about '{search_keyword}' on the YouTube channel '{channel_name}'.\n\n"
        "Steps:\n"
        f"1. Call find_channel('{channel_name}') to find the channel\n"
        "2. Use the channel_id from results to call get_channel_videos(channel_id)\n"
        "3. For each relevant video, call search_comments(video_id, "
        f"['{search_keyword}'])\n"
        "4. Summarize all matching comments found across videos"
    )


@mcp.prompt
def compare_video_sentiment(video_id_1: str, video_id_2: str) -> str:
    """Compare comment sentiment between two YouTube videos."""
    return (
        f"Compare the comment sentiment between two YouTube videos.\n\n"
        "Steps:\n"
        f"1. Call get_video_info('{video_id_1}') and get_video_info('{video_id_2}')\n"
        f"2. Call download_comments('{video_id_1}') for the first video\n"
        f"3. Call download_comments('{video_id_2}') for the second video\n"
        "4. For each video, analyze:\n"
        "   - Overall sentiment distribution\n"
        "   - Key themes and topics\n"
        "   - Engagement levels (likes on comments)\n"
        "5. Compare and contrast the two videos' comment sections\n"
        "6. Highlight notable differences in audience reception"
    )


@mcp.prompt
def viral_comments_analysis(video_id: str) -> str:
    """Find and analyze viral/popular comments on a video."""
    return (
        f"Find and analyze the most viral comments on YouTube video {video_id}.\n\n"
        "Steps:\n"
        f"1. Call get_video_info('{video_id}') to understand the video\n"
        f"2. Call get_top_comments('{video_id}', top_count=50) to get the most liked comments\n"
        "3. Analyze the top comments for:\n"
        "   - Common themes among popular comments\n"
        "   - What makes these comments resonate with viewers\n"
        "   - Any patterns in viral comment style or content\n"
        "   - Engagement ratios compared to total comments\n"
        "4. Provide insights on what drives comment engagement for this video"
    )


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='YouTube Comment Downloader MCP Server')
    parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--transport', choices=['stdio', 'sse', 'streamable-http', 'dual'], default='stdio',
                       help='Transport protocol: stdio for local use, sse/streamable-http for remote deployment, dual for both')
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
        logger = logging.getLogger('src.tools.youtube_api')
        logger.setLevel(logging.DEBUG)

    if args.transport == 'sse':
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info"
        )
    elif args.transport == 'streamable-http':
        mcp.run(
            transport="streamable-http",
            stateless_http=True,
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info"
        )
    elif args.transport == 'dual':
        import threading
        import time as time_mod

        def run_http_server():
            from fastmcp import FastMCP
            http_mcp = FastMCP("YouTube Comment Downloader HTTP")
            for tool_name, tool_func in mcp._tools.items():
                http_mcp._tools[tool_name] = tool_func
            http_mcp.run(
                transport="streamable-http",
                stateless_http=True,
                host=args.host,
                port=args.port,
                log_level="debug" if args.debug else "info"
            )

        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        time_mod.sleep(2)
        print(f"HTTP server started on {args.host}:{args.port}")
        print("STDIO server starting...")
        mcp.run()
    else:
        mcp.run()

if __name__ == "__main__":
    main()

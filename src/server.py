#!/usr/bin/env python3
"""YouTube Comment Downloader MCP Server."""

import argparse
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

# Initialize MCP server with stateless HTTP for streamable transport
mcp = FastMCP("YouTube Comment Downloader", stateless_http=True)

# Initialize comment downloader
downloader = YouTubeCommentDownloader()

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
    top_count: int = 20,
    sample_size: int = 500
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
    
    This sorts by ACTUAL like count, not YouTube's "popular" algorithm which mixes likes with recency.
    More reliable than YouTube's built-in popular sort for finding truly viral comments.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        top_count: Number of top comments to return (1-100, default: 20)
        sample_size: Size of sample to download and sort from (100-2000, default: 500)
    
    Returns:
        Dictionary containing top comments ranked by like count with engagement stats
    """
    try:
        if not 1 <= top_count <= 100:
            raise ToolError("top_count must be between 1 and 100")
        if not 100 <= sample_size <= 2000:
            raise ToolError("sample_size must be between 100 and 2000")
            
        # Download a larger sample using popular sort as starting point
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

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='YouTube Comment Downloader MCP Server')
    parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--transport', choices=['stdio', 'sse', 'streamable-http'], default='stdio', 
                       help='Transport protocol: stdio for local use, sse/streamable-http for remote deployment')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to for HTTP transport (default: 127.0.0.1)')
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    args = parse_arguments()
    
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
#!/usr/bin/env python3
"""Simple test of the YouTube comment downloader functionality."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

async def test_comment_download():
    """Test downloading comments from a YouTube video."""
    
    downloader = YouTubeCommentDownloader()
    
    # Test with a popular video that should have comments
    request = CommentRequest(
        video_id="dQw4w9WgXcQ",  # Rick Roll - should have lots of comments
        limit=10,  # Small limit for testing
        sort=1  # Recent comments
    )
    
    print(f"Testing comment download for video: {request.video_id}")
    print(f"Limit: {request.limit}, Sort: {request.sort}")
    
    try:
        response = await downloader.download_comments(request)
        
        print(f"\n=== Results ===")
        print(f"Video ID: {response.video_id}")
        print(f"Total comments downloaded: {response.total_comments}")
        print(f"Memory usage: {response.memory_usage_mb:.2f} MB")
        
        print(f"\n=== Sample Comments ===")
        for i, comment in enumerate(response.comments[:3]):  # Show first 3
            print(f"\nComment {i+1}:")
            print(f"  Author: {comment.author}")
            print(f"  Text: {comment.text[:100]}{'...' if len(comment.text) > 100 else ''}")
            print(f"  Likes: {comment.likes_count}")
            print(f"  Time: {comment.time}")
            print(f"  Is reply: {comment.reply}")
        
        # Test stats calculation
        stats = downloader.calculate_stats(response)
        print(f"\n=== Statistics ===")
        print(f"Total comments: {stats.total_comments}")
        print(f"Top-level comments: {stats.top_level_comments}")
        print(f"Replies: {stats.replies}")
        print(f"Average text length: {stats.average_text_length:.1f}")
        print(f"Average likes: {stats.average_likes:.1f}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comment_download())
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)
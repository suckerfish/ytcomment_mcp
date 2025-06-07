#!/usr/bin/env python3
"""Test the top comments by likes functionality."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

async def test_top_by_likes():
    """Test getting top comments sorted by actual like count."""
    
    downloader = YouTubeCommentDownloader()
    
    # Test the logic that will be in the new MCP tool
    request = CommentRequest(
        video_id="dQw4w9WgXcQ",
        limit=500,  # Larger sample
        sort=0  # Popular starting point
    )
    
    print("Testing top comments by likes...")
    print(f"Downloading {request.limit} comments from popular sort...")
    
    try:
        response = await downloader.download_comments(request)
        
        # Sort by actual like count
        sorted_comments = sorted(
            response.comments, 
            key=lambda c: c.likes_count, 
            reverse=True
        )
        
        # Show top 10
        top_10 = sorted_comments[:10]
        
        print(f"\n=== Top 10 Comments by Likes ===")
        for i, comment in enumerate(top_10):
            print(f"\n{i+1}. {comment.likes_count} likes - @{comment.author}")
            print(f"   Text: {comment.text[:100]}{'...' if len(comment.text) > 100 else ''}")
            print(f"   Type: {'Reply' if comment.reply else 'Top-level'}")
            print(f"   Time: {comment.time}")
        
        # Show the difference between YouTube's "popular" order vs like-count order
        print(f"\n=== Comparison: YouTube Popular vs Like Count ===")
        print("First 5 in YouTube's 'popular' order:")
        for i, comment in enumerate(response.comments[:5]):
            print(f"  {i+1}. {comment.likes_count} likes - {comment.text[:50]}...")
            
        print("\nTop 5 by actual like count:")
        for i, comment in enumerate(top_10[:5]):
            print(f"  {i+1}. {comment.likes_count} likes - {comment.text[:50]}...")
        
        # Show some stats
        all_likes = [c.likes_count for c in response.comments]
        print(f"\n=== Like Distribution ===")
        print(f"Highest likes: {max(all_likes)}")
        print(f"Average likes: {sum(all_likes) / len(all_likes):.1f}")
        print(f"Comments with 0 likes: {sum(1 for likes in all_likes if likes == 0)}")
        print(f"Comments with 100+ likes: {sum(1 for likes in all_likes if likes >= 100)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_top_by_likes())
#!/usr/bin/env python3
"""Test the new auto-sizing get_top_comments_by_likes function."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

async def test_new_auto_sizing():
    """Test the new auto-sizing logic manually."""
    downloader = YouTubeCommentDownloader()
    
    # Simulate the new auto-sizing logic
    video_id = 'KBvtvnYmi5w'
    top_count = 10
    sample_size = None  # Auto-size
    
    print("=== Testing New Auto-Sizing Logic ===")
    print(f"Video: {video_id}")
    print(f"Top count: {top_count}")
    
    # Auto-sizing logic
    if sample_size is None:
        sample_size = 10000  # Always try for maximum
        estimated_total = "auto-sized (max download)"
        auto_sized = True
        print(f"Auto-sized sample_size to: {sample_size}")
    else:
        estimated_total = "manual override"
        auto_sized = False
    
    # Download comments
    print(f"\nDownloading {sample_size} comments...")
    request = CommentRequest(
        video_id=video_id,
        limit=sample_size,
        sort=0  # Popular sort
    )
    
    try:
        response = await downloader.download_comments(request)
        print(f"Successfully downloaded: {response.total_comments} comments")
        
        # Sort by likes
        sorted_comments = sorted(
            response.comments, 
            key=lambda c: c.likes_count, 
            reverse=True
        )
        
        # Take top N
        top_comments = sorted_comments[:top_count]
        
        # Create result similar to the MCP tool
        result = {
            "video_id": response.video_id,
            "top_count_requested": top_count,
            "sample_size": response.total_comments,
            "auto_sizing_info": {
                "auto_sized": auto_sized,
                "estimated_total_comments": estimated_total,
                "calculated_sample_size": sample_size,
                "coverage_percentage": "N/A"
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
        
        # Display results
        print(f"\n=== RESULTS ===")
        print(f"Auto-sized: {result['auto_sizing_info']['auto_sized']}")
        print(f"Downloaded: {result['sample_size']} comments")  
        print(f"Like range: {result['like_range']['highest']} - {result['like_range']['lowest']}")
        
        print(f"\nTop {top_count} Comments by Likes:")
        for comment in result['top_comments']:
            print(f"{comment['rank']:2d}. {comment['likes']:4d} likes - {comment['text'][:70]}...")
            
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_new_auto_sizing())
#!/usr/bin/env python3
"""Test script for the new get_video_info tool."""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import MetadataRequest

async def test_video_info():
    """Test the get_video_info functionality with various video types."""
    
    # Check if API key is available
    if not os.getenv('YOUTUBE_API_KEY'):
        print("❌ YOUTUBE_API_KEY not found in environment variables")
        print("Please set your YouTube Data API key in the .env file")
        return
    
    print("🚀 Testing get_video_info functionality...\n")
    
    # Test cases with different video types
    test_cases = [
        {
            "name": "Rick Astley - Never Gonna Give You Up (Viral Video)",
            "video_id": "dQw4w9WgXcQ",
            "description": "Popular viral video with millions of comments"
        },
        {
            "name": "Recent Popular Video",
            "video_id": "jNQXAC9IVRw", 
            "description": "Me at the zoo - First YouTube video"
        },
        {
            "name": "Invalid Video ID",
            "video_id": "invalid_id_123",
            "description": "Test error handling"
        }
    ]
    
    client = YouTubeAPIClient()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Video ID: {test_case['video_id']}")
        print(f"Description: {test_case['description']}")
        print("-" * 50)
        
        try:
            request = MetadataRequest(video_id=test_case['video_id'])
            metadata = await client.get_video_info(request)
            
            print(f"✅ Success!")
            print(f"Title: {metadata.title}")
            print(f"Channel: {metadata.channel_title}")
            print(f"Views: {metadata.view_count:,}" if metadata.view_count else "Views: Not available")
            print(f"Likes: {metadata.like_count:,}" if metadata.like_count else "Likes: Not available")
            print(f"Comments: {metadata.comment_count:,}" if metadata.comment_count else "Comments: Not available")
            print(f"Duration: {metadata.duration}")
            print(f"Published: {metadata.published_at}")
            
            if metadata.description:
                preview = metadata.description[:100] + "..." if len(metadata.description) > 100 else metadata.description
                print(f"Description: {preview}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n" + "="*60 + "\n")
    
    # Test quota status
    print("📊 Testing quota status...")
    try:
        quota_status = client.get_quota_status()
        print(f"✅ Quota Status:")
        print(f"Daily usage: {quota_status['daily_usage']}/{quota_status['daily_limit']}")
        print(f"Requests made: {quota_status['requests_made']}")
        print(f"Remaining: {quota_status['remaining']}")
    except Exception as e:
        print(f"❌ Quota check error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_video_info())
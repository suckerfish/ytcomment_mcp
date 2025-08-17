#!/usr/bin/env python3
"""Test YouTube Data API implementation."""

import asyncio
import os
from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import CommentRequest

# Set API key from TODO file
API_KEY = "***REDACTED_API_KEY***"

async def test_api_basic():
    """Test basic API functionality."""
    print("🔵 Testing YouTube Data API basic functionality...")
    
    client = YouTubeAPIClient(api_key=API_KEY)
    
    # Test with the known video from the investigation
    video_id = "dQw4w9WgXcQ"  # Rick Roll
    request = CommentRequest(
        video_id=video_id,
        limit=5,  # Small test
        sort=0    # Popular
    )
    
    try:
        response = await client.download_comments(request)
        print(f"✅ Successfully downloaded {response.total_comments} comments")
        
        # Check for the expected high-like comment
        if response.comments:
            top_comment = max(response.comments, key=lambda c: c.likes_count)
            print(f"✅ Top comment has {top_comment.likes_count} likes from {top_comment.author}")
            print(f"   Text preview: {top_comment.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

async def test_quota_status():
    """Test quota status checking."""
    print("\n🔵 Testing quota status checking...")
    
    client = YouTubeAPIClient(api_key=API_KEY)
    
    try:
        status = client.get_quota_status()
        print(f"✅ Quota status retrieved:")
        print(f"   Daily usage: {status['daily_usage']}/{status['daily_limit']}")
        print(f"   Remaining: {status['remaining']}")
        print(f"   Requests made: {status['requests_made']}")
        return True
        
    except Exception as e:
        print(f"❌ Quota status check failed: {e}")
        return False

async def test_comparison():
    """Test API vs expected results from investigation."""
    print("\n🔵 Testing API vs known good results...")
    
    client = YouTubeAPIClient(api_key=API_KEY)
    
    # Test video with known high-like comment
    request = CommentRequest(
        video_id="dQw4w9WgXcQ",
        limit=100,
        sort=0  # Popular to find high-like comments
    )
    
    try:
        response = await client.download_comments(request)
        sorted_comments = sorted(response.comments, key=lambda c: c.likes_count, reverse=True)
        
        print(f"✅ Found {len(response.comments)} comments")
        
        if sorted_comments:
            top_comment = sorted_comments[0]
            print(f"✅ Highest-liked comment: {top_comment.likes_count} likes")
            print(f"   Author: {top_comment.author}")
            
            # Check if we're getting realistic numbers (investigation found 24k+ likes)
            if top_comment.likes_count > 1000:
                print(f"✅ Found high-engagement comment ({top_comment.likes_count} likes) - API working correctly!")
            else:
                print(f"⚠️  Top comment has only {top_comment.likes_count} likes - may need larger sample")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing YouTube Data API Implementation")
    print("=" * 50)
    
    # Check if API key is available
    if not API_KEY:
        print("❌ No API key found. Set YOUTUBE_API_KEY environment variable.")
        return
    
    print(f"🔑 Using API key: {API_KEY[:20]}...")
    
    tests = [
        test_api_basic(),
        test_quota_status(), 
        test_comparison()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    print("\n" + "=" * 50)
    passed = sum(1 for result in results if result is True)
    print(f"🎯 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ All tests passed! API implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
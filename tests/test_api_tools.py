#!/usr/bin/env python3
"""Test the new API-based MCP tools."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set API key
API_KEY = "***REDACTED_API_KEY***"
os.environ['YOUTUBE_API_KEY'] = API_KEY

# Import the MCP server and tools
from src.server import (
    download_youtube_comments_api,
    get_comment_stats_api,
    search_comments_api,
    get_top_comments_by_likes_api,
    get_youtube_api_quota_status
)

async def test_download_api():
    """Test the download_youtube_comments_api tool."""
    print("🔵 Testing download_youtube_comments_api...")
    
    try:
        result = await download_youtube_comments_api(
            video_id="dQw4w9WgXcQ",
            limit=10,
            sort=0
        )
        
        print(f"✅ Downloaded {result['total_comments']} comments")
        print(f"   API quota remaining: {result['api_metadata']['quota_remaining']}")
        print(f"   Data source: {result['api_metadata']['data_source']}")
        
        if result['comments']:
            top_comment = max(result['comments'], key=lambda c: int(c['votes']))
            print(f"   Top comment: {int(top_comment['votes'])} likes")
        
        return True
        
    except Exception as e:
        print(f"❌ download_youtube_comments_api failed: {e}")
        return False

async def test_stats_api():
    """Test the get_comment_stats_api tool.""" 
    print("\n🔵 Testing get_comment_stats_api...")
    
    try:
        result = await get_comment_stats_api(
            video_id="dQw4w9WgXcQ",
            limit=50,
            sort=0
        )
        
        stats = result['stats']
        print(f"✅ Stats generated for {stats['total_comments']} comments")
        print(f"   Average likes: {stats['average_likes']:.1f}")
        print(f"   Max likes: {stats['max_likes']}")
        print(f"   Sample comments: {len(result['sample_comments'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ get_comment_stats_api failed: {e}")
        return False

async def test_search_api():
    """Test the search_comments_api tool."""
    print("\n🔵 Testing search_comments_api...")
    
    try:
        result = await search_comments_api(
            video_id="dQw4w9WgXcQ",
            search_term="rick",
            limit=100,
            sort=0
        )
        
        print(f"✅ Searched {result['total_comments_searched']} comments")
        print(f"   Found {result['matching_comments_count']} matches ({result['match_percentage']}%)")
        
        if result['matching_comments']:
            print(f"   Example match: '{result['matching_comments'][0]['text'][:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"❌ search_comments_api failed: {e}")
        return False

async def test_top_comments_api():
    """Test the get_top_comments_by_likes_api tool."""
    print("\n🔵 Testing get_top_comments_by_likes_api...")
    
    try:
        result = await get_top_comments_by_likes_api(
            video_id="dQw4w9WgXcQ",
            top_count=5,
            sample_size=200
        )
        
        print(f"✅ Found top {len(result['top_comments'])} comments")
        print(f"   Like range: {result['like_range']['highest']} - {result['like_range']['lowest']}")
        print(f"   Data accuracy: {result['api_metadata']['data_accuracy']}")
        
        for i, comment in enumerate(result['top_comments'][:3], 1):
            print(f"   #{i}: {comment['likes']} likes - {comment['text'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ get_top_comments_by_likes_api failed: {e}")
        return False

async def test_quota_status():
    """Test the get_youtube_api_quota_status tool."""
    print("\n🔵 Testing get_youtube_api_quota_status...")
    
    try:
        result = await get_youtube_api_quota_status()
        
        usage = result['usage_analysis']
        print(f"✅ Quota status retrieved")
        print(f"   Usage: {usage['percentage_used']}%")
        print(f"   Remaining requests: {usage['requests_remaining_estimate']}")
        print(f"   Comments available: {usage['comments_remaining_estimate']}")
        print(f"   Near limit: {usage['is_near_limit']}")
        
        return True
        
    except Exception as e:
        print(f"❌ get_youtube_api_quota_status failed: {e}")
        return False

async def main():
    """Run all MCP tool tests."""
    print("🚀 Testing YouTube Data API MCP Tools")
    print("=" * 50)
    
    tests = [
        test_download_api(),
        test_stats_api(),
        test_search_api(), 
        test_top_comments_api(),
        test_quota_status()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    print("\n" + "=" * 50)
    passed = sum(1 for result in results if result is True)
    print(f"🎯 Test Results: {passed}/{len(tests)} MCP tools passed")
    
    if passed == len(tests):
        print("✅ All MCP tools working correctly! API migration successful.")
    else:
        print("⚠️  Some tools failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
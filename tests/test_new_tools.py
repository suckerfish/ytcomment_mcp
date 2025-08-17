#!/usr/bin/env python3
"""Test the new channel and video tools individually."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import ChannelSearchRequest, VideoListRequest

async def test_find_channel():
    """Test the find_channel functionality."""
    print("🔍 Testing find_channel")
    print("=" * 40)
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found")
        return False
    
    client = YouTubeAPIClient(api_key)
    
    try:
        # Test various channel searches
        test_queries = [
            "mkbhd",
            "veritasium", 
            "linus tech tips"
        ]
        
        for query in test_queries:
            print(f"\n🔎 Searching for: '{query}'")
            request = ChannelSearchRequest(channel_name=query, max_results=3)
            response = await client.search_channels(request)
            
            print(f"✅ Found {response.total_results} channels:")
            for channel in response.channels:
                print(f"   • {channel.title}")
                print(f"     ID: {channel.channel_id}")
                print(f"     Subscribers: {channel.subscriber_count:,}" if channel.subscriber_count else "     Subscribers: Unknown")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing find_channel: {str(e)}")
        return False

async def test_get_channel_videos():
    """Test the get_channel_videos functionality."""
    print("\n📺 Testing get_channel_videos")
    print("=" * 40)
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found")
        return False
    
    client = YouTubeAPIClient(api_key)
    
    try:
        # Use MKBHD channel ID
        channel_id = "UCBJycsmduvYEL83R_U4JriQ"
        
        # Test 1: Get recent videos without filter
        print(f"\n📋 Test 1: Recent videos from channel {channel_id}")
        request = VideoListRequest(channel_id=channel_id, limit=5)
        response = await client.get_channel_videos(request)
        
        print(f"✅ Found {response.total_videos_found} videos:")
        for video in response.videos:
            print(f"   • {video.title}")
            print(f"     ID: {video.video_id}")
            print(f"     Published: {video.published_at}")
            print(f"     Views: {video.view_count:,}" if video.view_count else "     Views: Unknown")
        
        # Test 2: Get videos with title filter  
        print(f"\n🎯 Test 2: Videos with 'review' in title")
        request = VideoListRequest(
            channel_id=channel_id, 
            title_filter="review",
            limit=3
        )
        response = await client.get_channel_videos(request)
        
        print(f"✅ Found {response.filtered_videos_count} videos matching filter:")
        for video in response.videos:
            print(f"   • {video.title}")
            print(f"     ID: {video.video_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing get_channel_videos: {str(e)}")
        return False

async def test_quota_costs():
    """Test and display quota costs."""
    print("\n💰 Testing quota costs")
    print("=" * 40)
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found")
        return False
    
    client = YouTubeAPIClient(api_key)
    
    try:
        initial_quota = client.get_quota_status()
        print(f"🏁 Starting quota: {initial_quota['daily_usage']}/{initial_quota['daily_limit']}")
        
        # Test find_channel cost
        print(f"\n💸 Testing find_channel quota cost...")
        request = ChannelSearchRequest(channel_name="test", max_results=1)
        await client.search_channels(request)
        
        after_search = client.get_quota_status()
        search_cost = after_search['daily_usage'] - initial_quota['daily_usage']
        print(f"✅ find_channel cost: {search_cost} units")
        
        # Test get_channel_videos cost
        print(f"\n💸 Testing get_channel_videos quota cost...")
        video_request = VideoListRequest(
            channel_id="UCBJycsmduvYEL83R_U4JriQ",
            limit=1
        )
        await client.get_channel_videos(video_request)
        
        after_videos = client.get_quota_status()
        video_cost = after_videos['daily_usage'] - after_search['daily_usage']
        print(f"✅ get_channel_videos cost: {video_cost} units")
        
        total_workflow_cost = search_cost + video_cost + 5  # +5 for comment search (5 videos)
        print(f"\n📊 Complete workflow cost estimate: {total_workflow_cost} units")
        print(f"📈 Daily workflows possible: ~{10000 // total_workflow_cost}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing quota costs: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("🧪 Testing New YouTube Channel & Video Tools")
    print("=" * 60)
    
    # Check API key first
    if not os.getenv('YOUTUBE_API_KEY'):
        print("❌ No YOUTUBE_API_KEY found!")
        print("Set your API key in .env file or environment variables")
        return
    
    # Run tests
    tests = [
        test_find_channel(),
        test_get_channel_videos(), 
        test_quota_costs()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r is True)
    total_tests = len(results)
    
    print(f"✅ Passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! New tools are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Test {i+1} failed: {result}")

if __name__ == "__main__":
    asyncio.run(main())
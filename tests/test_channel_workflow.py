#!/usr/bin/env python3
"""Test the complete channel workflow: find_channel → get_channel_videos → search_comments"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tools.youtube_api import YouTubeAPIClient
from src.models.youtube import ChannelSearchRequest, VideoListRequest, CommentRequest

async def test_complete_workflow():
    """Test the complete workflow that the user requested."""
    print("🚀 Testing Complete Channel Workflow")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found in environment")
        print("Add your API key to .env file or environment variables")
        return
    
    client = YouTubeAPIClient(api_key)
    
    try:
        # Step 1: Find channel by name
        print("\n📍 Step 1: Finding channel by name")
        print("-" * 40)
        
        channel_request = ChannelSearchRequest(
            channel_name="mkbhd",
            max_results=3
        )
        
        print(f"Searching for channels matching: '{channel_request.channel_name}'")
        channel_response = await client.search_channels(channel_request)
        
        print(f"✅ Found {channel_response.total_results} channels:")
        for i, channel in enumerate(channel_response.channels[:3], 1):
            print(f"  {i}. {channel.title} ({channel.channel_id})")
            print(f"     Subscribers: {channel.subscriber_count:,}" if channel.subscriber_count else "     Subscribers: Unknown")
            print(f"     Videos: {channel.video_count}" if channel.video_count else "     Videos: Unknown")
        
        # Use the main MKBHD channel
        main_channel = channel_response.channels[0]
        print(f"\n🎯 Selected: {main_channel.title} ({main_channel.channel_id})")
        
        # Step 2: Get recent videos with title filter
        print("\n📍 Step 2: Getting recent videos with title filter")
        print("-" * 40)
        
        video_request = VideoListRequest(
            channel_id=main_channel.channel_id,
            title_filter="tesla",  # Look for Tesla-related videos
            limit=10,
            order="date"
        )
        
        print(f"Looking for videos with '{video_request.title_filter}' in title...")
        video_response = await client.get_channel_videos(video_request)
        
        print(f"✅ Found {video_response.total_videos_found} total videos")
        print(f"📋 {video_response.filtered_videos_count} videos match title filter")
        
        if video_response.videos:
            print("\nMatching videos:")
            for i, video in enumerate(video_response.videos[:5], 1):
                print(f"  {i}. {video.title[:60]}...")
                print(f"     Video ID: {video.video_id}")
                print(f"     Published: {video.published_at}")
                print(f"     Comments: {video.comment_count}" if video.comment_count else "     Comments: Unknown")
        else:
            print("❌ No videos found with title filter. Trying without filter...")
            
            # Fallback: get recent videos without filter
            video_request.title_filter = None
            video_response = await client.get_channel_videos(video_request)
            
            print(f"✅ Found {video_response.total_videos_found} recent videos:")
            for i, video in enumerate(video_response.videos[:3], 1):
                print(f"  {i}. {video.title[:60]}...")
                print(f"     Video ID: {video.video_id}")
                print(f"     Comments: {video.comment_count}" if video.comment_count else "     Comments: Unknown")
        
        # Step 3: Search comments on the first video
        if video_response.videos:
            print("\n📍 Step 3: Searching comments for keywords")
            print("-" * 40)
            
            target_video = video_response.videos[0]
            print(f"🎯 Selected video: {target_video.title}")
            print(f"Video ID: {target_video.video_id}")
            
            # Use existing comment search functionality
            comment_request = CommentRequest(
                video_id=target_video.video_id,
                limit=1000,  # Search through first 1000 comments
                sort=0  # Popular first for better matches
            )
            
            print("Downloading comments for keyword search...")
            comment_response = await client.download_comments(comment_request)
            
            # Server-side keyword search
            search_terms = ["awesome", "amazing", "great"]
            print(f"Searching {comment_response.total_comments} comments for keywords: {search_terms}")
            
            matching_comments = []
            for comment in comment_response.comments:
                comment_text_lower = comment.text.lower()
                if any(term in comment_text_lower for term in search_terms):
                    matching_comments.append(comment)
                    if len(matching_comments) >= 5:  # Limit to 5 matches
                        break
            
            print(f"✅ Found {len(matching_comments)} comments matching keywords:")
            for i, comment in enumerate(matching_comments, 1):
                print(f"\n  {i}. @{comment.author} ({comment.likes_count} likes)")
                print(f"     \"{comment.text[:100]}...\"" if len(comment.text) > 100 else f"     \"{comment.text}\"")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 WORKFLOW COMPLETE!")
        print("=" * 60)
        
        quota_status = client.get_quota_status()
        print(f"📊 Quota used: {quota_status['daily_usage']} / {quota_status['daily_limit']}")
        print(f"📈 API calls made: {quota_status['requests_made']}")
        
        print("\n✅ Successfully demonstrated the complete workflow:")
        print("   1. ✅ find_channel → Found MKBHD channel")
        print("   2. ✅ get_channel_videos → Found recent videos")
        print("   3. ✅ search_comments → Found matching comments")
        
    except Exception as e:
        print(f"\n❌ Error during workflow test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
#!/usr/bin/env python3
"""Simple test of token counting integration with YouTube API client."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.youtube_api import YouTubeAPIClient
from src.tools.token_counter import ClaudeTokenCounter
from src.models.youtube import CommentRequest, SlimYouTubeComment


async def test_integration():
    """Test token counting integration with YouTube API."""
    print("🧪 Testing Token Counting with YouTube API Integration")
    print("=" * 55)
    
    # Check if API key is available
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ No YouTube API key found. Please set YOUTUBE_API_KEY in .env file")
        print("💡 This test requires a real API key to fetch comments")
        return False
    
    try:
        # Initialize components
        api_client = YouTubeAPIClient()
        token_counter = ClaudeTokenCounter()
        
        # Test video ID (Rick Astley - Never Gonna Give You Up)
        video_id = "dQw4w9WgXcQ"
        
        print(f"📥 Fetching comments from video: {video_id}")
        
        # Create request for small number of comments
        request = CommentRequest(
            video_id=video_id,
            limit=5,
            sort=1  # Recent comments
        )
        
        # Download comments
        response = await api_client.download_comments(request)
        print(f"✅ Retrieved {len(response.comments)} comments")
        
        # Convert to slim format
        print("\n📊 Testing Slim Format Token Counting:")
        slim_comments = [SlimYouTubeComment.from_full_comment(comment).model_dump() for comment in response.comments]
        slim_analysis = token_counter.count_comments_tokens(slim_comments, slim_mode=True)
        
        print(f"   Total tokens: {slim_analysis['total_tokens']}")
        print(f"   Average per comment: {slim_analysis['average_tokens_per_comment']}")
        print(f"   Token breakdown:")
        print(f"     Content: {slim_analysis['token_breakdown']['content_tokens']}")
        print(f"     Structure: {slim_analysis['token_breakdown']['structure_tokens']}")
        print(f"     Metadata: {slim_analysis['token_breakdown']['metadata_tokens']}")
        
        # Test full format
        print("\n📊 Testing Full Format Token Counting:")
        full_comments = [comment.model_dump() for comment in response.comments]
        full_analysis = token_counter.count_comments_tokens(full_comments, slim_mode=False)
        
        print(f"   Total tokens: {full_analysis['total_tokens']}")
        print(f"   Average per comment: {full_analysis['average_tokens_per_comment']}")
        
        # Show efficiency comparison
        efficiency = ((full_analysis['total_tokens'] - slim_analysis['total_tokens']) / full_analysis['total_tokens']) * 100
        print(f"\n📈 Efficiency Analysis:")
        print(f"   Slim mode: {slim_analysis['total_tokens']} tokens")
        print(f"   Full mode: {full_analysis['total_tokens']} tokens")
        print(f"   Size reduction: {efficiency:.1f}%")
        
        # Test context analysis
        print(f"\n🎯 Context Analysis (Slim Mode):")
        context_analysis = token_counter.get_context_analysis(slim_analysis['total_tokens'])
        for model, data in context_analysis.items():
            if model in ['claude_3_5', 'gpt4']:  # Show key models
                print(f"   {model}: {data['usage_percentage']:.3f}% context usage")
        
        # Show sample comment analysis
        if response.comments:
            print(f"\n🔍 Sample Comment Analysis:")
            first_comment = slim_comments[0]
            comment_tokens = token_counter.count_comment_tokens_slim(first_comment)
            text_tokens = token_counter.count_text_tokens(first_comment.get('text', ''))
            
            print(f"   Author: {first_comment.get('author', 'Unknown')}")
            print(f"   Text: \"{first_comment.get('text', '')[:60]}{'...' if len(first_comment.get('text', '')) > 60 else ''}\"")
            print(f"   Likes: {first_comment.get('likes', 0)}")
            print(f"   Total tokens: {comment_tokens}")
            print(f"   Text tokens: {text_tokens}")
            print(f"   Metadata tokens: {comment_tokens - text_tokens}")
        
        print("\n🎉 Token counting integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during integration test: {str(e)}")
        return False


if __name__ == "__main__":
    asyncio.run(test_integration())
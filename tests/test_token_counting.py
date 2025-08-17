#!/usr/bin/env python3
"""Test token counting functionality with real comment data."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.token_counter import ClaudeTokenCounter
from src.models.youtube import SlimYouTubeComment, YouTubeComment


async def test_token_counting():
    """Test token counting with sample comments."""
    print("🧪 Testing Token Counting Functionality")
    print("=" * 50)
    
    # Initialize token counter
    counter = ClaudeTokenCounter()
    
    # Test with sample comments
    sample_comments = [
        {
            "author": "TechReviewer123",
            "text": "This is an amazing video! The quality is fantastic and I learned so much. Thanks for sharing! 🔥✨",
            "likes": 1245,
            "time": "2024-01-15T10:30:00Z",
            "is_hearted": True
        },
        {
            "author": "User456",
            "text": "Short comment",
            "likes": 5,
            "time": "2024-01-15T11:00:00Z", 
            "is_hearted": False
        },
        {
            "author": "DevExpert",
            "text": "Here's a technical comment with code examples: console.log('Hello World'); and some URLs like https://github.com/example/repo - very useful! 💻🚀",
            "likes": 892,
            "time": "2024-01-15T09:45:00Z",
            "is_hearted": True
        }
    ]
    
    # Test slim mode counting
    print("📊 Testing Slim Mode Token Counting:")
    slim_analysis = counter.count_comments_tokens(sample_comments, slim_mode=True)
    print(f"  Total tokens: {slim_analysis['total_tokens']}")
    print(f"  Average per comment: {slim_analysis['average_tokens_per_comment']}")
    print(f"  Content tokens: {slim_analysis['token_breakdown']['content_tokens']}")
    print(f"  Structure tokens: {slim_analysis['token_breakdown']['structure_tokens']}")
    print(f"  Metadata tokens: {slim_analysis['token_breakdown']['metadata_tokens']}")
    
    # Test individual comment token counting
    print("\n🔍 Individual Comment Analysis:")
    for i, comment in enumerate(sample_comments, 1):
        tokens = counter.count_comment_tokens_slim(comment)
        text_tokens = counter.count_text_tokens(comment['text'])
        print(f"  Comment {i}: {tokens} total tokens ({text_tokens} from text)")
        print(f"    Text: \"{comment['text'][:50]}{'...' if len(comment['text']) > 50 else ''}\"")
    
    # Test full mode for comparison
    print("\n📊 Testing Full Mode Token Counting:")
    # Add some full format fields
    full_comments = []
    for comment in sample_comments:
        full_comment = comment.copy()
        full_comment.update({
            "cid": f"UgwS{'x' * 22}AaABAg",
            "channel": f"UC{'y' * 22}",
            "photo": "https://yt3.ggpht.com/ytc/example_profile_pic_url_here.jpg",
            "replies": "3",
            "time_parsed": 1705312200
        })
        full_comments.append(full_comment)
    
    full_analysis = counter.count_comments_tokens(full_comments, slim_mode=False)
    print(f"  Total tokens: {full_analysis['total_tokens']}")
    print(f"  Average per comment: {full_analysis['average_tokens_per_comment']}")
    print(f"  Content tokens: {full_analysis['token_breakdown']['content_tokens']}")
    print(f"  Structure tokens: {full_analysis['token_breakdown']['structure_tokens']}")
    print(f"  Metadata tokens: {full_analysis['token_breakdown']['metadata_tokens']}")
    
    # Test context analysis
    print("\n🎯 Context Analysis for Slim Mode:")
    context_analysis = counter.get_context_analysis(slim_analysis['total_tokens'])
    for model, data in context_analysis.items():
        print(f"  {model}: {data['usage_percentage']:.2f}% context usage")
        print(f"    Fits in context: {data['fits_in_context']}")
    
    # Compare efficiency
    print("\n📈 Efficiency Comparison:")
    slim_tokens = slim_analysis['total_tokens']
    full_tokens = full_analysis['total_tokens']
    reduction = ((full_tokens - slim_tokens) / full_tokens) * 100
    print(f"  Slim mode: {slim_tokens} tokens")
    print(f"  Full mode: {full_tokens} tokens")
    print(f"  Reduction: {reduction:.1f}%")
    
    print("\n✅ Token counting tests completed!")


if __name__ == "__main__":
    asyncio.run(test_token_counting())
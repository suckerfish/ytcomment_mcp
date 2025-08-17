#!/usr/bin/env python3
"""Test to estimate token count for 100 YouTube comments."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

def estimate_tokens(text):
    """Rough token estimation: ~4 chars per token for English text."""
    return len(text) / 4

async def test_token_estimation():
    """Test token estimation for 100 comments with both sorting methods."""
    
    downloader = YouTubeCommentDownloader()
    
    # Test both sorting methods
    test_cases = [
        ("dQw4w9WgXcQ", "Popular/Top", 0),
        ("dQw4w9WgXcQ", "Recent/Latest", 1),
    ]
    
    for video_id, sort_name, sort_value in test_cases:
        print(f"\n=== {sort_name} Comments ===")
        
        request = CommentRequest(
            video_id=video_id,
            limit=100,
            sort=sort_value
        )
        
        try:
            response = await downloader.download_comments(request)
            
            # Calculate text statistics
            all_text = ""
            comment_texts = []
            
            for comment in response.comments:
                comment_text = f"Author: {comment.author}\nText: {comment.text}\nLikes: {comment.votes}\nTime: {comment.time}\n---\n"
                all_text += comment_text
                comment_texts.append(comment.text)
            
            # Token estimation
            total_chars = len(all_text)
            estimated_tokens = estimate_tokens(all_text)
            
            # Text length analysis
            text_lengths = [len(text) for text in comment_texts]
            avg_text_length = sum(text_lengths) / len(text_lengths)
            max_text_length = max(text_lengths) if text_lengths else 0
            min_text_length = min(text_lengths) if text_lengths else 0
            
            print(f"Comments downloaded: {response.total_comments}")
            print(f"Total characters: {total_chars:,}")
            print(f"Estimated tokens: {estimated_tokens:,.0f}")
            print(f"Average comment length: {avg_text_length:.1f} chars")
            print(f"Longest comment: {max_text_length} chars")
            print(f"Shortest comment: {min_text_length} chars")
            
            # Show sample comments
            print(f"\nSample comments:")
            for i, comment in enumerate(response.comments[:3]):
                tokens_est = estimate_tokens(comment.text)
                print(f"{i+1}. [{tokens_est:.0f} tokens] {comment.author}: {comment.text[:80]}{'...' if len(comment.text) > 80 else ''}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_token_estimation())
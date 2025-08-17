#!/usr/bin/env python3
"""Test to understand how replies and nesting work in YouTube comments."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.youtube_comments import YouTubeCommentDownloader
from src.models.youtube import CommentRequest

async def test_reply_structure():
    """Test reply structure and nesting in YouTube comments."""
    
    downloader = YouTubeCommentDownloader()
    
    # Test with a video that likely has reply threads
    request = CommentRequest(
        video_id="dQw4w9WgXcQ",  # Rick Roll - should have reply conversations
        limit=200,  # Larger sample to find replies
        sort=0  # Popular comments more likely to have replies
    )
    
    print("Testing reply structure...")
    print(f"Video ID: {request.video_id}")
    print(f"Limit: {request.limit}, Sort: Popular")
    
    try:
        response = await downloader.download_comments(request)
        
        # Analyze reply structure
        top_level_comments = []
        replies = []
        comments_with_replies = []
        
        for comment in response.comments:
            if comment.reply:  # This is a reply
                replies.append(comment)
            else:  # Top-level comment
                top_level_comments.append(comment)
                if comment.replies_count > 0:
                    comments_with_replies.append(comment)
        
        print(f"\n=== Reply Analysis ===")
        print(f"Total comments downloaded: {response.total_comments}")
        print(f"Top-level comments: {len(top_level_comments)}")
        print(f"Reply comments: {len(replies)}")
        print(f"Top-level comments with replies: {len(comments_with_replies)}")
        
        # Show structure of comments with replies
        if comments_with_replies:
            print(f"\n=== Comments with Replies ===")
            for i, comment in enumerate(comments_with_replies[:5]):  # Show first 5
                print(f"\n{i+1}. Top-level comment:")
                print(f"   Author: {comment.author}")
                print(f"   Text: {comment.text[:80]}{'...' if len(comment.text) > 80 else ''}")
                print(f"   Likes: {comment.likes_count}")
                print(f"   Reply count: {comment.replies_count}")
        
        # Show actual reply examples
        if replies:
            print(f"\n=== Reply Examples ===")
            for i, reply in enumerate(replies[:5]):  # Show first 5 replies
                print(f"\n{i+1}. Reply:")
                print(f"   Author: {reply.author}")
                print(f"   Text: {reply.text[:80]}{'...' if len(reply.text) > 80 else ''}")
                print(f"   Likes: {reply.likes_count}")
                print(f"   Is reply: {reply.reply}")
                # Note: parent comment ID not available in current structure
        
        # Analyze reply patterns
        if replies:
            reply_lengths = [len(reply.text) for reply in replies]
            avg_reply_length = sum(reply_lengths) / len(reply_lengths)
            
            top_level_lengths = [len(comment.text) for comment in top_level_comments]
            avg_top_level_length = sum(top_level_lengths) / len(top_level_lengths) if top_level_lengths else 0
            
            print(f"\n=== Reply vs Top-Level Comparison ===")
            print(f"Average reply length: {avg_reply_length:.1f} chars")
            print(f"Average top-level length: {avg_top_level_length:.1f} chars")
            print(f"Replies are {'shorter' if avg_reply_length < avg_top_level_length else 'longer'} on average")
        
        # Check if we can determine nesting levels
        print(f"\n=== Nesting Analysis ===")
        print("Note: The youtube-comment-downloader library downloads comments in a flat structure.")
        print("It doesn't preserve the hierarchical relationship between parent and child comments.")
        print("Each comment has a 'reply' boolean flag, but no parent comment ID.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_reply_structure())
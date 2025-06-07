#!/usr/bin/env python3
"""
Test script to analyze YouTube comment data structure and volume.
This helps with capacity planning for the MCP server.
"""

import json
import sys
import subprocess
import tempfile
import os
from collections import Counter
from datetime import datetime
import statistics

def download_comments(video_id, limit=100, sort=1):
    """Download comments for a YouTube video and return parsed data."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Run youtube-comment-downloader
        cmd = [
            'python', '-m', 'youtube_comment_downloader',
            '--youtubeid', video_id,
            '--output', tmp_path,
            '--limit', str(limit),
            '--sort', str(sort)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"Error downloading comments: {result.stderr}")
            return []
            
        # Read and parse the line-delimited JSON
        comments = []
        with open(tmp_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        comment = json.loads(line)
                        comments.append(comment)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error on line {line_num}: {e}")
                        
        return comments
        
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def analyze_comments(comments, video_id):
    """Analyze the structure and volume of comment data."""
    if not comments:
        print(f"No comments found for video {video_id}")
        return
        
    print(f"\n=== Analysis for Video ID: {video_id} ===")
    print(f"Total comments downloaded: {len(comments)}")
    
    # Analyze data structure
    print("\n--- Data Structure Analysis ---")
    all_keys = set()
    key_counts = Counter()
    
    for comment in comments:
        comment_keys = set(comment.keys())
        all_keys.update(comment_keys)
        for key in comment_keys:
            key_counts[key] += 1
    
    print(f"Unique fields found: {len(all_keys)}")
    print("Field frequency:")
    for key, count in key_counts.most_common():
        percentage = (count / len(comments)) * 100
        print(f"  {key}: {count}/{len(comments)} ({percentage:.1f}%)")
    
    # Sample comment structure
    print(f"\n--- Sample Comment Structure ---")
    if comments:
        sample = comments[0]
        print("First comment fields and types:")
        for key, value in sample.items():
            value_type = type(value).__name__
            if isinstance(value, str):
                length = len(value)
                print(f"  {key}: {value_type} (length: {length})")
            else:
                print(f"  {key}: {value_type} (value: {value})")
    
    # Analyze text lengths
    print(f"\n--- Text Analysis ---")
    text_lengths = [len(c.get('text', '')) for c in comments if c.get('text')]
    if text_lengths:
        print(f"Comment text lengths:")
        print(f"  Min: {min(text_lengths)} chars")
        print(f"  Max: {max(text_lengths)} chars")
        print(f"  Average: {statistics.mean(text_lengths):.1f} chars")
        print(f"  Median: {statistics.median(text_lengths):.1f} chars")
    
    # Analyze likes
    print(f"\n--- Engagement Analysis ---")
    likes = [c.get('likes', 0) for c in comments if isinstance(c.get('likes'), int)]
    if likes:
        print(f"Likes distribution:")
        print(f"  Min: {min(likes)}")
        print(f"  Max: {max(likes)}")
        print(f"  Average: {statistics.mean(likes):.1f}")
        print(f"  Median: {statistics.median(likes):.1f}")
    
    # Count replies vs top-level comments
    top_level = sum(1 for c in comments if not c.get('parent'))
    replies = len(comments) - top_level
    print(f"Comment types:")
    print(f"  Top-level comments: {top_level}")
    print(f"  Replies: {replies}")
    
    # Verified authors
    verified_count = sum(1 for c in comments if c.get('is_verified'))
    print(f"  Verified authors: {verified_count}")
    
    # Memory estimation
    print(f"\n--- Memory Usage Estimation ---")
    total_size = 0
    for comment in comments:
        # Rough estimation of memory usage
        comment_size = sys.getsizeof(comment)
        for key, value in comment.items():
            comment_size += sys.getsizeof(key) + sys.getsizeof(value)
        total_size += comment_size
    
    avg_size_per_comment = total_size / len(comments) if comments else 0
    print(f"Average memory per comment: {avg_size_per_comment:.0f} bytes")
    print(f"Total memory for {len(comments)} comments: {total_size / 1024:.1f} KB")
    print(f"Estimated memory for 1000 comments: {(avg_size_per_comment * 1000) / 1024:.1f} KB")
    print(f"Estimated memory for 10000 comments: {(avg_size_per_comment * 10000) / 1024 / 1024:.1f} MB")

def main():
    """Test with various YouTube videos to understand data patterns."""
    
    # Test videos with different characteristics
    test_videos = [
        # Popular tech video (likely many comments)
        ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),  # Classic with tons of comments
        ("jNQXAC9IVRw", "Me at the zoo"),  # First YouTube video (historical)
    ]
    
    print("YouTube Comment Data Analysis")
    print("=" * 50)
    
    for video_id, description in test_videos:
        print(f"\nTesting: {description}")
        try:
            # Download recent comments (sort=1) with limit
            comments = download_comments(video_id, limit=50, sort=1)
            analyze_comments(comments, video_id)
            
        except Exception as e:
            print(f"Error analyzing video {video_id}: {e}")
        
        print("\n" + "-" * 50)

if __name__ == "__main__":
    main()
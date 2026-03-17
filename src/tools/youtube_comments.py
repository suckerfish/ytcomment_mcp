"""YouTube comment statistics utilities for MCP server."""

import statistics as stats_mod
from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.youtube import CommentsResponse, CommentStats


class YouTubeCommentDownloader:
    """Comment statistics calculator.

    Historical note: this class previously contained a CLI-based comment
    download path that shelled out to ``youtube-comment-downloader``.  That
    was replaced by the YouTube Data API client in ``youtube_api.py``.
    Only the statistics helper remains.
    """

    def __init__(self, timeout: int = 90):
        self.timeout = timeout

    def calculate_stats(self, response: CommentsResponse) -> CommentStats:
        """Calculate statistics for downloaded comments."""
        if not response.comments:
            return CommentStats(
                total_comments=0,
                top_level_comments=0,
                replies=0,
                hearted_comments=0,
                average_text_length=0,
                max_text_length=0,
                min_text_length=0,
                total_likes=0,
                average_likes=0,
                max_likes=0,
                memory_usage_mb=0
            )

        text_lengths = [len(c.text) for c in response.comments]
        likes_counts = [c.likes_count for c in response.comments]

        return CommentStats(
            total_comments=response.total_comments,
            top_level_comments=len(response.top_level_comments),
            replies=len(response.replies),
            hearted_comments=sum(1 for c in response.comments if c.heart),
            average_text_length=stats_mod.mean(text_lengths),
            max_text_length=max(text_lengths),
            min_text_length=min(text_lengths),
            total_likes=sum(likes_counts),
            average_likes=stats_mod.mean(likes_counts),
            max_likes=max(likes_counts),
            memory_usage_mb=response.memory_usage_mb
        )

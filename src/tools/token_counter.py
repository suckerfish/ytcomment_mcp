"""Token counting utilities using Claude tokenization patterns as baseline."""

import re
from typing import List, Dict, Any


class ClaudeTokenCounter:
    """Token counter that estimates tokens using Claude's tokenization patterns."""
    
    def __init__(self):
        # Average tokens per character for different text types based on Claude patterns
        self.base_tokens_per_char = 0.25  # ~4 chars per token baseline
        
        # Adjustment factors for different content types
        self.content_multipliers = {
            'english_text': 1.0,      # Standard English text
            'usernames': 1.2,         # Usernames tend to be more token-dense
            'numbers': 0.8,           # Numbers are often single tokens
            'punctuation': 1.5,       # Punctuation can be separate tokens
            'emojis': 2.0,            # Emojis often use multiple tokens
            'special_chars': 1.3,     # Special characters vary
            'urls': 0.6,              # URLs tend to be efficient
            'timestamps': 0.9         # Timestamps are fairly efficient
        }
    
    def count_text_tokens(self, text: str) -> int:
        """Count tokens in text using Claude tokenization patterns."""
        if not text:
            return 0
        
        # Basic character count
        char_count = len(text)
        
        # Apply content-specific adjustments
        multiplier = 1.0
        
        # Check for high emoji density
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]', text))
        if emoji_count > 0:
            emoji_ratio = emoji_count / max(len(text.split()), 1)
            if emoji_ratio > 0.1:  # High emoji density
                multiplier *= self.content_multipliers['emojis']
        
        # Check for special characters
        special_char_count = len(re.findall(r'[^\w\s.,!?;:]', text))
        if special_char_count > char_count * 0.1:  # High special char density
            multiplier *= self.content_multipliers['special_chars']
        
        # Check for URLs
        url_count = len(re.findall(r'https?://\S+', text))
        if url_count > 0:
            # URLs are more token-efficient, reduce multiplier
            multiplier *= self.content_multipliers['urls']
        
        # Estimate tokens
        estimated_tokens = char_count * self.base_tokens_per_char * multiplier
        
        # Minimum of 1 token for non-empty text
        return max(1, round(estimated_tokens))
    
    def count_comment_tokens_slim(self, comment: Dict[str, Any]) -> int:
        """Count tokens for a slim format comment."""
        total_tokens = 0
        
        # Author field - usernames tend to be more token-dense
        if 'author' in comment and comment['author']:
            author_chars = len(str(comment['author']))
            total_tokens += round(author_chars * self.base_tokens_per_char * self.content_multipliers['usernames'])
        
        # Text field - main content
        if 'text' in comment and comment['text']:
            total_tokens += self.count_text_tokens(str(comment['text']))
        
        # Likes field - numbers are efficient
        if 'likes' in comment:
            likes_str = str(comment['likes'])
            total_tokens += round(len(likes_str) * self.base_tokens_per_char * self.content_multipliers['numbers'])
        
        # Time field - timestamps are fairly efficient
        if 'time' in comment and comment['time']:
            time_str = str(comment['time'])
            total_tokens += round(len(time_str) * self.base_tokens_per_char * self.content_multipliers['timestamps'])
        
        # Boolean fields - very small
        if 'is_hearted' in comment:
            total_tokens += 1  # Boolean values are typically 1 token
        
        # Add overhead for JSON structure (keys, brackets, commas)
        structure_overhead = 5  # Estimated overhead for JSON structure
        total_tokens += structure_overhead
        
        return max(1, total_tokens)
    
    def count_comment_tokens_full(self, comment: Dict[str, Any]) -> int:
        """Count tokens for a full format comment."""
        total_tokens = 0
        
        # All the slim fields
        total_tokens += self.count_comment_tokens_slim(comment)
        
        # Additional full format fields
        fields_to_count = ['cid', 'channel', 'photo', 'replies', 'time_parsed']
        
        for field in fields_to_count:
            if field in comment and comment[field]:
                value_str = str(comment[field])
                
                if field == 'photo':
                    # URLs are more token-efficient
                    total_tokens += round(len(value_str) * self.base_tokens_per_char * self.content_multipliers['urls'])
                elif field in ['replies', 'time_parsed']:
                    # Numbers are efficient
                    total_tokens += round(len(value_str) * self.base_tokens_per_char * self.content_multipliers['numbers'])
                else:
                    # Default text processing
                    total_tokens += self.count_text_tokens(value_str)
        
        # Additional overhead for more complex JSON structure
        additional_overhead = 8  # More fields = more structure
        total_tokens += additional_overhead
        
        return max(1, total_tokens)
    
    def count_comments_tokens(self, comments: List[Dict[str, Any]], slim_mode: bool = True) -> Dict[str, Any]:
        """Count tokens for a list of comments with detailed breakdown."""
        if not comments:
            return {
                'total_tokens': 0,
                'average_tokens_per_comment': 0,
                'token_breakdown': {
                    'content_tokens': 0,
                    'structure_tokens': 0,
                    'metadata_tokens': 0
                },
                'comments_analyzed': 0
            }
        
        total_tokens = 0
        content_tokens = 0
        structure_tokens = 0
        metadata_tokens = 0
        
        for comment in comments:
            if slim_mode:
                comment_tokens = self.count_comment_tokens_slim(comment)
            else:
                comment_tokens = self.count_comment_tokens_full(comment)
            
            total_tokens += comment_tokens
            
            # Break down token types for analysis
            if 'text' in comment and comment['text']:
                content_tokens += self.count_text_tokens(str(comment['text']))
            
            # Structure tokens (JSON overhead)
            structure_tokens += 5 if slim_mode else 8
            
            # Metadata tokens (everything else)
            metadata_tokens += comment_tokens - self.count_text_tokens(str(comment.get('text', ''))) - (5 if slim_mode else 8)
        
        return {
            'total_tokens': total_tokens,
            'average_tokens_per_comment': round(total_tokens / len(comments), 2),
            'token_breakdown': {
                'content_tokens': content_tokens,
                'structure_tokens': structure_tokens, 
                'metadata_tokens': max(0, metadata_tokens)
            },
            'comments_analyzed': len(comments),
            'claude_tokenization_baseline': True
        }
    
    def get_context_analysis(self, token_count: int) -> Dict[str, Any]:
        """Analyze token count in context of LLM limits."""
        context_sizes = {
            'claude_3': 200000,
            'claude_3_5': 200000,
            'gpt4': 128000,
            'gemini_pro': 2000000
        }
        
        analysis = {}
        for model, limit in context_sizes.items():
            percentage = (token_count / limit) * 100
            analysis[model] = {
                'context_limit': limit,
                'usage_percentage': round(percentage, 2),
                'tokens_remaining': max(0, limit - token_count),
                'fits_in_context': token_count <= limit
            }
        
        return analysis
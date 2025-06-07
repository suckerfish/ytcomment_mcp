# YouTube Comment Downloader MCP Server

A Model Context Protocol (MCP) server that provides AI systems with the ability to download and analyze YouTube video comments without requiring API keys.

## Features

- **4 specialized tools** for different comment analysis needs
- **No authentication required** - uses web scraping
- **Context-efficient** statistics tool to avoid token bloat
- **Built-in capacity planning** with memory and timeout limits
- **Engagement analysis** with actual like-count sorting

## MCP Client Configuration

Add this configuration block to your MCP client (e.g., Claude Desktop):

```json
"ytcomment-mcp": {
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/Users/chad.kunsman/Documents/PythonProject/ytcomment_mcp",
    "src/server.py"
  ]
}
```

## Available Tools

### 1. `download_youtube_comments`
Download raw comment data with full details.
- **Parameters**: `video_id`, `limit` (1-10000), `sort` (0=popular, 1=recent)
- **Returns**: Full comment dataset with all metadata
- **Use case**: When you need complete comment data for analysis

### 2. `get_comment_stats` 
Get statistical analysis without full comment data (context-efficient).
- **Parameters**: `video_id`, `limit`, `sort`  
- **Returns**: Statistics + 5 sample comments (~200 tokens vs ~25,000)
- **Use case**: Quick engagement insights without context bloat
- **Triggers**: "how engaged", "what's the engagement", "comment patterns"

### 3. `search_comments`
Search for specific terms within comments.
- **Parameters**: `video_id`, `search_term`, `limit`, `sort`
- **Returns**: Matching comments + search metadata
- **Use case**: Finding mentions, sentiment analysis, topic research
- **Triggers**: "find comments about", "search for", "mentions of"

### 4. `get_top_comments_by_likes`
Get most-liked comments sorted by actual like count (not YouTube's "popular").
- **Parameters**: `video_id`, `top_count` (1-100), `sample_size` (100-2000, default: 500)
- **Returns**: Top comments ranked by likes + engagement stats
- **Use case**: Finding viral comments that YouTube's algorithm might not surface first
- **Triggers**: "most popular", "most liked", "viral comments", "best comments"

## Quick Start

```bash
# Install dependencies
uv venv && source .venv/bin/activate
uv pip install -e .

# Test functionality
python test_server.py

# Run MCP server
python src/server.py
```

## Data Structure

Each comment contains 11 fields:
- `cid`, `text`, `time`, `time_parsed`, `author`, `channel`
- `votes` (likes), `replies`, `photo`, `heart`, `reply`

**Capacity**: ~1.8KB memory, ~25 tokens per comment

## Key Limitations & Performance

- **Flat structure**: No hierarchical reply threading
- **Mixed results**: Top-level + replies mixed together (~10%/90% split)
- **Rate limited**: Built-in delays, ~30-90 sec per 500-1,000 comments
- **Timeout handling**: Larger requests may timeout; tool includes fallbacks
- **No API quotas**: Web scraping approach, but respect YouTube's terms

## Performance Optimizations

- **Reduced timeouts**: 90s default (was 120s) for faster failure detection
- **Smaller defaults**: 500 comment samples (was 1000) for better reliability
- **Timeout fallbacks**: `get_top_comments_by_likes` tries recent sort if popular fails
- **Context efficiency**: Stats tool uses ~200 tokens vs ~25,000 for full data

## Example Usage

```python
# Get engagement overview (context-efficient)
stats = await get_comment_stats("dQw4w9WgXcQ", limit=1000)

# Find specific mentions
results = await search_comments("dQw4w9WgXcQ", "rickroll", limit=500) 

# Get viral comments by actual likes
top = await get_top_comments_by_likes("dQw4w9WgXcQ", top_count=20)
```

Built with FastMCP and youtube-comment-downloader.
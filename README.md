# YouTube Comment Downloader MCP Server

A Model Context Protocol (MCP) server that provides AI systems with the ability to download and analyze YouTube video comments using the official YouTube Data API. Built with FastMCP 2.14.5, it offers intelligent comment analysis, server-side search filtering, engagement insights, and accurate token counting optimized for LLM ingestion.

## Features

- **9 specialized tools** for comprehensive comment analysis
- **YouTube Data API** integration for 100% accurate data
- **Slim Mode** with 87% size reduction for LLM efficiency
- **Server-side filtering** reduces token usage by 99%+
- **Multi-architecture Docker** via GitHub Container Registry (amd64, arm64)
- **Accurate token counting** using Claude tokenization patterns
- **Channel discovery** workflow for targeted analysis
- **MCP resources** for quota monitoring (`youtube://quota`)
- **Prompt templates** for common analysis workflows

## MCP Client Configuration

Add this configuration block to your MCP client (e.g., Claude Desktop):

```json
{
  "ytcomment": {
    "command": "uv",
    "args": ["run", "python", "src/server.py"],
    "cwd": "/path/to/ytcomment_mcp",
    "env": {
      "YOUTUBE_API_KEY": "your-api-key-here"
    }
  }
}
```

## Available Tools

All tools are read-only (`readOnlyHint=True`) and tagged for filtering.

### Comment Analysis Tools (`read` tag)
1. **`get_video_info`** - Get video metadata and total comment count (recommended first step)
2. **`download_comments`** - Download ALL comments with slim mode (87% size reduction) and progress reporting
3. **`search_comments`** - Server-side filtered search with 99%+ token reduction
4. **`get_top_comments`** - Server-side popularity sorting with slim format
5. **`get_comment_stats`** - Statistical analysis with sample comments

### Channel Discovery Tools (`read` tag)
6. **`find_channel`** - Search YouTube channels by name or partial name
7. **`get_channel_videos`** - List channel videos with server-side title filtering

### System Tools (`read` + `system` tags)
8. **`health_check`** - Server status and API configuration check
9. **`get_quota_status`** - Monitor API usage and remaining capacity

### Resources
- **`youtube://quota`** - Current quota usage as a readable MCP resource

### Prompt Templates
- **`analyze_video_comments`** - Full sentiment/theme analysis workflow
- **`find_channel_comments`** - Channel discovery to comment search workflow
- **`compare_video_sentiment`** - Compare two videos' comment sections
- **`viral_comments_analysis`** - Find and analyze top/viral comments

## Quick Start

### Local Development
```bash
# Install dependencies
uv pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY

# Test functionality
uv run python tests/test_server.py

# Run MCP server (stdio transport for local clients)
uv run python src/server.py

# Run with streamable HTTP transport (for remote access)
uv run python src/server.py --transport streamable-http --host 0.0.0.0 --port 8080
```

### Docker Deployment
```bash
# Using pre-built image from GitHub Container Registry
docker compose up -d

# Image: ghcr.io/suckerfish/ytcomment_mcp:latest
# Platforms: linux/amd64, linux/arm64
```

## Key Features

### Slim Mode (Default)
- **87% size reduction** with essential fields only (author, text, likes, time, is_hearted)
- **Token efficient**: ~6 tokens per comment vs ~25 in full mode
- **LLM optimized**: 4x more comments in same context window

### YouTube Data API Integration
- **100% accurate** like counts and engagement metrics
- **API quota**: 10,000 units/day, 1 unit per 100 comments
- **Reliable data**: No scraping limitations or rate limits

### Context and Progress Reporting
- All tools use MCP Context for structured logging (`ctx.info`, `ctx.warning`)
- `download_comments` reports real-time progress via `ctx.report_progress()`
- Session-level quota tracking via Context state

## Example Usage

```python
# Recommended workflow: Start with video info
info = await get_video_info("dQw4w9WgXcQ")
print(f"Video has {info['statistics']['comment_count']:,} comments")

# Channel discovery workflow
channels = await find_channel("mkbhd", max_results=5)
videos = await get_channel_videos(channel_id, title_filter="iphone", limit=10)

# Efficient comment analysis
comments = await download_comments("dQw4w9WgXcQ")  # Downloads ALL, slim by default
search_results = await search_comments("dQw4w9WgXcQ", ["amazing", "review"], max_results=25)
top_comments = await get_top_comments("dQw4w9WgXcQ", top_count=20)
```

## Documentation

- **[Deployment Guide](docs/deployment.md)** - Docker and cloud deployment
- **[Quick Start Guide](docs/quickstart.md)** - Setup and basic server creation
- **[Authentication Guide](docs/authentication.md)** - YouTube API key setup
- **[Transport Troubleshooting](docs/transport-troubleshooting.md)** - Transport configuration
- **[Testing Guide](docs/testing.md)** - MCPTools usage and testing
- **[Best Practices](docs/best-practices.md)** - Error handling, performance, security

Built with [FastMCP](https://gofastmcp.com) 2.14.5 and YouTube Data API v3.

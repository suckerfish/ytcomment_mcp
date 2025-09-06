# YouTube Comment Downloader MCP Server

A Model Context Protocol (MCP) server that provides AI systems with the ability to download and analyze YouTube video comments using the official YouTube Data API. Built with FastMCP, it offers intelligent comment analysis, server-side search filtering, engagement insights, and accurate token counting optimized for LLM ingestion.

## Features

- **8 specialized tools** for comprehensive comment analysis
- **YouTube Data API** integration for 100% accurate data
- **Slim Mode** with 87% size reduction for LLM efficiency
- **Server-side filtering** reduces token usage by 99%+
- **Multi-architecture Docker support** via GitHub Container Registry
- **Accurate token counting** using Claude tokenization patterns
- **Channel discovery** workflow for targeted analysis

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

### Comment Analysis Tools
1. **`get_video_info`** - Get video metadata and total comment count (recommended first step)
2. **`download_comments`** - Smart comment download with slim mode (87% size reduction)
3. **`search_comments`** - Server-side filtered search with 99%+ token reduction
4. **`get_top_comments`** - Server-side popularity sorting with slim format
5. **`get_comment_stats`** - Statistical analysis with sample comments
6. **`get_quota_status`** - Monitor API usage and remaining capacity

### Channel Discovery Tools  
7. **`find_channel`** - Search YouTube channels by name or partial name
8. **`get_channel_videos`** - List channel videos with server-side title filtering

## Quick Start

### Local Development
```bash
# Install dependencies
uv pip install -e .

# Set up environment
cp docker/.env.example .env
# Edit .env and add your YOUTUBE_API_KEY

# Test functionality
uv run python tests/test_server.py

# Run MCP server
uv run python src/server.py
```

### Docker Deployment
```bash
# Using pre-built image from GitHub Container Registry
docker-compose up -d

# Or build locally
docker-compose up -d --build
```

### Available Images
- `ghcr.io/suckerfish/ytcomment_mcp:latest` - Latest stable version
- `ghcr.io/suckerfish/ytcomment_mcp:main` - Latest from main branch  
- Multi-architecture support (amd64, arm64)

## Key Features

### Slim Mode (Default)
- **87% size reduction** with essential fields only (author, text, likes, time, is_hearted)
- **Token efficient**: ~6 tokens per comment vs ~25 in full mode
- **LLM optimized**: 4x more comments in same context window

### YouTube Data API Integration
- **100% accurate** like counts and engagement metrics
- **API quota**: 10,000 units/day, 1 unit per 100 comments
- **Reliable data**: No scraping limitations or rate limits

### Multi-Architecture Docker Support
- **Automated builds** via GitHub Actions
- **Multi-platform**: linux/amd64, linux/arm64
- **Easy deployment**: Pre-built images available on GHCR

## Example Usage

```python
# Recommended workflow: Start with video info
info = await get_video_info("dQw4w9WgXcQ")
print(f"Video has {info['statistics']['comment_count']:,} comments")

# Channel discovery workflow
channels = await find_channel("mkbhd", max_results=5)
videos = await get_channel_videos(channel_id, title_filter="iphone", limit=10)

# Efficient comment analysis
comments = await download_comments("dQw4w9WgXcQ", limit=100, slim=True)  # 87% smaller
search_results = await search_comments("dQw4w9WgXcQ", ["amazing", "review"], max_results=25)
top_comments = await get_top_comments("dQw4w9WgXcQ", top_count=20, slim=True)
```

## Documentation

- **[GHCR Deployment Guide](docs/ghcr-deployment.md)** - Docker deployment via GitHub Container Registry
- **[Quick Start Guide](docs/quickstart.md)** - Setup and basic server creation
- **[Authentication Guide](docs/authentication.md)** - YouTube API key setup
- **[Testing Guide](docs/testing.md)** - MCPTools usage and testing

Built with FastMCP and YouTube Data API v3.
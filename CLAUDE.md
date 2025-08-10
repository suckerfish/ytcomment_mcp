# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube Comment Downloader MCP server that allows AI systems to download and analyze YouTube video comments without requiring API keys. Built with FastMCP, it provides intelligent comment analysis, search functionality, and engagement insights.

The server downloads comments via web scraping using the `youtube-comment-downloader` library and provides structured access to comment data, statistics, and search capabilities.

## Quick Commands

### Testing the YouTube Comment Server

Test the MCP server locally:

```bash
# Test server functionality directly
uv run python test_server.py

# Test token estimation for comments
uv run python test_tokens.py

# Test reply structure analysis
uv run python test_replies.py

# Test top comments by likes
uv run python test_top_likes.py

# Run the MCP server for client connections (stdio transport)
uv run python src/server.py

# Run with debug logging
uv run python src/server.py --debug

# Run with streamable HTTP transport (for remote access)
uv run python src/server.py --transport streamable-http --host 0.0.0.0 --port 8080

# Test with MCPTools
mcp tools uv run python src/server.py
```

### Package Management

```bash
# Install dependencies manually
uv pip install -e .

# Add a new dependency
uv add <package_name>
```

**Note**: When using UV with MCP servers, add `[tool.hatch.build.targets.wheel]` and `packages = ["src"]` to pyproject.toml.

## YouTube Comment Server Tools

### Available MCP Tools

**🔧 SCRAPER-BASED TOOLS (Legacy - Unreliable):**
1. **`download_youtube_comments`** - Download raw comment data (35% data loss, corrupted like counts)
2. **`get_comment_stats`** - Get statistical analysis (based on corrupted data)
3. **`search_comments`** - Search for specific terms (limited dataset)
4. **`get_top_comments_by_likes`** - Get top comments (shows wrong comments due to data corruption)

**✅ API-BASED TOOLS (Recommended - 100% Reliable):**
1. **`download_youtube_comments_api`** - Download with YouTube Data API (100% accurate)
2. **`get_comment_stats_api`** - Statistical analysis with real data
3. **`search_comments_api`** - Search through complete comment dataset
4. **`get_top_comments_by_likes_api`** - True most-liked comments (1M+ likes vs scraper's ~800 max)
5. **`get_youtube_api_quota_status`** - Monitor API usage and quota consumption

### ✅ Recommended API Usage Examples

**🔑 MCP Client Configuration:**
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

**📊 Download Comments (100% Accurate):**
```python
# Download recent comments with API
result = await download_youtube_comments_api(
    video_id="dQw4w9WgXcQ",
    limit=100,
    sort=1  # 1=recent, 0=popular
)

# Get accurate engagement statistics
stats = await get_comment_stats_api(
    video_id="dQw4w9WgXcQ", 
    limit=1000
)

# Search through complete dataset
mentions = await search_comments_api(
    video_id="dQw4w9WgXcQ",
    search_term="rickroll",
    limit=500
)

# Get REAL most-liked comments (finds 1M+ like comments)
top_comments = await get_top_comments_by_likes_api(
    video_id="dQw4w9WgXcQ",
    top_count=20,
    sample_size=1000
)

# Monitor API quota usage
quota = await get_youtube_api_quota_status()
```

### 🔧 Legacy Scraper Usage (Not Recommended)
```python
# Only use if API quota exhausted or API key unavailable
result = await download_youtube_comments(video_id="dQw4w9WgXcQ", limit=100)
```

### Input Validation with Pydantic
```python
from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

@mcp.tool()
def create_user(request: UserRequest) -> dict:
    """Create user with validated input."""
    return {"user_id": "123", "name": request.name}
```

### Error Handling
```python
from fastmcp.exceptions import ToolError

@mcp.tool()
def safe_tool(param: str) -> str:
    try:
        # Your tool logic
        return result
    except ValueError as e:
        # Client sees generic error
        raise ValueError("Invalid input")
    except SomeError as e:
        # Client sees specific error
        raise ToolError(f"Tool failed: {str(e)}")
```

### Authentication Context
```python
from fastmcp import Context

@mcp.tool()
async def authenticated_tool(param: str, ctx: Context) -> dict:
    """Tool requiring authentication."""
    user_id = ctx.client_id
    scopes = ctx.scopes
    
    if "required_scope" not in scopes:
        raise ToolError("Insufficient permissions")
    
    return {"result": f"Hello user {user_id}"}
```

## Data Structure & Capacity Planning

### Comment Data Fields (11 fields per comment)
- `cid` - Comment ID  
- `text` - Comment content
- `time` - Human readable time ("1 day ago" for scraper, ISO timestamp for API)
- `time_parsed` - Unix timestamp
- `author` - Username
- `channel` - Channel ID
- `votes` - Like count (string) - **✅ 100% accurate with API vs ❌ corrupted with scraper**
- `replies` - Reply count (string) 
- `photo` - Profile picture URL
- `heart` - Hearted by creator (boolean)
- `reply` - Is this a reply (boolean)

### Memory & Token Usage
- **Memory**: ~1,800 bytes per comment
- **Tokens**: ~22-25 tokens per comment (with metadata)
- **100 comments**: ~2,200-2,500 tokens
- **1,000 comments**: ~22,000-25,000 tokens

### Built-in Limits
- **Maximum comments per request**: 10,000
- **Memory limit**: 50MB (~28,000 comments)
- **Timeout**: 120 seconds per request
- **API Quota**: 10,000 units/day (1 unit per 100 comments)

## Project Structure

```
src/
├── server.py                   # Main MCP server with 9 tools (4 scraper + 5 API)
├── tools/
│   ├── youtube_comments.py     # Legacy comment scraping (unreliable)
│   └── youtube_api.py          # YouTube Data API client (reliable)
├── models/
│   └── youtube.py              # Pydantic models for both scraper and API
└── __init__.py

# Test files (project root)
├── test_server.py              # Basic functionality test
├── test_tokens.py              # Token estimation analysis  
├── test_replies.py             # Reply structure analysis
├── test_top_likes.py           # Top comments by likes test (scraper)
├── test_api.py                 # YouTube Data API functionality test
├── test_api_tools.py           # API-based MCP tools test
├── test_server_api.py          # MCP server API integration test
├── comparison_test.py          # Scraper vs API comparison
└── data_analysis_report.md     # Detailed findings report
```

## Essential Dependencies

- `fastmcp>=0.2.0` - MCP server framework
- `youtube-comment-downloader` - Legacy comment scraping (unreliable)
- `google-api-python-client>=2.178.0` - YouTube Data API client (reliable)
- `google-auth>=2.40.3` - Google API authentication
- `pydantic>=2.0.0` - Data validation and models
- `aiohttp>=3.8.0` - Async HTTP client

## Comprehensive Documentation

For detailed implementation guidance, see:

- **[Quick Start Guide](docs/quickstart.md)** - Setup, basic server creation, first tools
- **[Authentication Guide](docs/authentication.md)** - OAuth 2.1, security patterns, context injection
- **[Deployment Guide](docs/deployment.md)** - Production deployment, Docker, cloud platforms
- **[Transport Troubleshooting](docs/transport-troubleshooting.md)** - Transport configuration, stateless HTTP, common errors
- **[Testing Guide](docs/testing.md)** - MCPTools usage, unit testing, integration testing
- **[Best Practices](docs/best-practices.md)** - Error handling, performance, security, code quality
- **[MCPTools Documentation](docs/mcptools.md)** - Detailed testing and validation guide

## Key Implementation Notes

### ✅ YouTube Data API Implementation (Recommended)
- **Data Accuracy**: 100% accurate like counts and engagement metrics
- **Coverage**: Full comment dataset access (vs scraper's 35% data loss)
- **Performance**: ~30-60 seconds per 1,000 comments with reliable pagination
- **Quota Management**: 10,000 units/day, 1 unit per 100 comments
- **Error Handling**: Comprehensive API error handling with specific user guidance
- **True Rankings**: Finds actual viral comments (1M+ likes vs scraper's corrupted 800 max)

### 🔧 Legacy Scraper (Fallback Only)
- **Data Quality**: ❌ 35% data loss, corrupted like counts showing 0 instead of thousands
- **Coverage**: ❌ Limited to ~1,800 comments on popular videos (vs 5,000+ actual)
- **Reliability**: ❌ Frequent failures, timeout issues, missing top comments
- **Use Cases**: Only when API quota exhausted or no API key available

### Transport Configuration
- **Local Development**: Uses `stdio` transport by default
- **Remote/VPS Deployment**: Uses `streamable-http` with `stateless_http=True`
- **Production Servers**: Always configure with `stateless_http=True` for reliability
- **Current Status**: ✅ VPS deployment working with streamable HTTP transport

### Reply Structure
- Comments downloaded in **flat structure** (not hierarchical)
- Mix of top-level comments (~10%) and replies (~90%) 
- No parent-child relationships preserved
- Only boolean `reply` field distinguishes comment types

### Sorting Behavior
- `sort=0` (popular): YouTube's relevance algorithm (API) vs corrupted popular (scraper)
- `sort=1` (recent): Newest comments first
- **Critical**: Use `get_top_comments_by_likes_api` for true viral comments, not scraper version

### API Quota Management
- **Session Tracking**: Monitors usage within current MCP server session
- **Daily Limits**: 10,000 units per day, resets at midnight Pacific Time
- **Cost Efficiency**: 100 comments per API unit (10,000x more efficient than assumed)
- **Real Quota Checking**: Optional integration with Google Service Usage API

## Environment Variables

Key configuration variables:
```bash
YOUTUBE_API_KEY=your-api-key     # YouTube Data API key (REQUIRED for API tools)
PORT=8000                        # Server port
DEBUG=false                      # Debug mode
LOG_LEVEL=info                   # Logging level
```

**🔑 Getting a YouTube API Key:**
1. Go to [Google Cloud Console](https://console.developers.google.com/apis/credentials)
2. Create/select a project
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Add to MCP client configuration (see example above)

**🧪 Local Testing:**
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API key
YOUTUBE_API_KEY=your-api-key-here

# Test locally
uv run python test_api.py
```

## Configuration Patterns

### Command-Line Arguments
```python
import argparse

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Your MCP Server')
    parser.add_argument('--api-key', help='API Key')
    parser.add_argument('--config-param', help='Configuration parameter')
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    args = parse_arguments()
    from src.config.settings import initialize_config
    initialize_config(api_key=args.api_key, config_param=args.config_param)
    mcp.run()

if __name__ == "__main__":
    main()
```

### Flexible Configuration Pattern
```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Global variables that can be set by command-line arguments
API_KEY = None
CONFIG_PARAM = None

def initialize_config(api_key=None, config_param=None):
    """Initialize configuration with command-line arguments or environment variables."""
    global API_KEY, CONFIG_PARAM
    
    # Use command-line arguments if provided, otherwise fall back to environment variables
    API_KEY = api_key or os.getenv('API_KEY')
    CONFIG_PARAM = config_param or os.getenv('CONFIG_PARAM')
    
    if not API_KEY:
        raise ValueError("API key must be provided via --api-key argument or API_KEY environment variable")
```

### Configuration Import Timing
**Important**: Import configuration modules inside tool functions to avoid timing issues:

```python
# WRONG - imports at module level before config is initialized
from src.config.settings import API_KEY

@mcp.tool()
async def my_tool():
    # API_KEY will be None here
    pass

# CORRECT - import inside function after config is set
@mcp.tool()
async def my_tool():
    from src.config.settings import API_KEY  # Gets current value
    # API_KEY has correct value here
```

### Client Configuration Example
```json
"your-mcp": {
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/path/to/your/mcp",
    "src/server.py",
    "--api-key",
    "YOUR_API_KEY",
    "--config-param",
    "YOUR_VALUE"
  ]
}
```

## VPS Deployment Status

### ✅ Current Deployment Configuration
The server is successfully deployed on VPS with:
- **Transport**: Streamable HTTP with `stateless_http=True`
- **Network**: Accessible via Tailscale
- **Service**: SystemD service configured and running
- **Status**: All transport issues resolved

### Quick VPS Commands
```bash
# Check service status
sudo systemctl status ytcomment-mcp

# View logs
sudo journalctl -u ytcomment-mcp -f

# Restart service
sudo systemctl restart ytcomment-mcp

# Test endpoint
curl -H "Accept: application/json, text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}' \
     http://localhost:8080/mcp
```

## Troubleshooting

### Transport Issues (Recently Solved)
- **"Task group is not initialized"**: ✅ Fixed with `stateless_http=True`
- **SSE 404 errors**: ✅ Fixed by switching to streamable HTTP transport
- **VPS deployment issues**: ✅ Resolved with proper SystemD configuration

### Common Issues
- **Tool not found**: Check tool is registered with `@mcp.tool()` decorator
- **Validation errors**: Verify Pydantic model matches expected input
- **Authentication issues**: Check Context usage and scope validation
- **Connection issues**: Verify server is running and accessible
- **Testing failures**: Use `mcp tools --server-logs` to see detailed errors
- **Variables showing as None**: Import configuration modules inside tool functions, not at module level
- **Build wheel errors**: Add `[tool.hatch.build.targets.wheel]` and `packages = ["src"]` to pyproject.toml
- **Command-line args not working**: Ensure `initialize_config()` is called in `main()` before `mcp.run()`

For detailed transport troubleshooting, see **[Transport Troubleshooting Guide](docs/transport-troubleshooting.md)**.
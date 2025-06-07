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
python test_server.py

# Test token estimation for comments
python test_tokens.py

# Test reply structure analysis
python test_replies.py

# Test top comments by likes
python test_top_likes.py

# Run the MCP server for client connections
python src/server.py

# Run with debug logging
python src/server.py --debug
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

1. **`download_youtube_comments`** - Download raw comment data
2. **`get_comment_stats`** - Get statistical analysis (context-efficient)
3. **`search_comments`** - Search for specific terms in comments
4. **`get_top_comments_by_likes`** - Get most-liked comments (sorted by actual likes)

### Basic Usage Examples
```python
# Download recent comments
result = await download_youtube_comments(
    video_id="dQw4w9WgXcQ",
    limit=100,
    sort=1  # 1=recent, 0=popular
)

# Get engagement statistics without full data
stats = await get_comment_stats(
    video_id="dQw4w9WgXcQ", 
    limit=1000
)

# Find mentions of specific topics
mentions = await search_comments(
    video_id="dQw4w9WgXcQ",
    search_term="rickroll",
    limit=500
)

# Get top comments by actual like count (not YouTube's "popular")
top_comments = await get_top_comments_by_likes(
    video_id="dQw4w9WgXcQ",
    top_count=20,
    sample_size=1000
)
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
- `time` - Human readable time ("1 day ago")
- `time_parsed` - Unix timestamp
- `author` - Username
- `channel` - Channel ID
- `votes` - Like count (string)
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

## Project Structure

```
src/
├── server.py                   # Main MCP server with 4 tools
├── tools/
│   └── youtube_comments.py     # Comment downloading and processing
├── models/
│   └── youtube.py              # Pydantic models for validation
└── __init__.py

# Test files (project root)
├── test_server.py              # Basic functionality test
├── test_tokens.py              # Token estimation analysis  
├── test_replies.py             # Reply structure analysis
├── test_top_likes.py           # Top comments by likes test
└── data_analysis_report.md     # Detailed findings report
```

## Essential Dependencies

- `fastmcp>=0.2.0` - MCP server framework
- `youtube-comment-downloader` - Core comment scraping
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

### Reply Structure
- Comments downloaded in **flat structure** (not hierarchical)
- Mix of top-level comments (~10%) and replies (~90%) 
- No parent-child relationships preserved
- Only boolean `reply` field distinguishes comment types

### Sorting Behavior
- `sort=0` (popular): YouTube's algorithm (likes + recency + replies)
- `sort=1` (recent): Newest comments first
- **Important**: Popular ≠ most-liked! Use `get_top_comments_by_likes` for pure like ranking

### Error Handling
- Graceful handling of private/unavailable videos
- Memory usage validation before processing
- Timeout protection for long downloads
- Partial results on network issues

### Performance Characteristics
- **Download time**: ~30-60 seconds per 1,000 comments
- **Rate limiting**: Handled automatically by library
- **Memory efficient**: Streaming processing where possible

## Environment Variables

Key configuration variables:
```bash
PORT=8000                    # Server port
DEBUG=false                  # Debug mode
LOG_LEVEL=info              # Logging level
DATABASE_URL=sqlite:///app.db # Database connection
EXTERNAL_API_KEY=key123     # External service keys
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

## Troubleshooting

- **Tool not found**: Check tool is registered with `@mcp.tool()` decorator
- **Validation errors**: Verify Pydantic model matches expected input
- **Authentication issues**: Check Context usage and scope validation
- **Connection issues**: Verify server is running and accessible
- **Testing failures**: Use `mcp tools --server-logs` to see detailed errors
- **"Task group is not initialized"**: Use `stateless_http=True` for remote deployments
- **SSE 404 errors**: Switch to streamable HTTP transport with stateless mode
- **Variables showing as None**: Import configuration modules inside tool functions, not at module level
- **Build wheel errors**: Add `[tool.hatch.build.targets.wheel]` and `packages = ["src"]` to pyproject.toml
- **Command-line args not working**: Ensure `initialize_config()` is called in `main()` before `mcp.run()`
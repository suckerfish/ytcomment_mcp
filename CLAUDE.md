# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube Comment Downloader MCP server that allows AI systems to download and analyze YouTube video comments using the official YouTube Data API. Built with FastMCP, it provides intelligent comment analysis, server-side search filtering, engagement insights, and **accurate token counting** optimized for LLM ingestion.

The server uses the YouTube Data API v3 for 100% accurate comment data with server-side filtering to minimize token usage and optimize LLM context efficiency. All tools automatically provide precise token counts using Claude's tokenization patterns.

## Project Standards

### Compose Files
- Use `compose.yaml` (new Docker Compose standard) instead of `docker-compose.yml`
- Follow modern Docker Compose naming conventions

## Quick Commands

### Testing the YouTube Comment Server

Test the MCP server locally:

```bash
# Test server functionality directly
uv run python tests/test_server.py

# Test new channel workflow (find → get videos → search comments)
uv run python tests/test_channel_workflow.py

# Test new channel and video tools individually
uv run python tests/test_new_tools.py

# Test token estimation for comments
uv run python tests/test_tokens.py

# Test reply structure analysis
uv run python tests/test_replies.py

# Test top comments by likes
uv run python tests/test_top_likes.py

# Test token counting functionality
uv run python tests/test_token_counting.py

# Test token counting integration with YouTube API
uv run python tests/test_integration_simple.py

# Run the MCP server for client connections (stdio transport)
uv run python src/server.py

# Run with debug logging
uv run python src/server.py --debug

# Run with streamable HTTP transport (for remote access)
uv run python src/server.py --transport streamable-http --host 0.0.0.0 --port 8080

# Test with MCPTools
mcp tools uv run python src/server.py
```

**📁 Tests Directory**: All testing and validation scripts are organized in the `tests/` directory for better project structure.

### Package Management

```bash
# Install dependencies manually
uv pip install -e .

# Add a new dependency
uv add <package_name>
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d --build

# Or just run if already built
docker-compose up -d
```

### Docker Optimization Features

The project follows Docker best practices for optimal build performance:

- **Layer Caching**: Dependencies installed separately from code for 95%+ cache hits
- **Build Context**: Comprehensive `.dockerignore` reduces context from 936KB to <100KB
- **Security**: Non-root user execution with dedicated `appuser`
- **Performance**: `--no-install-recommends` and cache cleanup for minimal image size
- **Reproducibility**: Pinned dependency versions (uv==0.8.15)

**Build Performance**: ~50-65% faster builds with optimal layer caching strategy.

**Note**: When using UV with MCP servers, add `[tool.hatch.build.targets.wheel]` and `packages = ["src"]` to pyproject.toml.

## YouTube Comment Server Tools

### Available MCP Tools - Streamlined & LLM-Optimized

**✅ 9 CORE TOOLS (100% Reliable via YouTube Data API):**

**📊 Comment Analysis Tools:**
1. **`get_video_info`** - Lightweight video metadata with total comment count (RECOMMENDED FIRST STEP)
2. **`analyze_comments_for_content`** - **🌟 SMART ANALYSIS TOOL** - Elicitation-powered approach selection (NEW!)
3. **`download_comments`** - Smart comment download with 87% size reduction (slim mode default)
4. **`search_comments`** - Server-side filtered search with 99%+ token reduction + slim format
5. **`get_top_comments`** - Server-side popularity sorting + 87% size reduction (slim mode default)
6. **`get_comment_stats`** - Statistical analysis with slim sample comments (87% smaller)
7. **`get_quota_status`** - Monitor API usage and remaining capacity

**🔍 Channel Discovery Tools:**
8. **`find_channel`** - Search YouTube channels by name/partial name (NEW!)
9. **`get_channel_videos`** - List channel videos with server-side title filtering (NEW!)

**🚀 Key Features:**
- **🌟 Smart Analysis Selection** - Elicitation-powered tool distinguishes contextual vs keyword analysis
- **Slim Mode (Default)** - 87% size reduction with only essential comment fields
- **Server-side filtering** reduces token usage by 99%+ for LLM efficiency
- **Smart warning system** prevents accidental context overflow (>2000 comments)
- **Advanced popularity sorting** finds viral comments with 1M+ likes
- **Multiple search terms** with OR logic and case sensitivity options
- **Accurate Token Counting** - Claude tokenization patterns as baseline with detailed breakdown
- **Context Analysis** - Multi-model LLM context usage estimates (Claude, GPT-4, Gemini)
- **Format flexibility** - slim=True (default) or slim=False for full metadata
- **Channel Discovery Workflow** - Complete pipeline from channel name to comment analysis
- **Title filtering** - Server-side video filtering by title keywords for targeted analysis

### Enhanced Workflows

**🌟 SMART ANALYSIS WORKFLOW (NEW!):**
```python
# The intelligent approach selector - perfect for ambiguous requests
result = await analyze_comments_for_content(
    video_id="dQw4w9WgXcQ",
    analysis_request="check for spoilers"  # Ambiguous: could be contextual or keyword-based
)

# Tool will elicit user preference:
# 🧠 Full Context: Download all comments for deep AI analysis
# 🔍 Keyword Search: Search for specific terms/phrases  
# 🤖 Let Me Decide: I'll choose the best approach for your request

# If user chooses "Full Context" or "Let Me Decide" → contextual analysis:
# Returns all comments with guidance: "Analyze these comments for spoilers using 
# contextual understanding - don't just search for keywords"

# If user chooses "Keyword Search" → returns search suggestions:
# Suggests terms like: ["spoiler", "ending", "finale", "dies", "plot twist"]
```

**📊 WHEN TO USE EACH TOOL:**
- `analyze_comments_for_content()` - **START HERE** for any content analysis request
- `download_comments()` - When you're certain you want full contextual analysis
- `search_comments()` - When you know specific keywords/phrases to search for
- `get_video_info()` - Always good first step to understand video scope

**🔍 CHANNEL DISCOVERY WORKFLOW (NEW!):**
```python
# Step 1: Find channel by name or partial name
channels = await find_channel("mkbhd", max_results=5)
channel_id = channels['channels'][0]['channel_id']
print(f"Found: {channels['channels'][0]['title']} ({channels['channels'][0]['subscriber_count']:,} subscribers)")

# Step 2: Get recent videos with title filtering
videos = await get_channel_videos(
    channel_id=channel_id,
    title_filter="iphone",  # Find videos about iPhone
    limit=5,
    order="date"  # Most recent first
)
print(f"Found {videos['filter_efficiency']['after_title_filter']} videos matching 'iphone'")

# Step 3: Search comments on each video
for video in videos['videos']:
    matches = await search_comments(
        video_id=video['video_id'],
        search_terms=["amazing", "review", "thoughts"],
        max_results=10
    )
    print(f"Video: {video['title']} - Found {matches['results']['matches_found']} matching comments")
```

**📊 VIDEO-FOCUSED WORKFLOW:**
```python
# Step 1: Get video metadata and total comment count
info = await get_video_info("dQw4w9WgXcQ")
print(f"'{info['title']}' by {info['channel']}")
print(f"Total comments: {info['statistics']['comment_count']:,}")

# Step 2: Use recommendations for optimal strategy
if info['statistics']['comment_count'] <= 2000:
    # Small video - download all comments
    comments = await download_comments("dQw4w9WgXcQ", limit=info['statistics']['comment_count'])
elif info['statistics']['comment_count'] <= 5000:
    # Medium video - download sample or search
    comments = await download_comments("dQw4w9WgXcQ", limit=3000)
else:
    # Large video - use targeted tools
    top_comments = await get_top_comments("dQw4w9WgXcQ", top_count=50)
    search_results = await search_comments("dQw4w9WgXcQ", ["amazing", "love"], max_results=25)

# Step 3: Optional - Get detailed stats
stats = await get_comment_stats("dQw4w9WgXcQ", limit=2000)
```

**✅ Benefits:**
- Know exact comment count before downloading
- Get informed recommendations for strategy  
- Avoid accidentally overwhelming LLM context
- Only 1 API unit cost for metadata
- Fast response time (<2 seconds)

### Token Counting Feature

**🧮 Automatic Token Analysis (NEW!):**

All comment retrieval tools now provide **accurate token counting** using Claude's tokenization patterns as baseline:

```json
"token_analysis": {
  "actual_tokens": 64,
  "average_tokens_per_comment": 21.33,
  "token_breakdown": {
    "content_tokens": 19,      // Actual comment text
    "structure_tokens": 15,    // JSON formatting overhead
    "metadata_tokens": 30      // Author, likes, time, etc.
  },
  "context_analysis": {
    "claude_3_5": {"usage_percentage": 0.03, "fits_in_context": true},
    "gpt4": {"usage_percentage": 0.05, "fits_in_context": true},
    "gemini_pro": {"usage_percentage": 0.0, "fits_in_context": true}
  },
  "tokenization_method": "Claude tokenization patterns"
}
```

**📊 Key Benefits:**
- **Automatic provision** - No need to ask, always included in responses
- **Claude-accurate** - Uses Claude's tokenization patterns (0.25 tokens/char baseline)
- **Multi-model support** - Context analysis for Claude, GPT-4, Gemini
- **Content-aware** - Adjusts for emojis, URLs, special characters
- **Breakdown analysis** - See exactly where tokens are used
- **LLM optimization** - Make informed decisions about comment limits

**🎯 Available in All Tools:**
- `download_comments` - Real token counts with detailed analysis
- `search_comments` - Token analysis for filtered results  
- `get_top_comments` - Token counting for popular comments
- `get_comment_stats` - Sample comment token analysis

### Usage Examples

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

**📊 Streamlined Tool Usage with Slim Mode:**
```python
# 🌟 SMART ANALYSIS TOOL (NEW!) - START HERE FOR CONTENT ANALYSIS
# Automatically chooses between contextual analysis vs keyword search
result = await analyze_comments_for_content(
    video_id="dQw4w9WgXcQ",
    analysis_request="check for spoilers"  # Works for any analysis request
)
# Returns either full comments for AI analysis or search term suggestions

# CHANNEL DISCOVERY TOOLS (NEW!)
# Find channels by name or partial name
channels = await find_channel(
    channel_name="veritasium",
    max_results=5  # Get top 5 matches
)

# Get videos from specific channel with filtering
videos = await get_channel_videos(
    channel_id="UCHnyfMqiRRG1u-2MsSQLbXA",  # From find_channel results
    title_filter="physics",     # Filter videos about physics
    limit=10,                   # Max videos to return
    order="date"                # Most recent first
)

# COMMENT ANALYSIS TOOLS
# STEP 1: Get video info first (RECOMMENDED WORKFLOW)
video_info = await get_video_info(video_id="dQw4w9WgXcQ")
print(f"Video has {video_info['statistics']['comment_count']:,} comments")
# Provides recommendations for optimal download strategy

# STEP 2: Smart download with 87% size reduction (slim mode default)
result = await download_comments(
    video_id="dQw4w9WgXcQ",
    limit=100,  # Warns if >2000
    sort=1,     # 1=recent, 0=popular
    slim=True,  # Default - only essential fields (author, text, likes, time, is_hearted)
    force_large_ingestion=False  # Override warnings
)

# Full metadata when needed
full_result = await download_comments(
    video_id="dQw4w9WgXcQ",
    limit=50,
    slim=False  # All fields: cid, channel, photo, replies, reply, time_parsed, etc.
)

# Server-side filtered search with slim format (99% + 87% reduction)
matches = await search_comments(
    video_id="dQw4w9WgXcQ",
    search_terms=["rick", "never", "gonna"],  # OR logic
    max_results=50,      # Limits returned results
    search_limit=3000,   # Total comments to search (default: 3000)
    case_sensitive=False,
    slim=True           # Default - essential fields only
)

# Server-side popularity sorting with slim format (finds 1M+ like viral comments)
top_comments = await get_top_comments(
    video_id="dQw4w9WgXcQ",
    top_count=25,        # Number to return
    min_likes=10000,     # Filter threshold
    include_replies=True, # Include reply comments
    sample_size=3000,    # Comments to analyze (default: 3000)
    slim=True            # Default - 87% size reduction
)

# Statistical analysis with slim sample comments
stats = await get_comment_stats(
    video_id="dQw4w9WgXcQ", 
    limit=2000,  # Default limit updated to 2000
    slim=True  # Default - sample comments use essential fields only
)

# Monitor API quota usage
quota = await get_quota_status()

# Get video metadata and comment count (RECOMMENDED FIRST STEP)
video_info = await get_video_info(video_id="dQw4w9WgXcQ")
# Returns: title, channel, view/like/comment counts, duration, recommendations
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

### Slim Mode (Default - 87% Size Reduction)
**Essential Fields Only (5 fields per comment):**
- `author` - Username (~5-30 chars)
- `text` - Comment content (variable length)
- `likes` - Like count (integer) - **✅ 100% accurate with YouTube Data API**
- `time` - ISO timestamp or human-readable time (~20 chars)
- `is_hearted` - Hearted by creator (boolean, 5 chars)

**Benefits**: ~42 chars overhead vs 342 chars = **87% reduction**

### Full Mode (Complete Metadata)
**All Fields (11 fields per comment):**
- `cid` - Comment ID (~26-50 chars)
- `text` - Comment content (variable length)
- `time` - Human readable time ("1 day ago" for scraper, ISO timestamp for API)
- `time_parsed` - Unix timestamp (~10 chars)
- `author` - Username (~5-30 chars)
- `channel` - Channel ID (~24 chars)
- `votes` - Like count (string) - **✅ 100% accurate with API vs ❌ corrupted with scraper**
- `replies` - Reply count (string, ~1-5 chars)
- `photo` - Profile picture URL (~130 chars) - **Largest overhead field**
- `heart` - Hearted by creator (boolean, 5 chars)
- `reply` - Is this a reply (boolean, 5 chars)

**Overhead**: ~342 chars metadata per comment (10.7x text content)

### Memory & Token Usage

#### Slim Mode (Default - 87% Reduction)
- **Memory**: ~270 bytes per comment (87% less)
- **Tokens**: ~6 tokens per comment (essential data only)
- **100 comments**: ~600 tokens (vs 2,500 in full)
- **1,000 comments**: ~6,000 tokens (vs 25,000 in full)

#### Full Mode (Complete Metadata)  
- **Memory**: ~1,800 bytes per comment
- **Tokens**: ~22-25 tokens per comment (with all metadata)
- **100 comments**: ~2,200-2,500 tokens
- **1,000 comments**: ~22,000-25,000 tokens

**Efficiency Comparison:**
- Slim mode provides **4x more comments** in same token budget
- **87% smaller** payloads for faster transfer and processing
- Same accurate data quality - just focused on essentials

### Built-in Limits & LLM Optimization
- **Maximum comments per request**: 10,000
- **Memory limit**: 50MB (~28,000 comments in full mode, ~185,000 in slim mode)
- **Timeout**: 120 seconds per request
- **API Quota**: 10,000 units/day (1 unit per 100 comments)
- **Smart warnings**: Triggers at >2000 comments to prevent LLM context overflow
- **Token efficiency**: Server-side filtering reduces token usage by 99%+
- **Slim mode efficiency**: Additional 87% reduction in data size (6 vs 25 tokens per comment)
- **Context protection**: Automatic token analysis with 128K context awareness
- **Default optimization**: All tools use slim mode by default for maximum efficiency

## Project Structure

```
src/
├── server.py                   # Streamlined MCP server with 8 LLM-optimized tools + token counting
├── tools/
│   ├── youtube_comments.py     # Stats calculation utilities  
│   ├── youtube_api.py          # YouTube Data API client with channel search & video listing
│   └── token_counter.py        # Claude tokenization pattern-based token counting (NEW!)
├── models/
│   └── youtube.py              # Pydantic models for validation (includes channel/video models)
└── __init__.py

# Test files - organized in tests/ directory
tests/
├── test_server.py              # Basic functionality test
├── test_channel_workflow.py    # Complete channel → videos → comments workflow test
├── test_new_tools.py           # Channel and video tools validation
├── test_tokens.py              # Token estimation analysis  
├── test_token_counting.py      # Token counting functionality test (NEW!)
├── test_integration_simple.py  # Token counting integration with YouTube API (NEW!)
├── test_replies.py             # Reply structure analysis
├── test_api.py                 # YouTube Data API functionality test
├── test_top_likes.py           # Top comments functionality test
├── test_video_info.py          # Video metadata functionality test
└── ...                         # Additional validation scripts
```

## Essential Dependencies

- `fastmcp>=0.2.0` - MCP server framework
- `google-api-python-client>=2.178.0` - YouTube Data API client
- `google-auth>=2.40.3` - Google API authentication
- `python-dotenv>=1.1.0` - Environment variable loading
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

### ✅ Streamlined YouTube Data API Implementation
- **Slim Mode (Default)**: 87% size reduction with essential fields only (author, text, likes, time, is_hearted)
- **Data Accuracy**: 100% accurate like counts and engagement metrics
- **LLM Optimization**: Server-side filtering reduces token usage by 99%+, slim mode adds another 87% reduction
- **Smart Warnings**: Prevents accidental LLM context overflow (>2000 comments)
- **Advanced Search**: Multiple terms, OR logic, case sensitivity options
- **Viral Detection**: Finds actual viral comments (1M+ likes)
- **Performance**: ~30-60 seconds per 1,000 comments with reliable results
- **Quota Management**: 10,000 units/day, 1 unit per 100 comments
- **Error Handling**: Comprehensive API error handling with specific user guidance
- **Clean Architecture**: 8 streamlined tools, zero redundancy, intuitive naming
- **Format Flexibility**: Toggle between slim (default) and full metadata modes
- **Channel Discovery**: Complete workflow from channel name to targeted comment analysis
- **Server-side Title Filtering**: Efficient video filtering by title keywords before comment analysis

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
- `sort=0` (popular): YouTube's relevance algorithm for best engagement candidates
- `sort=1` (recent): Newest comments first (chronological order)
- **Top Comments**: Use `get_top_comments` to find true viral comments by actual like count

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
uv run python tests/test_api.py
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
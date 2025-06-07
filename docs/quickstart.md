# FastMCP Quick Start Guide

This guide will get you up and running with a FastMCP server in minutes.

## Prerequisites

- Python 3.11+
- UV package manager

## Installation

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new MCP server project
uv init --lib my-mcp-server
cd my-mcp-server

# Add FastMCP dependency
uv add fastmcp

# Add common dependencies for API calls and validation
uv add aiohttp pydantic
```

## Basic Server Setup

Create `src/server.py`:

```python
from fastmcp import FastMCP
from datetime import datetime

# Create the MCP server instance
mcp = FastMCP("My MCP Server")

@mcp.tool()
def get_current_time() -> str:
    """Get the current time."""
    return datetime.now().isoformat()

@mcp.tool()
async def greet_user(name: str, greeting: str = "Hello") -> str:
    """Greet a user with a custom message."""
    return f"{greeting}, {name}!"

# Run the server
if __name__ == "__main__":
    mcp.run()
```

## Test Your Server

```bash
# Install MCPTools for testing
brew tap f/mcptools && brew install mcp

# Test your server
mcp tools python src/server.py

# Call a specific tool
mcp call get_current_time python src/server.py

# Call a tool with parameters
mcp call greet_user --params '{"name":"Alice","greeting":"Hi"}' python src/server.py

# Interactive testing
mcp shell python src/server.py
```

## Adding Data Validation

Use Pydantic for structured data:

```python
from pydantic import BaseModel, Field
from typing import List

class User(BaseModel):
    name: str
    email: str = Field(..., description="User's email address")
    age: int = Field(ge=0, le=120, description="User's age")

@mcp.tool()
def create_user(user: User) -> dict:
    """Create a new user with validation."""
    return {
        "message": f"Created user {user.name}",
        "user_data": user.model_dump()
    }
```

## External API Integration

```python
import aiohttp

@mcp.tool()
async def fetch_weather(city: str) -> dict:
    """Fetch weather data for a city."""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}"
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": "Failed to fetch weather data"}
```

## Error Handling

```python
from fastmcp.exceptions import ToolError

@mcp.tool()
def divide_numbers(a: float, b: float) -> float:
    """Divide two numbers."""
    try:
        if b == 0:
            raise ToolError("Cannot divide by zero")
        return a / b
    except Exception as e:
        raise ToolError(f"Division failed: {str(e)}")
```

## Resources

Add resources for data that doesn't require parameters:

```python
@mcp.resource("app://config")
def get_app_config() -> dict:
    """Get application configuration."""
    return {
        "version": "1.0.0",
        "features": ["tools", "resources"],
        "environment": "development"
    }

# Dynamic resources with parameters
@mcp.resource("user://{user_id}/profile")
def get_user_profile(user_id: str) -> dict:
    """Get user profile by ID."""
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "status": "active"
    }
```

## Next Steps

- **Authentication**: See [authentication.md](authentication.md) for OAuth 2.1 setup
- **Deployment**: Check [deployment.md](deployment.md) for production deployment
- **Testing**: Review [testing.md](testing.md) for comprehensive testing strategies
- **Best Practices**: Read [best-practices.md](best-practices.md) for production-ready code

## Common Project Structure

```
my-mcp-server/
├── src/
│   ├── server.py          # Main server file
│   ├── tools/             # Tool definitions
│   │   ├── __init__.py
│   │   ├── data_tools.py
│   │   └── api_tools.py
│   ├── resources/         # Resource handlers
│   └── models/            # Pydantic models
├── tests/                 # Test files
├── docs/                  # Documentation
└── pyproject.toml         # Dependencies
```

## Environment Setup

Create `.env` file for configuration:

```bash
# API Keys
OPENWEATHER_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///app.db

# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=true
```

Load environment variables in your server:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Use environment variables
API_KEY = os.getenv("OPENWEATHER_API_KEY")
```
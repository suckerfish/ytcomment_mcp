# Testing Guide

This guide covers comprehensive testing strategies for FastMCP servers, from unit tests to integration testing with AI clients.

## Testing Overview

### Test Types for MCP Servers

1. **Unit Tests**: Individual tool and resource testing
2. **Integration Tests**: Full server testing with clients
3. **MCPTools Testing**: Interactive testing and debugging
4. **Authentication Tests**: OAuth flows and security
5. **Performance Tests**: Load testing and benchmarks
6. **End-to-End Tests**: Real AI client integration

## MCPTools Testing (Primary Method)

MCPTools is the primary testing tool for MCP servers during development.

### Installation

```bash
# macOS (Homebrew)
brew tap f/mcptools
brew install mcp

# From source (Go)
go install github.com/f/mcptools/cmd/mcptools@latest
```

### Basic Testing Commands

```bash
# List all available tools
mcp tools python src/server.py

# Pretty-formatted tool listing
mcp tools --format pretty python src/server.py

# Call a tool without parameters
mcp call get_time python src/server.py

# Call a tool with parameters
mcp call greet_user --params '{"name":"Alice","greeting":"Hi"}' python src/server.py

# Interactive testing shell
mcp shell python src/server.py

# View server logs during testing
mcp tools --server-logs python src/server.py
```

### Advanced MCPTools Usage

```bash
# Test with custom environment variables
mcp tools --env API_KEY=test123 python src/server.py

# Test specific transport protocols
mcp tools --transport stdio python src/server.py
mcp tools --transport http --port 8000 python src/server.py

# Test with authentication headers
mcp tools --header "Authorization: Bearer token123" http://localhost:8000/mcp

# Save test results
mcp tools python src/server.py > tools_output.json
```

### Interactive Shell Testing

```bash
# Start interactive shell
mcp shell python src/server.py

# Inside the shell:
mcp > tools                          # List available tools
mcp > call get_time                  # Call tool without params
mcp > call greet_user {"name":"Bob"} # Call tool with params
mcp > resources                      # List resources
mcp > help                          # Show help
mcp > exit                          # Exit shell
```

## Unit Testing with pytest

### Basic Test Setup

```python
# tests/conftest.py
import pytest
from fastmcp import FastMCP, Client

@pytest.fixture
def sample_server():
    """Create a test MCP server."""
    server = FastMCP("Test Server")
    
    @server.tool()
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    @server.tool()
    async def fetch_data(url: str) -> dict:
        """Fetch data from URL."""
        # Mock response for testing
        return {"url": url, "data": "test_data"}
    
    @server.resource("config://app")
    def get_config() -> dict:
        """Get app configuration."""
        return {"version": "1.0.0", "env": "test"}
    
    return server

@pytest.fixture
async def client(sample_server):
    """Create a test client."""
    async with Client(sample_server) as client:
        yield client
```

### Tool Testing

```python
# tests/test_tools.py
import pytest

async def test_add_numbers(client):
    """Test basic tool functionality."""
    result = await client.call_tool("add_numbers", {"a": 5, "b": 3})
    assert result[0].text == "8"

async def test_add_numbers_validation(client):
    """Test parameter validation."""
    # Test missing parameter
    with pytest.raises(Exception):
        await client.call_tool("add_numbers", {"a": 5})
    
    # Test wrong parameter type
    with pytest.raises(Exception):
        await client.call_tool("add_numbers", {"a": "not_a_number", "b": 3})

async def test_async_tool(client):
    """Test async tool functionality."""
    result = await client.call_tool("fetch_data", {"url": "https://example.com"})
    data = eval(result[0].text)  # Parse JSON response
    assert data["url"] == "https://example.com"
    assert data["data"] == "test_data"

async def test_tool_error_handling(sample_server):
    """Test tool error handling."""
    @sample_server.tool()
    def failing_tool() -> str:
        raise ValueError("This tool always fails")
    
    async with Client(sample_server) as client:
        with pytest.raises(Exception):
            await client.call_tool("failing_tool", {})
```

### Resource Testing

```python
# tests/test_resources.py
async def test_static_resource(client):
    """Test static resource access."""
    result = await client.read_resource("config://app")
    data = eval(result[0].text)
    assert data["version"] == "1.0.0"
    assert data["env"] == "test"

async def test_dynamic_resource():
    """Test dynamic resource with parameters."""
    server = FastMCP("Resource Test Server")
    
    @server.resource("user://{user_id}/profile")
    def get_user_profile(user_id: str) -> dict:
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    async with Client(server) as client:
        result = await client.read_resource("user://123/profile")
        data = eval(result[0].text)
        assert data["user_id"] == "123"
        assert data["name"] == "User 123"
```

### Authentication Testing

```python
# tests/test_auth.py
import pytest
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

@pytest.fixture
def auth_server():
    """Create server with authentication."""
    server = FastMCP("Auth Test Server")
    
    @server.tool()
    async def protected_tool(ctx: Context) -> dict:
        """Tool requiring authentication."""
        if not ctx.client_id:
            raise ToolError("Authentication required")
        
        if "admin" not in ctx.scopes:
            raise ToolError("Admin privileges required")
        
        return {"user_id": ctx.client_id, "message": "Access granted"}
    
    return server

async def test_authenticated_access(auth_server):
    """Test successful authentication."""
    # Mock authentication context
    async with Client(auth_server) as client:
        # In a real test, you'd set up proper auth context
        result = await client.call_tool("protected_tool", {})
        # Test would verify authenticated behavior

async def test_unauthenticated_access(auth_server):
    """Test access without authentication."""
    async with Client(auth_server) as client:
        with pytest.raises(Exception, match="Authentication required"):
            await client.call_tool("protected_tool", {})
```

## Integration Testing

### Full Server Testing

```python
# tests/test_integration.py
import pytest
import asyncio
from fastmcp import FastMCP, Client

@pytest.fixture
def full_server():
    """Create a complete test server."""
    server = FastMCP("Integration Test Server")
    
    # Add multiple tools
    @server.tool()
    def calculate(expression: str) -> float:
        """Safely evaluate math expressions."""
        try:
            # Simple calculator - only allow basic operations
            allowed_chars = set('0123456789+-*/().')
            if not all(c in allowed_chars for c in expression.replace(' ', '')):
                raise ValueError("Invalid characters in expression")
            return eval(expression)
        except Exception as e:
            raise ValueError(f"Calculation error: {str(e)}")
    
    @server.tool()
    async def batch_process(items: list[str]) -> list[str]:
        """Process multiple items."""
        processed = []
        for item in items:
            await asyncio.sleep(0.01)  # Simulate processing
            processed.append(f"processed_{item}")
        return processed
    
    # Add resources
    @server.resource("data://stats")
    def get_stats() -> dict:
        return {"total_calls": 42, "uptime": "1h 30m"}
    
    return server

async def test_multiple_tool_calls(full_server):
    """Test calling multiple tools in sequence."""
    async with Client(full_server) as client:
        # Test calculator
        result1 = await client.call_tool("calculate", {"expression": "2 + 2"})
        assert float(result1[0].text) == 4.0
        
        # Test batch processing
        result2 = await client.call_tool("batch_process", {"items": ["a", "b", "c"]})
        processed = eval(result2[0].text)
        assert processed == ["processed_a", "processed_b", "processed_c"]
        
        # Test resource access
        result3 = await client.read_resource("data://stats")
        stats = eval(result3[0].text)
        assert stats["total_calls"] == 42

async def test_concurrent_access(full_server):
    """Test multiple concurrent clients."""
    async def client_task(client_id: int):
        async with Client(full_server) as client:
            result = await client.call_tool("calculate", {"expression": f"{client_id} * 2"})
            return float(result[0].text)
    
    # Run multiple clients concurrently
    tasks = [client_task(i) for i in range(1, 6)]
    results = await asyncio.gather(*tasks)
    
    assert results == [2.0, 4.0, 6.0, 8.0, 10.0]
```

## HTTP Transport Testing

### Testing Remote Servers

```python
# tests/test_http.py
import pytest
import httpx
from fastmcp import FastMCP

@pytest.fixture
async def http_server():
    """Start HTTP server for testing."""
    server = FastMCP("HTTP Test Server")
    
    @server.tool()
    def ping() -> str:
        return "pong"
    
    # Start the server in test mode
    import uvicorn
    import threading
    
    def run_server():
        uvicorn.run(
            server.http_app(),
            host="127.0.0.1",
            port=8001,
            log_level="error"
        )
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    import time
    time.sleep(1)
    
    yield "http://127.0.0.1:8001"

async def test_http_tools_endpoint(http_server):
    """Test tools listing via HTTP."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{http_server}/mcp",
            json={"method": "tools/list", "id": 1},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]

async def test_http_tool_call(http_server):
    """Test tool calling via HTTP."""
    async with httpx.AsyncClient() as client:
        # First, initialize session
        init_response = await client.post(
            f"{http_server}/mcp",
            json={"method": "initialize", "id": 1, "params": {"protocolVersion": "2024-11-05"}},
            headers={"Content-Type": "application/json"}
        )
        assert init_response.status_code == 200
        session_id = init_response.headers.get("mcp-session-id")
        
        # Then call tool
        tool_response = await client.post(
            f"{http_server}/mcp",
            json={"method": "tools/call", "id": 2, "params": {"name": "ping", "arguments": {}}},
            headers={
                "Content-Type": "application/json",
                "mcp-session-id": session_id
            }
        )
        assert tool_response.status_code == 200
        data = tool_response.json()
        assert data["result"]["content"][0]["text"] == "pong"
```

## Performance Testing

### Load Testing

```python
# tests/test_performance.py
import pytest
import asyncio
import time
from fastmcp import FastMCP, Client

@pytest.fixture
def performance_server():
    """Create server for performance testing."""
    server = FastMCP("Performance Test Server")
    
    @server.tool()
    async def cpu_intensive(iterations: int = 1000) -> int:
        """CPU-intensive task."""
        total = 0
        for i in range(iterations):
            total += i ** 2
        return total
    
    @server.tool()
    async def io_simulation(delay: float = 0.1) -> str:
        """Simulate I/O delay."""
        await asyncio.sleep(delay)
        return f"Completed after {delay}s"
    
    return server

async def test_throughput(performance_server):
    """Test server throughput."""
    async with Client(performance_server) as client:
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = []
        for i in range(100):
            task = client.call_tool("cpu_intensive", {"iterations": 100})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = len(results) / duration
        
        print(f"Throughput: {throughput:.2f} requests/second")
        assert len(results) == 100
        assert all(int(r[0].text) > 0 for r in results)

async def test_concurrent_io(performance_server):
    """Test concurrent I/O handling."""
    async with Client(performance_server) as client:
        start_time = time.time()
        
        # Make 50 concurrent I/O requests
        tasks = [
            client.call_tool("io_simulation", {"delay": 0.1})
            for _ in range(50)
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should be much faster than sequential (50 * 0.1 = 5s)
        assert duration < 1.0  # Should complete in under 1 second
        assert len(results) == 50
```

### Memory Testing

```python
# tests/test_memory.py
import pytest
import psutil
import os
from fastmcp import FastMCP, Client

async def test_memory_usage():
    """Test memory usage doesn't grow excessively."""
    server = FastMCP("Memory Test Server")
    
    @server.tool()
    def create_data(size: int = 1000) -> str:
        """Create some data."""
        return "x" * size
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    async with Client(server) as client:
        # Make many requests
        for i in range(100):
            await client.call_tool("create_data", {"size": 10000})
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory shouldn't increase by more than 50MB
    assert memory_increase < 50 * 1024 * 1024
```

## Mock Testing

### External API Mocking

```python
# tests/test_mocks.py
import pytest
from unittest.mock import AsyncMock, patch
from fastmcp import FastMCP, Client

@pytest.fixture
def api_server():
    """Create server that calls external APIs."""
    server = FastMCP("API Test Server")
    
    @server.tool()
    async def get_weather(city: str) -> dict:
        """Get weather data."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.weather.com/v1/current?city={city}"
            async with session.get(url) as response:
                return await response.json()
    
    return server

async def test_mocked_api_call(api_server):
    """Test API call with mocked response."""
    mock_response = {
        "city": "London",
        "temperature": 20,
        "condition": "sunny"
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Setup mock
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        
        async with Client(api_server) as client:
            result = await client.call_tool("get_weather", {"city": "London"})
            data = eval(result[0].text)
            
            assert data["city"] == "London"
            assert data["temperature"] == 20
            mock_get.assert_called_once()
```

## Test Configuration

### pytest Configuration

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    auth: Authentication tests
```

### Test Environment

```python
# tests/test_config.py
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "debug"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    yield
    
    # Cleanup
    for key in ["TESTING", "LOG_LEVEL", "DATABASE_URL"]:
        os.environ.pop(key, None)
```

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install UV
        run: pip install uv
      
      - name: Install dependencies
        run: |
          uv pip install --system -e .[dev]
          uv pip install --system pytest-cov pytest-asyncio
      
      - name: Install MCPTools
        run: |
          # Install Go for MCPTools
          sudo apt-get update
          sudo apt-get install -y golang-go
          go install github.com/f/mcptools/cmd/mcptools@latest
          echo "$HOME/go/bin" >> $GITHUB_PATH
      
      - name: Run unit tests
        run: pytest tests/test_*.py -v --cov=src --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/test_integration.py -v
      
      - name: Test with MCPTools
        run: |
          mcp tools python src/server.py
          mcp call example_tool python src/server.py
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Debugging Tests

### Debug Configuration

```python
# tests/debug_server.py
"""Debug script for manual testing."""
import asyncio
from fastmcp import FastMCP, Client

async def debug_server():
    server = FastMCP("Debug Server")
    
    @server.tool()
    def debug_tool(message: str) -> str:
        print(f"Debug: {message}")
        return f"Processed: {message}"
    
    async with Client(server) as client:
        result = await client.call_tool("debug_tool", {"message": "test"})
        print(f"Result: {result[0].text}")

if __name__ == "__main__":
    asyncio.run(debug_server())
```

### Logging for Tests

```python
# tests/conftest.py
import logging

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
```

## Test Data Management

### Fixtures and Data

```python
# tests/fixtures.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_data():
    """Load sample test data."""
    data_file = Path(__file__).parent / "data" / "sample.json"
    with open(data_file) as f:
        return json.load(f)

@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing."""
    test_file = tmp_path / "test_data.txt"
    test_file.write_text("test content")
    return test_file
```

## Next Steps

- **Best Practices**: See [best-practices.md](best-practices.md) for testing best practices
- **Deployment**: Check [deployment.md](deployment.md) for production testing strategies
- **Authentication**: Review [authentication.md](authentication.md) for auth testing patterns
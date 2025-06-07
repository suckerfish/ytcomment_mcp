# FastMCP Transport Troubleshooting Guide

This guide covers transport configuration issues, common errors, and solutions for FastMCP servers, with special focus on streamable HTTP transport and remote deployments.

## Quick Reference: Transport Decision Matrix

| Scenario | Recommended Transport | Configuration | Notes |
|----------|----------------------|---------------|-------|
| Local development | `stdio` | `mcp.run()` | Default, no extra config needed |
| Local testing with MCPTools | `stdio` | `mcp.run()` | Use `mcp tools python src/server.py` |
| Remote VPS deployment | `streamable-http` + stateless | `mcp.run(transport="streamable-http", stateless_http=True)` | Most reliable for production |
| Cloud serverless (Vercel, etc.) | `streamable-http` + stateless | `mcp.run(transport="streamable-http", stateless_http=True)` | Required for stateless environments |
| Legacy client support | `sse` | `mcp.run(transport="sse")` | Only if clients don't support streamable HTTP |

## Transport Types and When to Use Them

### 1. STDIO Transport (Default)
**Best for**: Local development and testing

```python
# Default transport - no configuration needed
if __name__ == "__main__":
    mcp.run()  # Uses stdio by default
```

**Characteristics:**
- ✅ Simple, reliable for local use
- ✅ Works with all MCP clients (Claude Desktop, MCPTools)
- ❌ Local only - not accessible over network
- ❌ Requires client to launch server as subprocess

### 2. SSE Transport (Legacy)
**Best for**: Legacy clients that don't support streamable HTTP

```python
if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="0.0.0.0", 
        port=8080
    )
```

**Characteristics:**
- ✅ Wide client compatibility
- ✅ Persistent connections for real-time updates
- ❌ Complex dual-endpoint architecture
- ❌ Connection management overhead
- ❌ Poor serverless compatibility

### 3. Streamable HTTP Transport (Modern)
**Best for**: Production deployments and remote access

```python
# For stable networks (stateful mode)
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8080
    )

# For production/VPS deployment (stateless mode) - RECOMMENDED
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0", 
        port=8080,
        stateless_http=True  # Key parameter for reliability
    )
```

**Characteristics:**
- ✅ Single endpoint architecture
- ✅ Better error handling than SSE
- ✅ Serverless compatible (with stateless mode)
- ✅ HTTP/2 and proxy friendly
- ❌ Newer - some older clients may not support

## The `stateless_http=True` Parameter

### What It Does
The `stateless_http=True` parameter tells FastMCP to treat each HTTP request independently:

- **Stateful (default)**: Maintains session state, task groups, and context between requests
- **Stateless**: Each request gets fresh context - no state preserved between requests

### When to Use `stateless_http=True`

**Always use for:**
- VPS deployments over any network (including Tailscale)
- Cloud deployments (Vercel, Railway, etc.)
- Load-balanced environments
- Any production deployment

**Optional for:**
- Local development on same machine
- Very stable, direct network connections

### Performance Trade-offs

| Aspect | Stateful (default) | Stateless (`stateless_http=True`) |
|--------|-------------------|-----------------------------------|
| **Context per request** | Cached between requests | Sent with each request |
| **Memory usage** | Lower (state reuse) | Slightly higher (fresh context) |
| **Network overhead** | Lower (less context) | Slightly higher (more context) |
| **Reliability** | Can break on connection issues | Always works |
| **Error resilience** | Poor (state corruption) | Excellent (fresh start) |
| **Load balancer support** | Poor (sticky sessions needed) | Excellent (any server) |

**Bottom line**: The reliability benefits far outweigh the minor performance costs.

## Common Errors and Solutions

### 1. "Task group is not initialized"

**Error message:**
```
RuntimeError: Task group is not initialized
```

**Cause**: Using stateful streamable HTTP in an environment where connection state gets corrupted.

**Solution**: Add `stateless_http=True`:

```python
# BEFORE (problematic)
mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)

# AFTER (fixed)  
mcp.run(transport="streamable-http", host="0.0.0.0", port=8080, stateless_http=True)
```

### 2. SSE 404 Errors

**Error messages:**
```
INFO: 127.0.0.1:41996 - "GET /mcp HTTP/1.1" 404 Not Found
INFO: 127.0.0.1:42006 - "GET / HTTP/1.1" 404 Not Found
```

**Cause**: Server is configured for SSE transport but clients are hitting wrong endpoints.

**Solutions:**

**Option A: Switch to streamable HTTP (recommended)**
```python
# Change from SSE to streamable HTTP
mcp.run(transport="streamable-http", host="0.0.0.0", port=8080, stateless_http=True)
```

**Option B: Fix SSE configuration**
```python
# Ensure SSE transport is properly configured
mcp.run(transport="sse", host="0.0.0.0", port=8080)
```

### 3. SystemD Service Not Updating

**Error**: Service shows old transport configuration after deployment.

**Symptoms:**
```bash
# Service still shows old transport
└─78744 /opt/ytcomment-mcp/venv/bin/python src/server.py --transport sse --host 0.0.0.0 --port 8080
```

**Solution**: Restart the service to pick up new configuration:
```bash
sudo systemctl restart ytcomment-mcp
sudo systemctl status ytcomment-mcp  # Verify new transport is loaded
```

### 4. Connection Refused / Can't Connect

**Error**: Client cannot connect to remote server.

**Debugging steps:**
```bash
# 1. Check if server is running
sudo systemctl status your-mcp-service

# 2. Check if port is open
curl -v http://localhost:8080/mcp

# 3. Check firewall
sudo ufw status
sudo ufw allow 8080

# 4. Test with proper headers for streamable HTTP
curl -v -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}' \
  http://localhost:8080/mcp
```

### 5. FastMCP Import Errors

**Error:**
```python
ModuleNotFoundError: No module named 'fastmcp'
```

**Solutions:**
```bash
# If using uv (recommended)
uv add fastmcp

# If using pip
pip install fastmcp

# For development installation
uv pip install -e .
```

## VPS Deployment Best Practices

### Recommended VPS Configuration

**Server Code (src/server.py):**
```python
#!/usr/bin/env python3
import argparse
from fastmcp import FastMCP

# Initialize with stateless HTTP for remote deployment
mcp = FastMCP("Your MCP Server", stateless_http=True)

# Your tools here...

def parse_arguments():
    parser = argparse.ArgumentParser(description='Your MCP Server')
    parser.add_argument('--port', type=int, default=8080, help='Port number')
    parser.add_argument('--transport', choices=['stdio', 'sse', 'streamable-http'], 
                       default='stdio', help='Transport protocol')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    if args.transport == 'streamable-http':
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port
        )
    elif args.transport == 'sse':
        mcp.run(
            transport="sse", 
            host=args.host,
            port=args.port
        )
    else:
        mcp.run()  # stdio

if __name__ == "__main__":
    main()
```

**SystemD Service (deploy/your-service.service):**
```ini
[Unit]
Description=Your MCP Server
After=network.target

[Service]
Type=simple
User=your-mcp-user
Group=your-mcp-user
WorkingDirectory=/opt/your-mcp-server
Environment=PATH=/opt/your-mcp-server/venv/bin
ExecStart=/opt/your-mcp-server/venv/bin/python src/server.py --transport streamable-http --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Deployment Verification Commands

```bash
# 1. Check service status
sudo systemctl status your-mcp-service

# 2. Test local endpoint
curl -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}' \
  http://localhost:8080/mcp

# 3. View logs
sudo journalctl -u your-mcp-service -f

# 4. Test from remote (replace with your server IP)
curl -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}' \
  http://YOUR_SERVER_IP:8080/mcp
```

## Network-Specific Considerations

### Tailscale + VPS
- **Status**: Works excellently with `stateless_http=True`
- **Network reliability**: Very good (direct P2P when possible)
- **Recommendation**: Use streamable HTTP with stateless mode
- **Firewall**: Usually not needed (Tailscale handles routing)

### Traditional VPS/Cloud
- **Status**: Works well with proper configuration  
- **Network reliability**: Variable (depends on provider)
- **Recommendation**: Always use `stateless_http=True`
- **Firewall**: May need to open port 8080

### Local Development
- **Status**: All transports work
- **Network reliability**: Excellent
- **Recommendation**: Use stdio for development, test with streamable HTTP
- **Firewall**: Usually not an issue

## Transport Migration Guide

### From SSE to Streamable HTTP

**1. Update server code:**
```python
# BEFORE
mcp.run(transport="sse", host="0.0.0.0", port=8080)

# AFTER  
mcp.run(transport="streamable-http", host="0.0.0.0", port=8080, stateless_http=True)
```

**2. Update systemd service:**
```bash
# Edit service file
sudo nano /etc/systemd/system/your-service.service

# Change ExecStart line:
# FROM: --transport sse
# TO:   --transport streamable-http

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart your-service
```

**3. Verify migration:**
```bash
sudo systemctl status your-service  # Should show --transport streamable-http
curl -v http://localhost:8080/mcp   # Should get 307 redirect to /mcp/
```

### From Stateful to Stateless HTTP

**1. Update FastMCP initialization:**
```python
# BEFORE  
mcp = FastMCP("Server Name")

# AFTER
mcp = FastMCP("Server Name", stateless_http=True)
```

**2. No service changes needed** - the `stateless_http` parameter is set in code.

**3. Restart service:**
```bash
sudo systemctl restart your-service
```

## Testing Your Transport Configuration

### Local Testing Script

Create `test_transport.py`:
```python
#!/usr/bin/env python3
import asyncio
import aiohttp
import json

async def test_mcp_server(base_url="http://localhost:8080"):
    """Test MCP server transport configuration."""
    
    # Test 1: Basic connectivity
    print(f"Testing MCP server at {base_url}")
    
    async with aiohttp.ClientSession() as session:
        # Test tools/list request
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list", 
            "id": "test",
            "params": {}
        }
        
        try:
            async with session.post(f"{base_url}/mcp", 
                                  headers=headers, 
                                  json=payload) as resp:
                print(f"Status: {resp.status}")
                print(f"Headers: {dict(resp.headers)}")
                
                if resp.status == 200:
                    content = await resp.text()
                    print(f"Response: {content[:200]}...")
                    print("✅ Transport working correctly!")
                else:
                    print(f"❌ Error: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
```

Run with:
```bash
python test_transport.py
```

### MCPTools Testing

```bash
# Test with MCPTools (requires stdio transport)
mcp tools python src/server.py

# Test specific tool
mcp call your_tool_name --params '{"param": "value"}' python src/server.py

# Interactive testing  
mcp shell python src/server.py
```

## Performance Monitoring

### Key Metrics to Watch

**1. Response Times:**
```bash
# Test response time
time curl -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}' \
  http://localhost:8080/mcp
```

**2. Memory Usage:**
```bash
# Monitor memory usage
sudo systemctl status your-service  # Shows memory usage
htop  # Real-time monitoring
```

**3. Connection Health:**
```bash
# Monitor connections
sudo netstat -tlnp | grep :8080
sudo ss -tlnp | grep :8080
```

### Logging Configuration

Add structured logging to your server:
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# In your tools, add logging
logger = logging.getLogger(__name__)

@mcp.tool()
async def your_tool(param: str) -> dict:
    logger.info(f"Tool called with param: {param}")
    # Your tool logic
    logger.info("Tool completed successfully")
    return {"result": "success"}
```

## Troubleshooting Checklist

When transport issues occur, work through this checklist:

### 1. Basic Connectivity
- [ ] Server process is running (`sudo systemctl status your-service`)
- [ ] Port is accessible (`curl http://localhost:8080/mcp`)
- [ ] Firewall allows connections (`sudo ufw status`)

### 2. Transport Configuration  
- [ ] Correct transport specified in systemd service
- [ ] `stateless_http=True` set for remote deployments
- [ ] Service restarted after configuration changes

### 3. Client Configuration
- [ ] Client supports chosen transport type
- [ ] Correct endpoint URL (include `/mcp` path)
- [ ] Proper headers for streamable HTTP

### 4. Network Issues
- [ ] DNS resolution working
- [ ] Network path clear (ping, traceroute)
- [ ] No proxy/load balancer interference

### 5. Logs and Debugging
- [ ] Check server logs (`sudo journalctl -u your-service -f`)
- [ ] Enable debug logging if needed
- [ ] Test with minimal example

## Related Documentation

- **[Deployment Guide](deployment.md)** - Production deployment strategies
- **[Quick Start Guide](quickstart.md)** - Basic FastMCP setup  
- **[Best Practices](best-practices.md)** - Production-ready patterns
- **[Testing Guide](testing.md)** - Comprehensive testing strategies

For additional help, check the [FastMCP GitHub repository](https://github.com/jlowin/fastmcp) and [MCP specification](https://modelcontextprotocol.io/).
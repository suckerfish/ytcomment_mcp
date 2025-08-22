# Docker Deployment for YouTube Comment MCP Server

## Simple HTTP Setup

This setup runs the MCP server in Docker with HTTP transport for easy integration with MCP clients.

### Quick Start

1. **Set up environment:**
```bash
cd docker/
cp .env.example .env
# Edit .env with your YouTube API key
```

2. **Deploy:**
```bash
# Modern Docker (builds image automatically)
docker compose up -d

# Force rebuild if needed  
docker compose up --build -d
```

3. **Verify:**
```bash
# Check server health
curl http://localhost:8080/health

# Test MCP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}'
```

### MCP Client Configuration

Configure your MCP client to connect via HTTP:

```json
{
  "servers": {
    "ytcomment": {
      "transport": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

If your MCP client runs in Docker on the same network:
```json
{
  "servers": {
    "ytcomment": {
      "transport": "http",
      "url": "http://ytcomment-mcp:8080/mcp"
    }
  }
}
```

### Benefits

✅ **Simple**: No complex STDIO bridging  
✅ **Clean**: API key set directly in container  
✅ **Reliable**: HTTP transport is well-tested  
✅ **Scalable**: Easy to deploy and manage
✅ **Compatible**: Works with any MCP client  

### Architecture

```
MCP Client  ──HTTP──▶  YouTube MCP Container
     │                      │
     │                      ├─ YOUTUBE_API_KEY (env var)
     │                      ├─ FastMCP Server
     │                      └─ Port 8080
     │
     └─ config.json (HTTP endpoint)
```

### Production Notes

- Set strong container restart policies
- Consider adding nginx proxy for SSL termination
- Monitor container health and logs
- Use Docker secrets for API keys in production

### Troubleshooting

```bash
# Check logs
docker compose logs ytcomment-mcp

# Restart services
docker compose restart

# Clean rebuild
docker compose down
docker compose up --build -d
```
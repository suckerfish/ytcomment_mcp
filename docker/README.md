# Docker Deployment for YouTube Comment MCP Server

## Simple HTTP Setup (Recommended)

This setup runs the MCP server in Docker with HTTP transport, completely bypassing MetaMCP's STDIO environment variable limitation.

### Quick Start

1. **Set up environment:**
```bash
cd docker/
cp .env.example .env
# Edit .env with your YouTube API key
```

2. **Deploy:**
```bash
docker-compose -f simple-docker-compose.yml up -d
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

### MetaMCP Configuration

MetaMCP connects via HTTP (no environment variables needed):

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
✅ **Scalable**: Easy to add more MCP servers  
✅ **Compatible**: Works with any MetaMCP setup  

### Architecture

```
MetaMCP Container  ──HTTP──▶  YouTube MCP Container
     │                            │
     │                            ├─ YOUTUBE_API_KEY (env var)
     │                            ├─ FastMCP Server
     │                            └─ Port 8080
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
docker-compose -f simple-docker-compose.yml logs ytcomment-mcp

# Restart services
docker-compose -f simple-docker-compose.yml restart

# Clean rebuild
docker-compose -f simple-docker-compose.yml down
docker-compose -f simple-docker-compose.yml up --build -d
```
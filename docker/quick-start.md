# Quick Docker Start Guide

## 🚀 Ready to Deploy!

### 1. Set Your API Key
```bash
cd docker/
# Edit .env file with your YouTube Data API key
nano .env
# Change: YOUTUBE_API_KEY=your-actual-api-key-here
```

### 2. Deploy (Simple HTTP Setup)
```bash
# Modern Docker (builds image automatically)
docker compose up -d

# Force rebuild if needed
docker compose up --build -d
```

### 3. Test
```bash
# Health check
curl http://localhost:8080/health

# List MCP tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}'
```

### 4. Connect Your MCP Client
Configure your MCP client to connect:
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

Or if your client runs in Docker on the same network:
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

## ✅ Status: **READY FOR PRODUCTION**

All Docker files, configurations, and health checks are in place!
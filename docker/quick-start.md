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
docker-compose -f simple-docker-compose.yml up -d
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

### 4. Connect MetaMCP
Use this config in MetaMCP:
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
# GitHub Container Registry (GHCR) Deployment

This project is automatically built and published to GitHub Container Registry (GHCR) using GitHub Actions.

## Available Images

The Docker images are available at:
```
ghcr.io/suckerfish/ytcomment_mcp:latest
ghcr.io/suckerfish/ytcomment_mcp:main
ghcr.io/suckerfish/ytcomment_mcp:v1.0.0  # For tagged releases
```

## Quick Start with Pre-built Image

### 1. Create Environment File
```bash
# Copy the example and add your API key
cp docker/.env.example docker/.env
# Edit docker/.env and add your YOUTUBE_API_KEY
```

### 2. Run with Docker Compose (GHCR)
```bash
# Use the GHCR compose file
docker-compose -f compose.ghcr.yaml up -d

# Or with the regular compose file (will pull from GHCR)
docker-compose up -d
```

### 3. Run with Docker (Direct)
```bash
docker run -d \
  --name ytcomment-mcp \
  -p 8080:8080 \
  -e YOUTUBE_API_KEY=your-api-key-here \
  ghcr.io/suckerfish/ytcomment_mcp:latest
```

## Image Tags

- **`latest`** - Latest build from main branch
- **`main`** - Latest build from main branch  
- **`v1.0.0`** - Specific version tags (when you create releases)
- **`sha-abcd123`** - Specific commit builds
- **`pr-123`** - Pull request builds

## Multi-Architecture Support

Images are built for:
- `linux/amd64` (Intel/AMD x86_64)
- `linux/arm64` (Apple Silicon, ARM servers)

## Using in Production

### Docker Compose with Version Pinning
```yaml
services:
  ytcomment-mcp:
    image: ghcr.io/suckerfish/ytcomment_mcp:v1.0.0  # Pin to specific version
    # ... rest of config
```

### Pull Latest Updates
```bash
# Pull latest image
docker-compose -f compose.ghcr.yaml pull

# Restart with new image
docker-compose -f compose.ghcr.yaml up -d
```

## Configuration

### Environment Variables
- `YOUTUBE_API_KEY` - YouTube Data API key (required)
- `PORT` - Server port (default: 8080)
- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)

### Health Check
The container includes health checks that verify the MCP server is responding:
- **Endpoint**: `POST /mcp/`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## GitHub Actions Workflow

The Docker image is automatically built and pushed when:
- **Push to main** - Creates `latest` and `main` tags
- **Create tag** - Creates version tags (e.g., `v1.0.0`)
- **Pull requests** - Creates PR-specific tags for testing

## Registry Permissions

Images are public and can be pulled without authentication:
```bash
docker pull ghcr.io/suckerfish/ytcomment_mcp:latest
```

## Local Development vs GHCR

### Local Development (Build from Source)
```bash
docker-compose up -d  # Uses local Dockerfile
```

### Production (Use GHCR Image)
```bash
docker-compose -f compose.ghcr.yaml up -d  # Uses pre-built image
```

## Troubleshooting

### Image Not Found
If you get image not found errors:
1. Check the image name: `ghcr.io/suckerfish/ytcomment_mcp`
2. Ensure the repository is public
3. Try pulling manually: `docker pull ghcr.io/suckerfish/ytcomment_mcp:latest`

### Container Won't Start
1. Check logs: `docker logs ytcomment-mcp`
2. Verify environment variables are set
3. Ensure API key is valid
4. Check health status: `docker inspect --format='{{.State.Health}}' ytcomment-mcp`

### Update to Latest Version
```bash
# Stop current container
docker-compose -f compose.ghcr.yaml down

# Pull latest image
docker-compose -f compose.ghcr.yaml pull

# Start with new image
docker-compose -f compose.ghcr.yaml up -d
```
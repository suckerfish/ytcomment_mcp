# VPS Deployment Guide

This guide walks you through deploying the YouTube Comment MCP Server on your VPS as an always-on systemd service with streamable HTTP transport.

## Quick Start

1. **Clone the repository on your VPS:**
   ```bash
   git clone https://github.com/suckerfish/ytcomment_mcp.git
   cd ytcomment_mcp
   ```

2. **Run the deployment script:**
   ```bash
   sudo chmod +x deploy/vps-deploy.sh
   sudo ./deploy/vps-deploy.sh
   ```

3. **Test the deployment:**
   ```bash
   curl http://localhost:8080/mcp/health
   ```

That's it! Your MCP server is now running as a systemd service.

## What the deployment script does:

1. ✅ Installs Python 3, git, and other dependencies
2. ✅ Creates a dedicated `ytcomment-mcp` user for security
3. ✅ Sets up the application in `/opt/ytcomment-mcp/`
4. ✅ Creates a Python virtual environment and installs dependencies
5. ✅ Configures a systemd service for auto-start and restarts
6. ✅ Starts the MCP server with streamable HTTP on port 8080

## Service Management

**Check status:**
```bash
sudo systemctl status ytcomment-mcp
```

**View live logs:**
```bash
sudo journalctl -u ytcomment-mcp -f
```

**Restart service:**
```bash
sudo systemctl restart ytcomment-mcp
```

**Stop/Start service:**
```bash
sudo systemctl stop ytcomment-mcp
sudo systemctl start ytcomment-mcp
```

## Testing the MCP Server

**Health check:**
```bash
curl http://localhost:8080/mcp/health
```

**Test tools endpoint:**
```bash
curl http://localhost:8080/mcp/tools
```

**Test with a YouTube video (replace VIDEO_ID):**
```bash
curl -X POST http://localhost:8080/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_comment_stats", 
    "arguments": {
      "video_id": "dQw4w9WgXcQ",
      "limit": 100
    }
  }'
```

## Client Configuration

Connect your MCP client using streamable HTTP:

```json
{
  "type": "streamable-http", 
  "url": "http://YOUR_TAILSCALE_IP:8080/mcp"
}
```

Replace `YOUR_TAILSCALE_IP` with your VPS's Tailscale IP address.

## Resource Usage

- **RAM**: ~80-100MB
- **Storage**: ~300MB
- **Network**: Port 8080 (adjust firewall as needed)

## Security Notes

- Service runs as dedicated `ytcomment-mcp` user (not root)
- Uses systemd security features (NoNewPrivileges, ProtectSystem, etc.)
- Binds to all interfaces (0.0.0.0) - secure with firewall/Tailscale
- Logs are handled by systemd journal

## Troubleshooting

**Service won't start:**
```bash
sudo journalctl -u ytcomment-mcp --no-pager -l
```

**Check Python dependencies:**
```bash
sudo -u ytcomment-mcp /opt/ytcomment-mcp/venv/bin/pip list
```

**Manual test:**
```bash
sudo -u ytcomment-mcp /opt/ytcomment-mcp/venv/bin/python /opt/ytcomment-mcp/src/server.py --transport streamable-http --host 0.0.0.0 --port 8080 --debug
```

**Update to latest code:**
```bash
cd /opt/ytcomment-mcp
sudo -u ytcomment-mcp git pull
sudo systemctl restart ytcomment-mcp
```

## Advanced Configuration

The systemd service file is located at:
- `/etc/systemd/system/ytcomment-mcp.service`

To modify configuration:
1. Edit the service file
2. Run `sudo systemctl daemon-reload`
3. Run `sudo systemctl restart ytcomment-mcp`

## Logs Location

- **systemd logs**: `sudo journalctl -u ytcomment-mcp`
- **Application logs**: `/opt/ytcomment-mcp/logs/` (if file logging is enabled)
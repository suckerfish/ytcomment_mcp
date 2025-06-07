#!/usr/bin/env python3
"""HTTP wrapper for YouTube Comment Downloader MCP Server."""

import asyncio
import json
import sys
import subprocess
import argparse
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Comment MCP Server")

class MCPStdioWrapper:
    """Wrapper to communicate with MCP server via stdio."""
    
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.process: Optional[subprocess.Popen] = None
        
    async def start(self):
        """Start the MCP server process."""
        try:
            self.process = subprocess.Popen(
                [sys.executable, self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            logger.info("MCP server process started")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
            
    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await asyncio.sleep(1)
            if self.process.poll() is None:
                self.process.kill()
            self.process = None
            
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and get response."""
        if not self.process:
            raise HTTPException(status_code=500, detail="MCP server not running")
            
        try:
            # Send request
            request_str = json.dumps(request) + '\n'
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Read response
            response_str = self.process.stdout.readline()
            if not response_str:
                raise HTTPException(status_code=500, detail="No response from MCP server")
                
            response = json.loads(response_str.strip())
            return response
            
        except Exception as e:
            logger.error(f"Error communicating with MCP server: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Global MCP wrapper instance
mcp_wrapper = MCPStdioWrapper("/opt/ytcomment-mcp/src/server.py")

@app.on_event("startup")
async def startup_event():
    """Start the MCP server on application startup."""
    await mcp_wrapper.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the MCP server on application shutdown."""
    await mcp_wrapper.stop()

@app.get("/mcp/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "YouTube Comment MCP Server"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint that forwards requests to stdio server."""
    try:
        body = await request.json()
        response = await mcp_wrapper.send_request(body)
        return response
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    return await mcp_wrapper.send_request(request)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='YouTube Comment MCP HTTP Server')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def main():
    """Main entry point for the HTTP server."""
    args = parse_arguments()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting YouTube Comment MCP HTTP Server on {args.host}:{args.port}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="debug" if args.debug else "info"
    )

if __name__ == "__main__":
    main()
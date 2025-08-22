#!/usr/bin/env python3
"""
STDIO wrapper for YouTube Comment MCP server.
Accepts STDIO MCP requests and forwards to HTTP server on localhost.
"""

import json
import sys
import os
import requests
from typing import Any, Dict

def forward_to_http(request: Dict[str, Any]) -> Dict[str, Any]:
    """Forward MCP request to local HTTP server."""
    try:
        response = requests.post(
            "http://localhost:8080/mcp",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        return response.json()
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"HTTP forward error: {str(e)}"
            },
            "id": request.get("id")
        }

def main():
    """Handle STDIO MCP protocol."""
    # Validate API key is available
    if not os.getenv('YOUTUBE_API_KEY'):
        error = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32001,
                "message": "YOUTUBE_API_KEY environment variable required"
            }
        }
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = forward_to_http(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError:
                error = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
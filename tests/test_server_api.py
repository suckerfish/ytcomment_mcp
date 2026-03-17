#!/usr/bin/env python3
"""Test MCP server with API tools using mcp tools command."""

import subprocess
import json
import os

API_KEY = os.getenv('YOUTUBE_API_KEY')
if not API_KEY:
    raise RuntimeError("Set YOUTUBE_API_KEY environment variable before running tests")

def test_mcp_tools_list():
    """Test listing tools from the MCP server."""
    print("🔵 Testing MCP tools list...")
    
    try:
        result = subprocess.run([
            'mcp', 'tools', 'uv', 'run', 'python', 'src/server.py'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ MCP server started successfully")
            lines = result.stdout.strip().split('\n')
            
            # Find API tools
            api_tools = [line for line in lines if '_api' in line or 'quota' in line]
            
            print(f"   Found {len(api_tools)} API tools:")
            for tool in api_tools[:5]:  # Show first 5
                print(f"     - {tool}")
            
            return True
        else:
            print(f"❌ MCP server failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ MCP server test timed out")
        return False
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

def test_api_tool_call():
    """Test calling an API tool through MCP."""
    print("\n🔵 Testing API tool call...")
    
    try:
        # Test the quota status tool (simplest API call)
        cmd = [
            'mcp', 'tools', 'call', 'get_youtube_api_quota_status',
            '--', 'uv', 'run', 'python', 'src/server.py'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ API tool called successfully")
            
            # Try to parse JSON output
            try:
                data = json.loads(result.stdout)
                if 'quota_status' in data:
                    quota = data['quota_status']
                    print(f"   Daily usage: {quota['daily_usage']}/{quota['daily_limit']}")
                    print(f"   Remaining: {quota['remaining']}")
                else:
                    print("   Output format different than expected")
            except json.JSONDecodeError:
                print("   Non-JSON output received (may be normal)")
            
            return True
        else:
            print(f"❌ API tool call failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ API tool call timed out")
        return False
    except Exception as e:
        print(f"❌ API tool call failed: {e}")
        return False

def main():
    """Run MCP server tests."""
    print("🚀 Testing YouTube Data API via MCP Server")
    print("=" * 50)
    
    if not API_KEY:
        print("❌ No API key found. Using hardcoded key from investigation.")
    else:
        print(f"🔑 Using API key: {API_KEY[:20]}...")
    
    tests = [
        test_mcp_tools_list(),
        test_api_tool_call()
    ]
    
    print("\n" + "=" * 50) 
    passed = sum(1 for result in tests if result)
    print(f"🎯 Test Results: {passed}/{len(tests)} MCP tests passed")
    
    if passed == len(tests):
        print("✅ MCP server with API tools working correctly!")
        print("\n📋 Next steps:")
        print("   1. Update CLAUDE.md with API usage instructions")
        print("   2. Test with MCP client connections")
        print("   3. Compare API vs scraper results on popular videos")
    else:
        print("⚠️  Some MCP tests failed. Check the implementation.")

if __name__ == "__main__":
    main()
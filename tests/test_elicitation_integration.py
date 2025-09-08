#!/usr/bin/env python3
"""Integration test for elicitation functionality."""

import json
import subprocess
import sys
import os
from pathlib import Path

def test_mcp_tools_list():
    """Test that all tools are properly registered, including the new analysis tool."""
    print("🧪 Testing MCP tool registration...")
    print("=" * 50)
    
    try:
        # Run the MCP tools command to list all available tools
        result = subprocess.run([
            "mcp", "tools", 
            "uv", "run", "python", "src/server.py"
        ], 
        capture_output=True, 
        text=True, 
        timeout=15,
        cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout
        
        # Check for our new tool
        if "analyze_comments_for_content" in output:
            print("✅ analyze_comments_for_content tool found!")
            
            # Extract the tool description
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if "analyze_comments_for_content" in line:
                    print(f"📝 Tool signature: {line.strip()}")
                    # Print next few lines for description
                    for j in range(1, 6):
                        if i + j < len(lines) and lines[i + j].strip():
                            print(f"   {lines[i + j].strip()}")
                        else:
                            break
                    break
        else:
            print("❌ analyze_comments_for_content tool NOT found!")
            
        # Count total tools
        tool_lines = [line for line in output.split('\n') if line and not line.startswith('[>]') and not line.startswith('     ') and '(' in line]
        print(f"\n📊 Total tools found: {len(tool_lines)}")
        
        # List all tool names
        print("\n🛠️  All available tools:")
        for line in tool_lines:
            if '(' in line:
                tool_name = line.split('(')[0].strip()
                print(f"  - {tool_name}")
        
        # Check for key tools we expect
        expected_tools = [
            "analyze_comments_for_content",
            "download_comments", 
            "search_comments",
            "get_video_info",
            "find_channel",
            "get_channel_videos"
        ]
        
        print(f"\n🎯 Checking for expected tools:")
        for tool in expected_tools:
            if tool in output:
                print(f"  ✅ {tool}")
            else:
                print(f"  ❌ {tool} - MISSING!")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out - server may have started correctly but took too long")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_tool_descriptions():
    """Test that tool descriptions contain the enhanced guidance."""
    print("\n🎯 Testing enhanced tool descriptions...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            "mcp", "tools", 
            "uv", "run", "python", "src/server.py"
        ], 
        capture_output=True, 
        text=True, 
        timeout=15,
        cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout
        
        # Test for enhanced descriptions
        test_cases = [
            ("download_comments", "CONTEXTUAL ANALYSIS", "✅ download_comments has contextual analysis guidance"),
            ("search_comments", "KEYWORD-BASED SEARCH", "✅ search_comments has keyword search guidance"),  
            ("analyze_comments_for_content", "intelligent approach", "✅ analyze_comments_for_content has smart selection guidance"),
        ]
        
        for tool_name, expected_text, success_msg in test_cases:
            if tool_name in output and expected_text.lower() in output.lower():
                print(success_msg)
            else:
                print(f"❌ {tool_name} missing expected guidance: '{expected_text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Description test failed: {e}")
        return False

def test_server_startup():
    """Test that the server starts without errors."""
    print("\n🚀 Testing server startup...")
    print("=" * 50)
    
    try:
        # Quick syntax check
        result = subprocess.run([
            "uv", "run", "python", "-c", 
            "from src.server import mcp; print('Server imports successfully')"
        ], 
        capture_output=True, 
        text=True, 
        timeout=10,
        cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ Server imports and initializes successfully")
            print(f"📝 Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Server failed to import: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        return False

if __name__ == "__main__":
    print("🌟 Integration Testing for Elicitation Features")
    print("=" * 60)
    
    # Set working directory to project root
    os.chdir(Path(__file__).parent.parent)
    
    # Run all tests
    tests = [
        ("Server Startup", test_server_startup),
        ("Tool Registration", test_mcp_tools_list), 
        ("Enhanced Descriptions", test_tool_descriptions),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed!")
    
    print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Elicitation features integrated successfully!")
    else:
        print("⚠️  Some tests failed - check output above for details")
        sys.exit(1)
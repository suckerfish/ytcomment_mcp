#!/usr/bin/env python3
"""Test script for the new analyze_comments_for_content tool with elicitation."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.youtube import AnalysisMode
from src.server import analyze_comments_for_content

class MockContext:
    """Mock FastMCP Context for testing elicitation."""
    
    def __init__(self, response_data=None, action="accept"):
        self.response_data = response_data or AnalysisMode(approach="let_me_decide")
        self.action = action
    
    async def elicit(self, message, response_type):
        """Mock elicitation that returns test data."""
        print(f"🤖 ELICITATION MESSAGE:")
        print(message)
        print(f"📝 Expected Response Type: {response_type}")
        
        # Create mock elicitation result
        result = MagicMock()
        result.action = self.action
        result.data = self.response_data
        
        print(f"✅ Mock Response: {self.action} - {self.response_data}")
        return result

async def test_analysis_elicitation():
    """Test the analyze_comments_for_content tool with different scenarios."""
    
    print("🧪 Testing analyze_comments_for_content with elicitation...")
    print("=" * 60)
    
    # Test case 1: Let me decide (contextual analysis request)
    print("\n📋 TEST CASE 1: 'Let me decide' with spoiler detection")
    print("-" * 50)
    
    try:
        mock_ctx = MockContext(
            response_data=AnalysisMode(
                approach="let_me_decide",
                reasoning="I want the system to choose the best approach"
            ),
            action="accept"
        )
        
        result = await analyze_comments_for_content(
            video_id="dQw4w9WgXcQ",  # Rick Roll video - safe test
            analysis_request="check for spoilers",
            ctx=mock_ctx
        )
        
        print(f"✅ Result approach: {result.get('approach_used')}")
        print(f"📊 Reasoning: {result.get('reasoning', 'No reasoning provided')}")
        
        if result.get('approach_used') == 'full_context_analysis':
            print(f"💬 Comments returned: {len(result.get('comments_for_analysis', []))}")
            print(f"🧠 LLM Guidance: {result.get('analysis_guidance', {}).get('instruction_to_llm', '')[:100]}...")
        else:
            print(f"🔍 Search suggestions: {result.get('search_suggestions', [])}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test case 2: Explicit full context choice
    print("\n📋 TEST CASE 2: Explicit 'full context' choice")
    print("-" * 50)
    
    try:
        mock_ctx = MockContext(
            response_data=AnalysisMode(
                approach="full_context",
                reasoning="I want AI to analyze all comments contextually"
            ),
            action="accept"
        )
        
        result = await analyze_comments_for_content(
            video_id="dQw4w9WgXcQ",
            analysis_request="analyze sentiment",
            ctx=mock_ctx
        )
        
        print(f"✅ Result approach: {result.get('approach_used')}")
        print(f"📊 Analysis guidance provided: {'analysis_guidance' in result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test case 3: Keyword search choice
    print("\n📋 TEST CASE 3: Explicit 'keyword search' choice")
    print("-" * 50)
    
    try:
        mock_ctx = MockContext(
            response_data=AnalysisMode(
                approach="keyword_search",
                reasoning="I want to search for specific terms"
            ),
            action="accept"
        )
        
        result = await analyze_comments_for_content(
            video_id="dQw4w9WgXcQ",
            analysis_request="find mentions of never gonna give you up",
            ctx=mock_ctx
        )
        
        print(f"✅ Result approach: {result.get('approach_used')}")
        print(f"🔍 Search suggestions: {result.get('search_suggestions', [])}")
        print(f"📝 Next steps provided: {'next_steps' in result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test case 4: User cancellation
    print("\n📋 TEST CASE 4: User cancellation")
    print("-" * 50)
    
    try:
        mock_ctx = MockContext(action="decline")
        
        result = await analyze_comments_for_content(
            video_id="dQw4w9WgXcQ",
            analysis_request="check comments",
            ctx=mock_ctx
        )
        
        print(f"✅ Cancellation handled: {result.get('cancelled', False)}")
        print(f"📝 Message: {result.get('message', 'No message')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_search_suggestions():
    """Test the search suggestion generation."""
    print("\n🔍 Testing search suggestion generation...")
    print("-" * 50)
    
    from src.server import _generate_search_suggestions
    
    test_cases = [
        "check for spoilers",
        "analyze sentiment", 
        "find toxic comments",
        "look for controversy",
        "see reactions",
        "random analysis request"
    ]
    
    for request in test_cases:
        suggestions = _generate_search_suggestions(request)
        print(f"📝 '{request}' → {suggestions}")

if __name__ == "__main__":
    print("🌟 Testing Smart Analysis Tool with Elicitation")
    print("=" * 60)
    
    # Set environment variable for testing (you'll need a real API key for full testing)
    if not os.getenv('YOUTUBE_API_KEY'):
        print("⚠️  No YOUTUBE_API_KEY found - using mock mode")
        os.environ['YOUTUBE_API_KEY'] = 'mock_key_for_testing'
    
    # Test search suggestions (no API needed)
    test_search_suggestions()
    
    # Test elicitation logic (requires API key for video info)
    if os.getenv('YOUTUBE_API_KEY') and os.getenv('YOUTUBE_API_KEY') != 'mock_key_for_testing':
        asyncio.run(test_analysis_elicitation())
    else:
        print("\n⚠️  Skipping API-dependent tests (set YOUTUBE_API_KEY for full testing)")
    
    print("\n✅ Test script completed!")
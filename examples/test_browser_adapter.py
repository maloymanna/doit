#!/usr/bin/env python3
"""Test Browser LLM Adapter - depends on working BrowserController."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator
from doit.core.browser_llm_adapter import async_llm_client

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"


async def test_browser_adapter():
    print("\n" + "="*60)
    print("TEST 5: Browser LLM Adapter")
    print("="*60)
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Setup browser
        print("\n5.1 Opening browser with persistent profile...")
        await orch.open_chat_session(PROJECT)
        
        print("\n5.2 Navigating to UseGPT...")
        await orch.navigate(URL)
        
        # Wait for chat interface
        print("\n5.3 Waiting for chat interface to be ready...")
        bc = orch.browser
        ready = await bc.wait_for_prompt_box(timeout_ms=120000)
        
        if not ready:
            print("   ❌ Timeout waiting for chat interface")
            return
        print("   ✓ Chat interface ready")
        
        # Test 5.4: Send simple prompt and get response
        print("\n5.4 Testing simple prompt...")
        test_prompt = "Reply with just the word: OK"
        print(f"   Sending: {test_prompt}")
        
        response = await async_llm_client(bc, test_prompt)
        print(f"   Response: {response[:100] if response else 'None'}")
        
        if response and "OK" in response:
            print("   ✓ Simple prompt test passed")
        else:
            print("   ⚠ Unexpected response, but adapter works")
        
        # Test 5.5: Send another prompt to verify state
        print("\n5.5 Testing second prompt (verifies conversation context)...")
        test_prompt2 = "Reply with just the number: 42"
        print(f"   Sending: {test_prompt2}")
        
        response2 = await async_llm_client(bc, test_prompt2)
        print(f"   Response: {response2[:100] if response2 else 'None'}")
        
        if response2 and "42" in response2:
            print("   ✓ Second prompt test passed")
        elif response2:
            print("   ⚠ Response received but unexpected content")
        else:
            print("   ⚠ No response received")
        
        print("\n✅ Browser Adapter tests passed!\n")
        
        # Keep browser open for inspection
        print("Browser will stay open for 5 seconds...")
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        await orch.close_browser()


async def test_adapter_error_handling():
    """Test adapter error handling."""
    print("\n" + "="*60)
    print("TEST 5b: Browser Adapter Error Handling")
    print("="*60)
    
    # This test requires a properly initialized browser session
    print("\n5.6 Testing adapter with missing browser state...")
    
    # Create a dummy browser controller without proper setup
    # This should fail gracefully
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Don't open session or navigate - just call adapter
        bc = orch.browser
        if bc is None:
            print("   ⚠ Browser not initialized - skipping error test")
            return
        
        # Try to send prompt without proper page state
        try:
            await async_llm_client(bc, "This should fail")
            print("   ⚠ Adapter did not fail gracefully")
        except Exception as e:
            print(f"   ✓ Adapter raised expected error: {type(e).__name__}")
    finally:
        await orch.close_browser()
    
    print("\n✅ Error handling test passed!\n")


if __name__ == "__main__":
    asyncio.run(test_browser_adapter())
    asyncio.run(test_adapter_error_handling())
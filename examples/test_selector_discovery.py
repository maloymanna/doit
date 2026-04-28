"""Test selector discovery on usegpt.myorg."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

WORKSPACE = Path("~/arbitrary_folder/doit-workspace").expanduser()
URL = "https://usegpt.myorg"


async def test_selector_discovery():
    """Discover and test selectors on the actual site."""
    
    print(f"\n{'='*60}")
    print(f"Testing Selector Discovery on {URL}")
    print(f"{'='*60}")
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Open browser
        print("\n1. Opening browser...")
        await orch.open_chat_session("selector-test")
        
        # Navigate to URL
        print(f"2. Navigating to {URL}...")
        await orch.navigate(URL)
        
        print("\n3. Waiting for manual SSO (if needed)...")
        print("   Please complete login in the browser window.")
        input("   Press Enter after you're logged in and see the chat interface...")
        
        bc = orch.browser
        
        # Test each selector
        print("\n4. Testing selectors:")
        print("-" * 40)
        
        # Test new chat button
        selector = bc.sel('new_chat_button')
        if selector:
            try:
                await bc.click_new_chat()
                print(f"  ✅ New chat button: {selector}")
            except Exception as e:
                print(f"  ❌ New chat button failed: {e}")
        else:
            print(f"  ⚠ No selector for new_chat_button")
        
        # Test model selector
        selector = bc.sel('model_selector_button')
        if selector:
            try:
                await bc.click_new_chat()  # Reset first
                print(f"  ⚠ Model selector not tested (would change model)")
            except Exception as e:
                print(f"  ❌ Model selector failed: {e}")
        else:
            print(f"  ⚠ No selector for model_selector_button")
        
        # Test prompt input
        selector = bc.sel('prompt_input')
        if selector:
            try:
                await bc.page.fill(selector, "Test message")
                print(f"  ✅ Prompt input: {selector}")
            except Exception as e:
                print(f"  ❌ Prompt input failed: {e}")
        else:
            print(f"  ⚠ No selector for prompt_input")
        
        # Test send button
        selector = bc.sel('send_button_enabled')
        if selector:
            try:
                # Clear prompt first
                await bc.page.fill(bc.sel('prompt_input'), "Hello")
                await asyncio.sleep(1)
                print(f"  ✅ Send button (enabled): {selector}")
            except Exception as e:
                print(f"  ❌ Send button failed: {e}")
        else:
            print(f"  ⚠ No selector for send_button_enabled")
        
        # List all configured selectors
        print("\n5. Configured selectors:")
        print("-" * 40)
        for key, value in bc.selectors.items():
            print(f"  {key}: {value}")
        
        # Validate required selectors
        print("\n6. Validating required selectors:")
        print("-" * 40)
        missing = bc.validate_selectors()
        if missing:
            print(f"  ⚠ Missing required selectors: {missing}")
            print("  These need to be added to your selector config.")
        else:
            print("  ✅ All required selectors present!")
        
        print("\n7. Testing message extraction...")
        print("-" * 40)
        
        # Send a test message
        test_prompt = "Please respond with 'OK' to confirm selectors work."
        print(f"  Sending: {test_prompt}")
        await bc.send_prompt(test_prompt)
        
        print("  Waiting for response...")
        await asyncio.sleep(5)
        
        response = await bc.extract_last_assistant_message()
        if response:
            print(f"  ✅ Response received: {response[:100]}...")
        else:
            print("  ⚠ No response extracted (may still be generating)")
        
        print("\n" + "="*60)
        print("Selector discovery complete!")
        print("="*60)
        
        # Keep browser open for manual inspection
        print("\nBrowser will remain open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
    finally:
        await orch.close_browser()


async def test_selector_fallback():
    """Test fallback selectors when configured ones fail."""
    
    print(f"\n{'='*60}")
    print(f"Testing Selector Fallback Mechanism")
    print(f"{'='*60}")
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        await orch.open_chat_session("fallback-test")
        await orch.navigate(URL)
        
        input("\nPress Enter after completing SSO login...")
        
        bc = orch.browser
        
        # Simulate missing selector by temporarily clearing it
        original_selector = bc.selectors.get('new_chat_button')
        bc.selectors['new_chat_button'] = None  # Remove configured selector
        
        print("\nTesting fallback for new_chat_button:")
        fallback = bc.get_selector_with_fallback('new_chat_button')
        print(f"  Fallback selector: {fallback}")
        
        # Try to use fallback
        try:
            # Restore original for actual test
            bc.selectors['new_chat_button'] = original_selector
            await bc.click_new_chat()
            print("  ✅ New chat button works with original selector")
        except Exception as e:
            print(f"  ❌ New chat button failed: {e}")
        
    finally:
        await orch.close_browser()


if __name__ == "__main__":
    asyncio.run(test_selector_discovery())
    # Uncomment to test fallback:
    # asyncio.run(test_selector_fallback())
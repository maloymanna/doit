#!/usr/bin/env python3
"""Test send button detection and clicking."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "send-button-test"

async def main():
    print("\n" + "="*60)
    print("TEST 2.1: Send Button Detection")
    print("="*60)
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Launch and navigate
        await orch.open_chat_session(PROJECT)
        await orch.navigate(URL)
        
        print("\n Waiting for SSO login...")
        input(" Press Enter AFTER completing SSO login...")
        
        bc = orch.browser
        
        # Step 1: Type something in prompt box
        print("\n1. Typing test message...")
        prompt_sel = bc.sel("prompt_input")
        await bc.page.focus(prompt_sel)
        await bc.page.keyboard.press("Control+A")
        await bc.page.keyboard.press("Delete")
        await bc.page.type(prompt_sel, "Test message", delay=50)
        await asyncio.sleep(1)
        print("   ✓ Text typed")
        
        # Step 2: Detect send button
        print("\n2. Detecting send button...")
        send_sel = bc.sel("send_button_enabled")
        print(f"   Selector: {send_sel}")
        
        # Check if send button exists and is enabled
        send_button = await bc.page.query_selector(send_sel)
        if send_button:
            print("   ✓ Send button found")
            is_enabled = await send_button.is_enabled()
            print(f"   Is enabled: {is_enabled}")
        else:
            print("   ✗ Send button NOT found")
            # Try to find any button that might be send
            all_buttons = await bc.page.query_selector_all("button")
            print(f"   Total buttons on page: {len(all_buttons)}")
            for i, btn in enumerate(all_buttons[:5]):
                text = await btn.inner_text()
                print(f"     Button {i}: '{text}'")
        
        # Step 3: Click send button
        if send_button:
            print("\n3. Clicking send button...")
            await send_button.click()
            print("   ✓ Send button clicked")
            
            # Step 4: Wait a moment and check if message appeared
            await asyncio.sleep(3)
            
            # Check for user message in conversation
            user_sel = bc.sel("user_message")
            if user_sel:
                user_messages = await bc.page.query_selector_all(user_sel)
                print(f"\n   User messages found: {len(user_messages)}")
                if user_messages:
                    text = await user_messages[-1].inner_text()
                    print(f"   Last user message: '{text[:50]}'")
        
        print("\n Browser will stay open for inspection...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
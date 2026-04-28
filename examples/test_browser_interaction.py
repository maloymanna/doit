#!/usr/bin/env python3
"""Standalone browser interaction test for UseGPT."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
URL = "https://chatgpt.com"


async def test_browser_flow():
    """Complete browser interaction flow test."""
    
    print("\n" + "="*70)
    print("REAL BROWSER INTERACTION TEST - UseGPT")
    print("="*70)
    print(f"Workspace: {WORKSPACE}")
    print(f"Target URL: {URL}")
    print()
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Step 1: Launch browser
        print("1️⃣ Launching Edge with persistent profile...")
        await orch.open_chat_session("interactive-test")
        print("   ✅ Browser launched")
        
        # Step 2: Navigate to UseGPT
        print("\n2️⃣ Navigating to UseGPT...")
        await orch.navigate(URL)
        print(f"   ✅ Navigated to: {URL}")
        
        # Step 3: Handle SSO
        print("\n3️⃣ SSO Login Required")
        print("   ┌" + "─" * 66 + "┐")
        print("   │ Please complete SSO login in the browser window.    │")
        print("   │ The browser will stay open for you to log in.       │")
        print("   └" + "─" * 66 + "┘")
        input("\n   Press Enter AFTER you've successfully logged in...")
        
        bc = orch.browser
        
        # Step 4: Check prompt box
        print("\n4️⃣ Checking prompt input box...")
        prompt_selector = bc.sel('prompt_input')
        if not prompt_selector:
            prompt_selector = "textarea[data-testid='prompt-input']"
        
        try:
            await bc.page.wait_for_selector(prompt_selector, timeout=5000)
            print(f"   ✅ Prompt box detected: {prompt_selector}")
        except Exception as e:
            print(f"   ❌ Prompt box not found: {e}")
            return
        
        # Step 5: Start new chat
        print("\n5️⃣ Starting new chat...")
        await bc.click_new_chat()
        await asyncio.sleep(1)
        print("   ✅ New chat started")
        
        # Step 6: Send test prompt
        print("\n6️⃣ Sending test prompt...")
        test_prompt = "Hello! This is a test of the doit automation system. Please respond with a brief confirmation."
        print(f"   Prompt: {test_prompt[:60]}...")
        await bc.send_prompt(test_prompt)
        print("   ✅ Prompt sent")
        
        # Step 7: Wait for response
        print("\n7️⃣ Waiting for response (max 30 seconds)...")
        response = None
        for i in range(30):
            await asyncio.sleep(1)
            response = await bc.extract_last_assistant_message()
            if response and len(response) > 10:
                print(f"   ✅ Response received after {i+1} seconds")
                break
            if i % 5 == 0 and i > 0:
                print(f"      Still waiting... ({i}s)")
        
        if response:
            print(f"\n   Response preview:")
            print("-" * 70)
            # Print first 500 chars of response
            print(response[:500])
            if len(response) > 500:
                print(f"... (truncated, total {len(response)} chars)")
            print("-" * 70)
            print("\n   ✅ Response extracted successfully")
        else:
            print("   ❌ No response received")
            print("   Check if the page is functioning correctly")
        
        # Step 8: Test copy functionality
        print("\n8️⃣ Testing copy button...")
        copied = await bc.copy_last_assistant_message_via_ui()
        if copied:
            print(f"   ✅ Copied response length: {len(copied)} chars")
        else:
            print("   ⚠ Copy button test skipped (hover may be required)")
        
        # Step 9: Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print("✅ Browser launched successfully")
        print("✅ Page navigation successful")
        print("✅ Prompt box detected")
        print("✅ New chat started")
        print("✅ Prompt sent successfully")
        print(f"{'✅' if response else '❌'} Response received and extracted")
        print(f"{'✅' if copied else '⚠️'} Copy functionality")
        
        print("\n🎉 Browser interaction test complete!")
        
        # Keep browser open for manual inspection
        print("\n" + "─" * 70)
        print("Browser will remain open for 30 seconds for manual inspection.")
        print("You can interact with the chat, try uploads, etc.")
        print("─" * 70)
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nClosing browser...")
        await orch.close_browser()
        print("Done.")


async def test_multiple_turns():
    """Test multiple conversation turns."""
    
    print("\n" + "="*70)
    print("MULTI-TURN CONVERSATION TEST")
    print("="*70)
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        await orch.open_chat_session("multi-turn-test")
        await orch.navigate(URL)
        
        input("\nPress Enter after SSO login...")
        
        bc = orch.browser
        await bc.click_new_chat()
        
        turns = [
            "I'm going to test multiple turns. First, say 'Turn 1 received'.",
            "Now say 'Turn 2 received' as a follow-up.",
            "Finally, say 'Turn 3 complete' to finish."
        ]
        
        for i, prompt in enumerate(turns, 1):
            print(f"\n🔄 Turn {i}:")
            print(f"   Sending: {prompt[:50]}...")
            await bc.send_prompt(prompt)
            
            # Wait for response
            await asyncio.sleep(3)
            response = await bc.extract_last_assistant_message()
            print(f"   Response: {response[:100] if response else 'None'}...")
            
            await asyncio.sleep(1)
        
        print("\n✅ Multi-turn conversation test complete")
        
    finally:
        await orch.close_browser()


if __name__ == "__main__":
    print("Choose test:")
    print("1. Complete browser flow test")
    print("2. Multi-turn conversation test")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_multiple_turns())
    else:
        asyncio.run(test_browser_flow())
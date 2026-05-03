#!/usr/bin/env python3
"""Complete round-trip: send prompt → get response (no new chat, just send)."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

# Print test name for identification
print("\n" + "="*60)
print("RUNNING: test_round_trip_final.py")
print("="*60)

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"  # Same project as test_auto_sso.py

async def main():
    print(f"\n📁 Project: {PROJECT} (reusing persistent session)")
    print(f"🌐 URL: {URL}")
    print()
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        # Step 1: Open browser with persistent session
        print("1️⃣ Opening browser with persistent profile...")
        await orch.open_chat_session(PROJECT)
        
        # Step 2: Navigate to UseGPT
        print("2️⃣ Navigating to UseGPT...")
        await orch.navigate(URL)
        
        # Step 3: Wait for prompt box (auto-detects after SSO)
        print("3️⃣ Waiting for chat interface to be ready...")
        bc = orch.browser
        ready = await bc.wait_for_prompt_box(timeout_ms=120000)
        
        if not ready:
            print("   ❌ Timeout waiting for prompt box")
            return
        print("   ✓ Chat interface ready")
        
        # Step 4: Type prompt (no new chat - already on fresh conversation)
        prompt = "Reply with: OK"
        print(f"4️⃣ Typing prompt: '{prompt}'")
        prompt_sel = bc.sel("prompt_input")
        await bc.page.focus(prompt_sel)
        await bc.page.keyboard.press("Control+A")
        await bc.page.keyboard.press("Delete")
        await bc.page.type(prompt_sel, prompt, delay=50)
        await asyncio.sleep(0.5)
        print("   ✓ Prompt typed")
        
        # Step 5: Click send button
        print("5️⃣ Clicking send button...")
        send_sel = bc.sel("send_button_enabled")
        send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
        await send_btn.click()
        print("   ✓ Prompt sent")
        
        # Step 6: Wait for response
        print("6️⃣ Waiting for assistant response...")
        assistant_sel = bc.sel("assistant_message")
        
        # Wait for assistant message to appear
        await bc.page.wait_for_selector(assistant_sel, timeout=60000)
        
        # Get the response
        messages = await bc.page.query_selector_all(assistant_sel)
        if messages:
            response = await messages[-1].inner_text()
        else:
            response = None
        
        # Step 7: Display result
        print("\n" + "="*60)
        print("📥 RESPONSE:")
        print("="*60)
        print(response[:500] if response else "[No response received]")
        print("="*60)
        
        if response and "OK" in response:
            print("\n✅ ROUND-TRIP SUCCESSFUL!")
        else:
            print("\n⚠️ Response received but unexpected content")
        
        # Keep browser open briefly for inspection
        print("\n7️⃣ Browser will close in 5 seconds...")
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Closing browser (session preserved for next run)...")
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
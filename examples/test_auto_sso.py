#!/usr/bin/env python3
"""Test auto-detection after SSO (no manual Enter)."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"

async def main():
    print("\n" + "="*60)
    print("TEST: Auto-detection after SSO")
    print("="*60)
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        print("\n1. Opening browser...")
        await orch.open_chat_session(PROJECT)
        
        print("\n2. Navigating to UseGPT...")
        await orch.navigate(URL)
        
        print("\n3. Waiting for prompt box (auto-detects after SSO)...")
        bc = orch.browser
        found = await bc.wait_for_prompt_box(timeout_ms=120000)
        
        if found:
            print("   ✓ Prompt box detected - page is ready")
        else:
            print("   ✗ Timeout - prompt box not found")
            return
        
        print("\n4. Testing interaction...")
        prompt_sel = bc.sel("prompt_input")
        await bc.page.focus(prompt_sel)
        await bc.page.type(prompt_sel, "Auto-detection works!")
        print("   ✓ Can type in prompt box")
        
        print("\n✅ Auto-detection test complete!")
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
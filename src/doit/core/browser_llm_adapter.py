# src/doit/core/browser_llm_adapter.py [MOD v1.3]
import asyncio
import time
from typing import Optional
from ..browser.controller import BrowserController

async def async_llm_client(bc: BrowserController, prompt: str) -> Optional[str]:
    print(f"\n[ADAPTER] Starting round-trip at {time.strftime('%H:%M:%S')}")
    
    prompt_sel = bc.sel("prompt_input")
    send_sel = bc.sel("send_button_enabled")
    
    if not prompt_sel or not send_sel:
        raise RuntimeError(f"Missing selectors: prompt_input='{prompt_sel}', send_button_enabled='{send_sel}'")

    # 1. Clear & Type (proven keyboard flow)
    await bc.page.focus(prompt_sel)
    await bc.page.keyboard.press("Control+A")
    await bc.page.keyboard.press("Delete")
    await bc.page.type(prompt_sel, prompt, delay=50)
    await asyncio.sleep(0.5)
    print(f"[ADAPTER] Prompt typed. Length: {len(prompt)} chars")

    # 2. Click Send
    send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
    await send_btn.click()
    print(f"[ADAPTER] Send clicked at {time.strftime('%H:%M:%S')}. Waiting for generation...")

    # 3. WAIT FOR COMPLETION (Critical for long responses)
    # Uses your controller's proven UI state detection
    await bc.wait_for_completion(timeout_ms=180000)
    print(f"[ADAPTER] Generation marked complete at {time.strftime('%H:%M:%S')}")

    # 4. MANUAL INSPECTION WINDOW (5 seconds)
    print("[ADAPTER] ⏸️ PAUSED 5s. Check browser now: Is the full response visible?")
    await asyncio.sleep(5)

    # 5. Extract with verbose logging
    print("[ADAPTER] Attempting extraction...")
    response = await bc.extract_last_assistant_message()
    
    if response:
        print(f"[ADAPTER] ✅ Extracted {len(response)} chars. First 50: '{response[:50]}'")
    else:
        print("[ADAPTER] ❌ Extraction returned None. Checking DOM manually...")
        # Debug fallback: query the selector directly
        asst_sel = bc.sel("assistant_message") or bc.sel("message_container")
        if asst_sel:
            count = len(await bc.page.query_selector_all(asst_sel))
            print(f"[ADAPTER] DOM check: Found {count} container(s) for '{asst_sel}'")
        else:
            print("[ADAPTER] DOM check: No assistant/message selector configured")

    return response
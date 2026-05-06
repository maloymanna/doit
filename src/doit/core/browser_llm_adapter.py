# src/doit/core/browser_llm_adapter.py [MOD v1.2]
"""
Sync/Async bridge for LLM round-trip.
EXACTLY mirrors test_round_trip.py / test_browser_adapter.py flow.
Zero status-polling wrappers. Direct DOM interaction only.
"""
import asyncio
from typing import Optional
from ..browser.controller import BrowserController

async def async_llm_client(bc: BrowserController, prompt: str) -> Optional[str]:
    """
    Proven round-trip: clear → type → send → wait → extract.
    Restores the exact working sequence you verified on Win11.
    """
    # 1. Extract selectors (proven logic)
    prompt_sel = bc.sel("prompt_input")
    send_sel = bc.sel("send_button_enabled")
    assistant_sel = bc.sel("assistant_message") or bc.sel("message_container")

    if not prompt_sel or not send_sel or not assistant_sel:
        raise RuntimeError("Missing required selectors: prompt_input, send_button_enabled, or assistant_message/message_container")

    # 2. Clear & Type (proven keyboard flow)
    await bc.page.focus(prompt_sel)
    await bc.page.keyboard.press("Control+A")
    await bc.page.keyboard.press("Delete")
    await bc.page.type(prompt_sel, prompt, delay=50)
    await asyncio.sleep(0.5)  # Let JS framework register input

    # 3. Click Send
    send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
    await send_btn.click()

    # 4. Wait for response (explicit, proven)
    await bc.page.wait_for_selector(assistant_sel, timeout=120000)

    # 5. Extract (proven)
    messages = await bc.page.query_selector_all(assistant_sel)
    if not messages:
        return None
    return (await messages[-1].inner_text()).strip()
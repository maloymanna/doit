# src/doit/core/browser_llm_adapter.py [NEW v1]
import asyncio
from typing import Optional
from ..browser.controller import BrowserController

async def async_llm_client(bc: BrowserController, prompt: str) -> Optional[str]:
    """
    Proven round-trip: clear → type → send → wait → extract.
    Exact logic from test_browser_adapter.py (verified on Win11).
    """
    prompt_sel = bc.sel("prompt_input")
    send_sel = bc.sel("send_button_enabled")
    assistant_sel = bc.sel("assistant_message") or bc.sel("message_container")

    # Clear & Type (proven keyboard flow)
    await bc.page.focus(prompt_sel)
    await bc.page.keyboard.press("Control+A")
    await bc.page.keyboard.press("Delete")
    await bc.page.type(prompt_sel, prompt, delay=50)
    await asyncio.sleep(0.5)  # Let JS framework register input

    # Click Send
    send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
    await send_btn.click()

    # Wait for response
    await bc.page.wait_for_selector(assistant_sel, timeout=120000)

    # Extract
    messages = await bc.page.query_selector_all(assistant_sel)
    if not messages:
        return None
    return (await messages[-1].inner_text()).strip()
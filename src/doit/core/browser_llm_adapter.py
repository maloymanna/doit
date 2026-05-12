# src/doit/core/browser_llm_adapter.py [v2.1]
import asyncio
from typing import Optional
from ..browser.controller import BrowserController
from doit.utils.session_logger import logger

async def async_llm_client(bc: BrowserController, prompt: str, completion_timeout_ms: int = 180000) -> Optional[str]:
    logger.info("Starting round-trip")

    prompt_sel = bc.sel("prompt_input")
    send_sel = bc.sel("send_button_enabled")
    if not prompt_sel or not send_sel:
        raise RuntimeError(f"Missing selectors: prompt_input='{prompt_sel}', send_button_enabled='{send_sel}'")

    # 1. Clear & Type (proven keyboard flow)
    await bc.page.focus(prompt_sel)
    await bc.page.keyboard.press("Control+A")
    await bc.page.keyboard.press("Delete")

    # Fix for long prompts
    if len(prompt) > 500:
        # Escape backticks to avoid breaking JS template literal
        safe_text = prompt.replace("`", "\\'")
        await bc.page.evaluate(f"navigator.clipboard.writeText(`{safe_text}`)")
        await bc.page.keyboard.press("Control+V")
    else:
        await bc.page.type(prompt_sel, prompt, delay=0) # Remove typing delay

    # Small buffer for JS framework to register input
    await asyncio.sleep(0.3)
    logger.info("Prompt typed. Length: %d chars", len(prompt))

    # 2. Click Send
    send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
    await send_btn.click()
    logger.info("Send clicked. Waiting for generation...")

    # 3. WAIT FOR COMPLETION (Critical for long responses)
    # Uses your controller's proven UI state detection with config-driven timeout
    await bc.wait_for_completion(timeout_ms=completion_timeout_ms)
    logger.info("Generation marked complete (timeout: %d ms)", completion_timeout_ms)

    # 4. Extract with verbose logging
    logger.info("Attempting extraction...")
    response = await bc.extract_last_assistant_message()
    if response:
        logger.info("Extracted %d chars. First 50: '%s'", len(response), response[:50])
    else:
        logger.warning("Extraction returned None. Checking DOM manually...")
        # Debug fallback: query the selector directly
        asst_sel = bc.sel("assistant_message") or bc.sel("message_container")
        if asst_sel:
            count = len(await bc.page.query_selector_all(asst_sel))
            logger.debug("DOM check: Found %d container(s) for '%s'", count, asst_sel)
        else:
            logger.warning("DOM check: No assistant/message selector configured")

    return response
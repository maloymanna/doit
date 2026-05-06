# src/doit/core/browser_llm_adapter.py [MOD v1.1]
import asyncio
from typing import Optional
from ..browser.controller import BrowserController

async def async_llm_client(bc: BrowserController, prompt: str) -> Optional[str]:
    """
    Robust multi-turn round-trip.
    Leverages bc.send_prompt() for proven typing/clicking/status-polling.
    Avoids premature extraction race conditions on subsequent turns.
    """
    # 1. Send prompt & wait for generation to complete
    # bc.send_prompt() already handles: focus -> clear -> type -> click -> status poll
    await bc.send_prompt(prompt)

    # 2. Small buffer for final DOM rendering/token flushing
    await asyncio.sleep(0.5)

    # 3. Extract response
    response = await bc.extract_last_assistant_message()
    
    # Fallback: if DOM extraction fails (e.g., shadow DOM or heavy JS framework), try UI copy
    if not response:
        response = await bc.copy_last_assistant_message_via_ui()

    return response
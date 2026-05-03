"""Adapter to use BrowserController as an LLM client."""

from typing import Callable
import asyncio


def create_llm_client(browser_controller) -> Callable[[str], str]:
    """Create a sync LLM client from browser controller."""
    def llm_client(prompt: str) -> str:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_llm_client(browser_controller, prompt))
        finally:
            loop.close()
    return llm_client


async def async_llm_client(browser_controller, prompt: str) -> str:
    """
    Send prompt and return response.
    """
    bc = browser_controller
    
    # Step 1: Type prompt
    prompt_sel = bc.sel("prompt_input")
    await bc.page.focus(prompt_sel)
    await bc.page.keyboard.press("Control+A")
    await bc.page.keyboard.press("Delete")
    await bc.page.type(prompt_sel, prompt, delay=50)
    await asyncio.sleep(0.5)
    print("   ✓ Prompt typed")
    
    # Step 2: Click send button (from test_round_trip.py)
    send_sel = bc.sel("send_button_enabled")
    send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
    await send_btn.click()
    print("   ✓ Prompt sent")
    
    # Step 3: Wait for for completion using model selector button class
    print("   Waiting for response to complete...")
    await bc.wait_for_completion()
    
    # Debug: find all assistant containers
    assistant_sel = bc.sel("assistant_message")
    all_containers = await bc.page.query_selector_all(assistant_sel)
           
    # Step 4: Extract full response
    print("Extracting full response...")
    assistant_sel = bc.sel("assistant_message")

    # Wait for the last assistant container to exist
    await bc.page.wait_for_selector(assistant_sel, timeout=10000)
    
    # Get all assistant messages
    all_messages = await bc.page.query_selector_all(assistant_sel)
    if not all_messages:
        response = None
    else:
        # Get the last one (most recent response)
        last_message = all_messages[-1]
        
        # Method 1: Try to get all token divs inside and combine
        token_divs = await last_message.query_selector_all("div[data-testid*='-token-']")
        if token_divs:
            full_response = ""
            for token_div in token_divs:
                part = await token_div.inner_text()
                if part.strip():
                    full_response += part + "\n"
            response = full_response.strip()
        else:
            # Method 2: Fallback to entire inner text
            response = await last_message.inner_text() 
        
    if not response:
        response = ""
    
    return response
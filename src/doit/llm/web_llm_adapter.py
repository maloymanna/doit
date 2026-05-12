# src/doit/llm/web_llm_adapter.py [MOD v1.4]
"""
Sync adapter wrapping your PROVEN test_round_trip.py flow.
Exactly mirrors the working script with minimal changes for sync/async bridging.
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional
import warnings
from doit.utils.session_logger import logger

warnings.filterwarnings("ignore", category=DeprecationWarning, module="asyncio")

from doit.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class WebLLMSyncAdapter:
    def __init__(self, workspace: Path, project: str, url: str):
        self.workspace = workspace
        self.project = project
        self.url = url
        self._orch: Optional[Orchestrator] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._initialized = False

    def _ensure_loop(self):
        """Create or return a persistent event loop to avoid Playwright context poisoning."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def send_prompt(self, prompt: str) -> str:
        loop = self._ensure_loop()
        return loop.run_until_complete(self._async_round_trip(prompt))

    async def _async_round_trip(self, prompt: str) -> str:
        # 1. Initialize browser ONCE (persistent session)
        if not self._initialized:
            logger.info("[LLM] Initializing Orchestrator (persistent session)...")
            self._orch = Orchestrator(self.workspace)
            await self._orch.open_chat_session(self.project)
            await self._orch.navigate(self.url)
            
            # 🛑 MANUAL INTERVENTION WINDOW
            logger.info("\n⏳ [LLM] PAUSING 15 SECONDS. Manually click SKIP or log in if prompted.")
            logger.info("   Agent will resume automatically after pause...\n")
            await asyncio.sleep(15)
            self._initialized = True

        bc = await self._orch.ensure_browser()

        # 2. Wait for prompt box (EXACTLY like test_round_trip.py)
        ready = await bc.wait_for_prompt_box(timeout_ms=120000)
        if not ready:
            raise RuntimeError("Prompt box not found after 120s timeout")

        # 3. Type prompt (PROVEN FLOW)
        prompt_sel = bc.sel("prompt_input")
        await bc.page.focus(prompt_sel)
        await bc.page.keyboard.press("Control+A")
        await bc.page.keyboard.press("Delete")
        await bc.page.type(prompt_sel, prompt, delay=50)
        await asyncio.sleep(0.5)
        logger.info("[LLM] ✓ Prompt typed")

        # 4. Click Send (PROVEN FLOW)
        send_sel = bc.sel("send_button_enabled")
        send_btn = await bc.page.wait_for_selector(send_sel, timeout=10000)
        await send_btn.click()
        logger.info("[LLM] ✓ Send clicked. Waiting for response...")

        # 5. Wait for assistant message (EXACTLY like test_round_trip.py)
        assistant_sel = bc.sel("assistant_message")
        if not assistant_sel:
            raise RuntimeError("Missing selector: 'assistant_message' in your config")
            
        await bc.page.wait_for_selector(assistant_sel, timeout=120000)

        # 6. Extract response (EXACTLY like test_round_trip.py)
        messages = await bc.page.query_selector_all(assistant_sel)
        if not messages:
            raise RuntimeError("No assistant messages found on page")

        response = await messages[-1].inner_text()
        if not response or len(response.strip()) == 0:
            raise RuntimeError("Extracted assistant message is empty")

        logger.info("[LLM] ✓ Response extracted successfully")
        return response.strip()

    def close(self):
        """Gracefully shutdown browser and event loop."""
        if self._orch:
            loop = self._ensure_loop()
            try:
                loop.run_until_complete(self._orch.close_browser())
                logger.info("[LLM] ✓ Browser session closed")
            except Exception as e:
                logger.warning(f"[LLM] Close warning (safe to ignore): {e}")
            finally:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
                self._orch = None
                self._initialized = False
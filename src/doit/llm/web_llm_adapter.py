# src/doit/llm/web_llm_adapter.py [MOD v1.1]
import asyncio
import logging
from pathlib import Path
from typing import Optional
from doit.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class WebLLMSyncAdapter:
    """
    Sync adapter wrapping the existing async Orchestrator/Controller.
    Provides a simple send_prompt(text) -> str interface for the AgentOrchestrator.
    """
    def __init__(self, workspace: Path, project: str, url: str):
        self.workspace = workspace
        self.project = project
        self.url = url
        self._orch: Optional[Orchestrator] = None

    def _init_orchestrator(self):
        if self._orch is None:
            logger.info(f"[LLM] Initializing Orchestrator for workspace: {self.workspace}")
            self._orch = Orchestrator(self.workspace)

    def _safe_async_run(self, coro):
        """Safely run async code with event-loop crash protection."""
        try:
            return asyncio.run(coro)
        except RuntimeError as e:
            if "Event loop is closed" in str(e) or "cannot be called from a running event loop" in str(e):
                logger.warning(f"[LLM] Skipped async call (loop state): {e}")
                return None
            raise

    def send_prompt(self, prompt: str) -> str:
        self._init_orchestrator()
        logger.debug(f"[LLM] Sending prompt (len={len(prompt)})")

        async def _async_round_trip():
            orch = self._orch
            await orch.open_chat_session(self.project)
            await orch.navigate(self.url)

            # === MANUAL SKIP / BROADCAST MESSAGE WINDOW ===
            print("\n⏳ PAUSING 10s. If you see a broadcast/SKIP message, CLICK IT NOW.")
            print("   (Agent will resume automatically after pause)\n")
            await asyncio.sleep(10)

            bc = await orch.ensure_browser()
            ready = await bc.wait_for_prompt_box(timeout_ms=120000)
            if not ready:
                raise RuntimeError("Timed out waiting for chat interface prompt box")

            await bc.send_prompt(prompt)
            
            # Extract with fallback
            response = await bc.extract_last_assistant_message()
            if not response or len(response.strip()) == 0:
                logger.warning("No assistant message via DOM. Attempting UI copy fallback...")
                response = await bc.copy_last_assistant_message_via_ui()
                
            if not response or len(response.strip()) == 0:
                raise RuntimeError("No assistant message extracted after prompt")

            return response.strip()

        result = self._safe_async_run(_async_round_trip())
        if result is None:
            raise RuntimeError("LLM round-trip failed or was skipped due to loop state")
        return result

    def close(self):
        """Gracefully close browser session."""
        if self._orch:
            async def _close():
                try:
                    await self._orch.close_browser()
                except Exception as e:
                    logger.warning(f"[LLM] Browser close warning: {e}")
            
            self._safe_async_run(_close())
            self._orch = None
            logger.info("[LLM] Browser session closed.")
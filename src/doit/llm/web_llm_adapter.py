# src/doit/llm/web_llm_adapter.py [NEW v1]
import asyncio
import logging
from pathlib import Path
from typing import Optional
from doit.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class WebLLMSyncAdapter:
    """
    Sync adapter wrapping the existing async Orchestrator/Controller.
    Provides a simple send_prompt(text) -> str interface for the new AgentOrchestrator.
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

    def send_prompt(self, prompt: str) -> str:
        """Sends a single-line prompt to the web LLM and returns raw response text."""
        self._init_orchestrator()
        logger.debug(f"[LLM] Sending prompt (len={len(prompt)})")

        async def _async_round_trip():
            orch = self._orch
            # 1. Open/Reuse persistent session
            await orch.open_chat_session(self.project)
            # 2. Navigate to LLM site
            await orch.navigate(self.url)
            # 3. Ensure prompt box is ready
            bc = await orch.ensure_browser()
            ready = await bc.wait_for_prompt_box(timeout_ms=120000)
            if not ready:
                raise RuntimeError("Timed out waiting for chat interface prompt box")

            # 4. Send prompt (existing controller handles fill + click + wait + status poll)
            await bc.send_prompt(prompt)

            # 5. Extract response
            response = await bc.extract_last_assistant_message()
            if not response:
                raise RuntimeError("No assistant message extracted after prompt")

            return response.strip()

        # Safe sync call: AgentOrchestrator has no running event loop
        return asyncio.run(_async_round_trip())

    def close(self):
        """Gracefully close browser session."""
        if self._orch:
            try:
                asyncio.run(self._orch.close_browser())
                logger.info("[LLM] Browser session closed.")
            except Exception as e:
                logger.warning(f"[LLM] Error closing browser: {e}")
            self._orch = None
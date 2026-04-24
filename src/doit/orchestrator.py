from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio

from .config import Config
from .permissions import Permissions
from .files import FileManager
from .browser.controller import (
    BrowserController,
    EdgeUnavailableError,
    AllowlistError,
    BrowserError,
)


class Orchestrator:
    """
    High‑level orchestrator for Milestone 2.

    - Owns Config, Permissions, FileManager, BrowserController
    - Exposes high‑level methods for:
      - opening chat sessions
      - sending prompts
      - querying status
      - scrolling
      - extracting responses (all modes)
      - navigation + page text
    """

    def __init__(self, workspace_root: Path):
        self.config = Config(workspace_root)
        self.permissions = Permissions(self.config)
        self.files = FileManager(self.permissions)
        self.browser: Optional[BrowserController] = None

    # -----------------------------
    # Browser lifecycle
    # -----------------------------
    async def ensure_browser(self) -> BrowserController:
        if self.browser is None:
            self.browser = BrowserController(self.config)
            await self.browser.ensure_running()
        return self.browser

    async def open_chat_session(self, project_name: str):
        bc = await self.ensure_browser()
        return await bc.open_chat_session(project_name)

    async def close_browser(self):
        if self.browser:
            await self.browser.close_session()
            self.browser = None

    # -----------------------------
    # Chat operations
    # -----------------------------
    async def start_new_chat(self, project_name: str, url: str, model_name: Optional[str] = None):
        """
        Open session, navigate to URL, click New chat, select model.
        """
        bc = await self.ensure_browser()
        await bc.open_chat_session(project_name)
        await bc.navigate(url)
        await bc.click_new_chat()
        await bc.select_model(model_name)

    async def send_prompt(
        self,
        project_name: str,
        url: str,
        text: str,
        files: Optional[List[str]] = None,
        model_name: Optional[str] = None,
    ):
        """
        High‑level: ensure session, navigate, new chat (if first time), select model, send prompt.
        """
        bc = await self.ensure_browser()

        if bc.session_dir is None or bc.session_dir.name != project_name:
            await bc.open_chat_session(project_name)

        # Navigate only if not already on the target URL (best‑effort)
        try:
            current_url = bc.page.url if bc.page else ""
        except Exception:
            current_url = ""

        if not current_url.startswith(url):
            await bc.navigate(url)

        # Assume caller decides when to start a new chat; we expose it separately
        if model_name:
            await bc.select_model(model_name)

        await bc.send_prompt(text, files=files)

    # -----------------------------
    # Status + scrolling
    # -----------------------------
    async def get_status(self) -> str:
        bc = await self.ensure_browser()
        return await bc.get_status()

    async def scroll_to_top(self):
        bc = await self.ensure_browser()
        await bc.scroll_to_top()

    async def scroll_to_bottom(self):
        bc = await self.ensure_browser()
        await bc.scroll_to_bottom()

    async def scroll_by(self, delta: int):
        bc = await self.ensure_browser()
        await bc.scroll_by(delta)

    async def scroll_message_into_view(self, index: int):
        bc = await self.ensure_browser()
        await bc.scroll_message_into_view(index)

    # -----------------------------
    # Extraction modes
    # -----------------------------
    async def get_last_response(self) -> Optional[str]:
        bc = await self.ensure_browser()
        return await bc.extract_last_assistant_message()

    async def get_conversation_history(self) -> List[Dict[str, str]]:
        bc = await self.ensure_browser()
        return await bc.extract_all_messages()

    async def get_last_response_tokens(self) -> List[str]:
        bc = await self.ensure_browser()
        return await bc.extract_last_assistant_tokens()

    async def get_last_response_via_copy(self) -> Optional[str]:
        bc = await self.ensure_browser()
        return await bc.copy_last_assistant_message_via_ui()

    # -----------------------------
    # Navigation + page text
    # -----------------------------
    async def navigate(self, url: str):
        bc = await self.ensure_browser()
        await bc.navigate(url)

    async def fetch_page_text(self, url: str) -> str:
        bc = await self.ensure_browser()
        return await bc.fetch_page_text(url)

    async def fetch_youtube_transcript(self, url: str) -> Optional[str]:
        bc = await self.ensure_browser()
        return await bc.fetch_youtube_transcript(url)

    # -----------------------------
    # Synchronous entry point (non‑browser commands)
    # -----------------------------
    def run(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Placeholder for non‑browser commands (plugins, git, etc.).
        Milestone 2 focuses on browser integration; this remains minimal.
        """
        return {"status": "ok", "command": command, "kwargs": kwargs}

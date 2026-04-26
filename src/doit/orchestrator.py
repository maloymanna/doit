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
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()        
        self.config = Config(self.workspace_root)
        self.permissions = Permissions.non_interactive(str(self.workspace_root))
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
    async def start_new_chat(self, project_name: str, url: str, model_name: Optional[str] = None, wait_for_sso: bool = True):
        """
        Open session, navigate to URL, wait for SSO if needed, click New chat, select model.
        """
        bc = await self.ensure_browser()
        
        # Open persistent session
        await bc.open_chat_session(project_name)
        
        # Navigate to the URL
        await bc.navigate(url)
        
        # Wait for SSO login if requested
        if wait_for_sso:
            from urllib.parse import urlparse
            target_host = urlparse(url).netloc
            print(f"Waiting for SSO completion and navigation to {target_host}...")
            await bc.wait_for_sso(target_host)
            print("SSO completed or navigation detected!")
        
        # Now click new chat and select model
        await bc.click_new_chat()
        if model_name:
            await bc.select_model(model_name)

    async def ensure_session_and_navigate(self, project_name: str, url: str, wait_for_sso: bool = True):
        """
        Ensure a session is open and navigated to the URL, handling SSO if needed.
        """
        bc = await self.ensure_browser()
        
        if bc.session_dir is None or bc.session_dir.name != project_name:
            await bc.open_chat_session(project_name)
        
        # Navigate only if not already on the target URL
        try:
            current_url = bc.page.url if bc.page else ""
        except Exception:
            current_url = ""
        
        if not current_url.startswith(url):
            await bc.navigate(url)
            if wait_for_sso:
                from urllib.parse import urlparse
                target_host = urlparse(url).netloc
                print(f"Waiting for SSO completion and navigation to {target_host}...")
                await bc.wait_for_sso(target_host)

    async def send_prompt(
        self,
        project_name: str,
        url: str,
        text: str,
        files: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        wait_for_sso: bool = False,  # Assume already handled if calling this
    ):
        """
        Send a prompt in the current chat session.
        """
        bc = await self.ensure_browser()
        
        # Ensure we're on the right page with session
        await self.ensure_session_and_navigate(project_name, url, wait_for_sso=wait_for_sso)
        
        # Select model if specified
        if model_name:
            await bc.select_model(model_name)
        
        # Send the prompt
        await bc.send_prompt(text, files=files)

    async def start_new_conversation(self):
        """
        Start a fresh conversation in the current session (clears current chat).
        """
        bc = await self.ensure_browser()
        await bc.click_new_chat()

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
    # Synchronous entry point
    # -----------------------------
    def run(self, command: str, **kwargs) -> Dict[str, Any]:
        return {"status": "ok", "command": command, "kwargs": kwargs}
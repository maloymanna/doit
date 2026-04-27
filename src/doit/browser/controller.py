import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from playwright.async_api import (
    async_playwright,
    BrowserContext,
    Page,
    TimeoutError as PWTimeout,
)

from ..config import Config


# -----------------------------
# Exceptions
# -----------------------------
class BrowserError(Exception):
    pass


class EdgeUnavailableError(BrowserError):
    pass


class AllowlistError(BrowserError):
    pass


# -----------------------------
# Browser Controller
# -----------------------------
class BrowserController:
    """
    Edge‑only Playwright controller for Milestone 2.

    Supports:
    - Persistent profile per project
    - New chat
    - Model selection
    - Prompt sending
    - Response completion detection
    - Extraction modes (latest, full conversation, tokens, UI-copy)
    - File upload flow
    - Scrolling
    - Status reporting
    """

    def __init__(self, config: Config):
        self.config = config
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_dir: Optional[Path] = None

        pw_cfg = self.config.data.get("playwright", {})
        self.timeout_ms = pw_cfg.get("timeout_ms", 15000)
        self.headless = pw_cfg.get("headless", False)
        self.launch_args = pw_cfg.get("launch_args", [])
        self.model_name = pw_cfg.get("model_name", "GPT-5.1")
        self.selectors = pw_cfg.get("selectors", {})

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def sel(self, key: str) -> Optional[str]:
        return self.selectors.get(key)

    async def _wait(self, ms: int):
        await asyncio.sleep(ms / 1000)

    # -----------------------------
    # Playwright lifecycle
    # -----------------------------
    async def ensure_running(self):
        """Ensure Playwright is running and Edge is available."""
        if self.playwright:
            return

        self.playwright = await async_playwright().start()

        # Test Edge availability
        try:
            ctx = await self.playwright.chromium.launch(
                channel="msedge",
                headless=True,
            )
            await ctx.close()
        except Exception as exc:
            print(f"[ensure_running] Browser launch failed: {exc}")
            raise EdgeUnavailableError(
                "Microsoft Edge (msedge) could not be launched. "
                "This controller is Edge‑only."
            ) from exc

    async def open_chat_session(self, project_name: str) -> Page:
        """Open persistent Edge session for a project."""
        await self.ensure_running()

        workspace = Path(self.config.data["workspace_root"]).resolve()
        sessions = workspace / ".doit" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)

        self.session_dir = sessions / project_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                channel="msedge",
                headless=self.headless,
                args=self.launch_args,
            )
        except Exception as exc:
            print(f"[open_chat_session] Failed to launch persistent context: {exc}")
            raise EdgeUnavailableError(
                "Failed to launch Edge persistent context."
            ) from exc

        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        return self.page

    async def close_session(self):
        """Close browser and Playwright."""
        try:
            if self.context:
                await self.context.close()
        finally:
            if self.playwright:
                await self.playwright.stop()

        self.context = None
        self.page = None
        self.playwright = None
        self.session_dir = None

    # -----------------------------
    # Allowlist
    # -----------------------------
    def _is_url_allowed(self, url: str) -> bool:
        allowlist = []

        workspace = Path(self.config.data["workspace_root"]).resolve()
        allowlist_file = workspace / ".doit" / "allowlist.txt"

        if allowlist_file.exists():
            allowlist = [
                line.strip()
                for line in allowlist_file.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

        if not allowlist:
            allowlist = self.config.data.get("allowlist", [])

        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        for pattern in allowlist:
            if pattern.endswith("*"):
                if normalized.startswith(pattern[:-1]):
                    return True
            else:
                if normalized == pattern:
                    return True

        return False

    def _load_selectors_for_url(self, url: str):
        """Load selectors specific to the current URL domain."""
        from urllib.parse import urlparse
        from pathlib import Path
        
        domain = urlparse(url).netloc.replace('www.', '')
        selector_file = self.config.doit_dir / 'selectors' / f"{domain}.yaml"
        
        if selector_file.exists():
            import yaml
            with open(selector_file, 'r') as f:
                data = yaml.safe_load(f)
                custom_selectors = data.get('selectors', {})
                # Merge with existing selectors (custom overrides defaults)
                self.selectors.update(custom_selectors)
                print(f"[BrowserController] Loaded selectors for {domain}")
        else:
            print(f"[BrowserController] No domain-specific selectors for {domain}, using defaults")

    async def navigate(self, url: str, wait_until="networkidle"):
        if not self.page:
            raise BrowserError("Session not open.")

        if not self._is_url_allowed(url):
            raise AllowlistError(f"URL not allowed: {url}")

        await self.page.goto(url, wait_until=wait_until)
        self._load_selectors_for_url(url)

    # -----------------------------
    # SSO Login Helper (FIXED: properly indented as a method)
    # -----------------------------
    async def wait_for_sso(self, target_host: str, timeout_ms: int = 120000):
        """
        If an SSO/login page appears, wait for the user to complete manual login
        and for navigation to the target_host (e.g. usegpt.myorg).
        """
        if not self.page:
            raise BrowserError("Session not open.")

        # quick check: if already on target host, return immediately
        try:
            parsed = urlparse(self.page.url)
            if parsed.netloc and target_host in parsed.netloc:
                return
        except Exception:
            pass

        # Wait for either a login page or direct navigation to target_host.
        # First wait briefly to see if a login page appears.
        try:
            await self.page.wait_for_url("**/login**", timeout=5000)
            # user likely needs to login manually; wait for navigation to target_host
            await self.page.wait_for_url(f"**://*{target_host}**/*", timeout=timeout_ms)
        except PWTimeout:
            # no explicit /login detected; still wait for target_host navigation
            try:
                await self.page.wait_for_url(f"**://*{target_host}**/*", timeout=timeout_ms)
            except PWTimeout:
                # final fallback: do nothing (caller can decide)
                return

    # -----------------------------
    # Status API
    # -----------------------------
    async def get_status(self) -> str:
        """
        Returns:
        - "idle"
        - "sending"
        - "generating"
        - "complete"
        - "error"
        """
        if not self.page:
            return "error"

        send_disabled = self.sel("send_button_disabled")
        send_enabled = self.sel("send_button_enabled")

        try:
            disabled_btn = await self.page.query_selector(send_disabled)
            if disabled_btn:
                return "generating"
        except Exception:
            pass

        try:
            enabled_btn = await self.page.query_selector(send_enabled)
            if enabled_btn:
                return "idle"
        except Exception:
            pass

        return "idle"

    # -----------------------------
    # Scrolling API
    # -----------------------------
    async def scroll_to_top(self):
        await self.page.evaluate("window.scrollTo(0, 0)")

    async def scroll_to_bottom(self):
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    async def scroll_by(self, delta: int):
        await self.page.evaluate(f"window.scrollBy(0, {delta})")

    async def scroll_message_into_view(self, index: int):
        containers = await self.page.query_selector_all(self.sel("message_container"))
        if index < 0 or index >= len(containers):
            return
        await containers[index].scroll_into_view_if_needed()

    # -----------------------------
    # New chat
    # -----------------------------
    async def click_new_chat(self):
        new_chat_selector = self.sel("new_chat_button")
        if not new_chat_selector:
            # Fallback selector if not in config
            new_chat_selector = "button:has-text('New chat')"
        
        btn = await self.page.wait_for_selector(new_chat_selector, timeout=self.timeout_ms)
        await btn.click()

    # -----------------------------
    # Model selection
    # -----------------------------
    async def select_model(self, model_name: Optional[str] = None):
        model_name = model_name or self.model_name

        model_selector = self.sel("model_selector_button")
        if not model_selector:
            # Fallback selector
            model_selector = "button:has-text('Model')"
        
        btn = await self.page.wait_for_selector(model_selector, timeout=self.timeout_ms)
        await btn.click()

        item = await self.page.wait_for_selector(f"button:has-text('{model_name}')", timeout=self.timeout_ms)
        await item.click()

    # -----------------------------
    # Prompt sending
    # -----------------------------
    async def send_prompt(self, text: str, files: Optional[List[str]] = None):
        if not self.page:
            raise BrowserError("Session not open.")

        prompt_sel = self.sel("prompt_input")
        send_enabled = self.sel("send_button_enabled")

        if not prompt_sel or not send_enabled:
            raise BrowserError("Required selectors not configured")

        # Fill prompt (contenteditable)
        await self.page.focus(prompt_sel)
        await self.page.eval_on_selector(
            prompt_sel,
            "el => { el.innerText = arguments[0]; }",
            text,
        )

        # Upload files if needed
        if files:
            await self.upload_file(files)

        # Click send
        btn = await self.page.wait_for_selector(send_enabled, timeout=self.timeout_ms)
        await btn.click()

        # Wait for generation to start
        await self._wait(200)

        # Wait for completion
        while True:
            status = await self.get_status()
            if status == "complete" or status == "idle":
                break
            await self._wait(200)

    # -----------------------------
    # File upload
    # -----------------------------
    async def upload_file(self, paths: List[str]):
        upload_btn = await self.page.wait_for_selector(self.sel("upload_button"), timeout=self.timeout_ms)
        await upload_btn.click()

        attach_btn = await self.page.wait_for_selector(self.sel("attach_file_button"), timeout=self.timeout_ms)
        await attach_btn.click()

        # Playwright auto-handles file chooser
        async with self.page.expect_file_chooser() as fc_info:
            pass  # clicking attach triggers chooser

        file_chooser = await fc_info.value
        await file_chooser.set_files(paths)

    # -----------------------------
    # Extraction Modes (Option E)
    # -----------------------------
    async def extract_last_assistant_message(self) -> Optional[str]:
        containers = await self.page.query_selector_all(self.sel("message_container"))
        if not containers:
            return None
        return await containers[-1].inner_text()

    async def extract_all_messages(self) -> List[Dict[str, str]]:
        results = []

        # User messages
        user_sel = self.sel("user_message")
        if user_sel:
            user_nodes = await self.page.query_selector_all(user_sel)
            for node in user_nodes:
                txt = await node.inner_text()
                results.append({"role": "user", "text": txt})

        # Assistant messages
        asst_sel = self.sel("message_container")
        if asst_sel:
            asst_nodes = await self.page.query_selector_all(asst_sel)
            for node in asst_nodes:
                txt = await node.inner_text()
                results.append({"role": "assistant", "text": txt})

        return results

    async def extract_last_assistant_tokens(self) -> List[str]:
        token_sel = self.sel("message_token")
        if not token_sel:
            return []
        nodes = await self.page.query_selector_all(token_sel)
        return [await n.inner_text() for n in nodes]

    async def copy_last_assistant_message_via_ui(self) -> Optional[str]:
        copy_btn = await self.page.query_selector(self.sel("copy_button"))
        if not copy_btn:
            return None

        await copy_btn.hover()
        await copy_btn.click()

        # Read clipboard
        try:
            return await self.page.evaluate("navigator.clipboard.readText()")
        except Exception:
            return None

    # -----------------------------
    # Page extraction
    # -----------------------------
    async def fetch_page_text(self, url: str) -> str:
        await self.navigate(url)
        body = await self.page.query_selector("body")
        return await body.inner_text() if body else ""

    async def fetch_youtube_transcript(self, url: str) -> Optional[str]:
        # Basic placeholder; YouTube transcript extraction is Milestone 4
        await self.navigate(url)
        return await self.fetch_page_text(url)
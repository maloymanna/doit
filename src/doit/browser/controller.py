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

        # Load from config.playwright (which reads from playwright_config.yaml)
        pw_cfg = config.playwright
        self.timeout_ms = pw_cfg.timeout_ms  # Should be 20000
        self.navigation_timeout_ms = pw_cfg.navigation_timeout_ms  # Should be 30000
        self.headless = pw_cfg.headless
        self.launch_args = pw_cfg.launch_args
        self.model_name = config.browser.default_model  # From config.yaml

        # Load selectors (will be overridden per URL)
        self.selectors = pw_cfg.selectors.data

        self.current_domain = None
        self.strict_selectors = False   # temporary

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def sel(self, key: str) -> Optional[str]:
        """Get selector for current context."""
        return self.selectors.get(key)

    async def _wait(self, ms: int):
        await asyncio.sleep(ms / 1000)

    async def get_status(self) -> str:
        """
        Returns current chat status.
        
        Possible values: "idle", "sending", "generating", "complete", "error"
        """
        if not self.page:
            return "error"
        
        # Check for generating indicator (optional - don't fail if missing)
        generating_sel = self.sel("generating_indicator")
        if generating_sel:
            try:
                generating = await self.page.query_selector(generating_sel)
                if generating:
                    return "generating"
            except:
                pass
        
        # Check if send button is enabled (indicates ready for input)
        send_enabled = self.sel("send_button_enabled")
        if send_enabled:
            try:
                btn = await self.page.query_selector(send_enabled)
                if btn:
                    return "idle"
            except:
                pass
        
        # Check if there's a complete response (assistant message exists)
        assistant_sel = self.sel("assistant_message") or self.sel("message_container")
        if assistant_sel:
            try:
                containers = await self.page.query_selector_all(assistant_sel)
                if containers and len(containers) > 0:
                    return "complete"
            except:
                pass
        
        return "idle"  # Default assumption

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

        # workspace = Path(self.config.data["workspace_root"]).resolve()
        workspace = self.config.workspace_root
        sessions_dir = workspace / ".doit" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        self.session_dir = sessions_dir / project_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        try:

            # Check if we already have a context (browser might be open)
            if self.context:
                print("[BrowserController] Closing existing context...")
                await self.context.close()

            # Launch persistent context - this reuses existing profile if directory exists                            
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                channel="msedge",
                headless=self.headless,
                args=self.launch_args,
            )
            print(f"[BrowserController] Persistent context launched with user data dir: {self.session_dir}")

        except Exception as exc:
            print(f"[open_chat_session] Failed to launch persistent context: {exc}")
            raise EdgeUnavailableError(
                "Failed to launch Edge persistent context."
            ) from exc

        # Get or create page
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout_ms)

        print(f"[BrowserController] Page ready, URL: {self.page.url}")
        return self.page

    async def close_session(self):
        """Close browser and Playwright, but preserve session files."""
        try:
            if self.context:
                await self.context.close()
                print("[BrowserController] Context closed (session preserved)")
        finally:
            if self.playwright:
                await self.playwright.stop()

        self.context = None
        self.page = None
        self.playwright = None
        #  Do NOT delete self.session_dir - it contains the persistent profile
        # self.session_dir = None

    # -----------------------------
    # Allowlist
    # -----------------------------
    def _is_url_allowed(self, url: str) -> bool:
        allowlist = []

        # workspace = Path(self.config.data["workspace_root"]).resolve()
        workspace = self.config.workspace_root
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

    def validate_selectors(self) -> List[str]:
        """
        Validate that required selectors exist.
        
        Returns:
            List of missing selector keys
        """
        required = [
            'new_chat_button',
            'send_button_enabled',
            'prompt_input',
            'message_container',
            'generating_indicator'
        ]
        
        missing = []
        for key in required:
            if not self.sel(key):
                missing.append(key)
        
        if missing:
            print(f"[BrowserController] Warning: Missing selectors: {missing}")
        
        return missing

    def get_selector_with_fallback(self, key: str, fallback: str = None) -> Optional[str]:
        """
        Get selector with fallback options.
        
        Tries:
        1. Configured selector for current URL
        2. Provided fallback
        3. Common patterns
        """
        selector = self.sel(key)
        
        if selector:
            return selector
        
        if fallback:
            return fallback
        
        # Common fallback patterns
        common_fallbacks = {
            'new_chat_button': ['button:has-text("New chat")', '[aria-label="New chat"]'],
            'send_button_enabled': ['button[type="submit"]:not([disabled])', 'button.send:enabled'],
            'prompt_input': ['textarea', '[contenteditable="true"]', 'input[type="text"]'],
            'message_container': ['.message', '[role="article"]', '.assistant-message'],
            'generating_indicator': ['.loading', '.spinner', '[aria-label="Loading"]'],
        }
        
        fallbacks = common_fallbacks.get(key, [])
        return fallbacks[0] if fallbacks else None

    def _load_selectors_for_url(self, url: str):
        """Load selectors for the current URL domain."""
        print(f"*** _load_selectors_for_url called with {url} ***")
        self.selectors = self.config.get_selectors_for_url(url)
        print(f"*** Loaded {len(self.selectors)} selectors ***")
        print(f"[DEBUG] Selectors loaded: {list(self.selectors.keys())}")
        
        # Also update the required keys mapping for backward compatibility
        # Map 'send_enabled' to 'send_button_enabled' if needed
        if 'send_button_enabled' in self.selectors and 'send_enabled' not in self.selectors:
            self.selectors['send_enabled'] = self.selectors['send_button_enabled']
            print(f"[DEBUG] Added 'send_enabled' alias for 'send_button_enabled'")

    async def navigate(self, url: str, wait_until="networkidle"):
        """Navigate to URL and load domain-specific selectors."""
        if not self.page:
            raise BrowserError("Session not open.")
        
        if not self._is_url_allowed(url):
            raise AllowlistError(f"URL not allowed: {url}")
        
        # Navigate
        await self.page.goto(url, wait_until=wait_until, timeout=self.navigation_timeout_ms)
        
        # Load domain-specific selectors
        from urllib.parse import urlparse
        parsed = urlparse(url)
        self.current_domain = parsed.netloc.replace('www.', '')
        self._load_selectors_for_url(url)

    async def wait_for_prompt_box(self, timeout_ms: int = 60000) -> bool:
        """Wait for the prompt input box to become visible."""
        selector = self.sel("prompt_input")
        if not selector:
            print("[wait_for_prompt_box] No prompt_input selector configured")
            return False
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout_ms)
            print("[wait_for_prompt_box] Prompt box found")
            return True
        except:
            print("[wait_for_prompt_box] Timeout waiting for prompt box")
            return False

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
        selector = self.sel('new_chat_button')
        if not selector:
            print(f"Warning: missing selector 'new_chat_button' for {self.current_domain}")
            if self.strict_selectors:
                raise BrowserError("Missing new_chat_button selector")
            return
        btn = await self.page.wait_for_selector(selector, timeout=self.timeout_ms)
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
        """
        Send a prompt to the chat interface.
        
        Critical selectors: prompt_input, send_button_enabled
        If missing: prints warning but does NOT exit (for initial testing)
        """
        if not self.page:
            raise BrowserError("Session not open.")

        prompt_sel = self.sel("prompt_input")
        if not prompt_sel:
            print(f"⚠️ CRITICAL WARNING: Selector 'prompt_input' missing for domain '{self.current_domain}'")
            print(f"   Cannot send prompt. Please add to .doit/selectors/{self.current_domain}.yaml")
            if self.strict_selectors:
                raise BrowserError(f"Missing required selector: prompt_input")
            return  # Exit early without sending

        send_enabled = self.sel("send_button_enabled")
        if not send_enabled:
            print(f"⚠️ CRITICAL WARNING: Selector 'send_button_enabled' missing for domain '{self.current_domain}'")
            print(f"   Cannot send prompt. Please add to .doit/selectors/{self.current_domain}.yaml")
            if self.strict_selectors:
                raise BrowserError(f"Missing required selector: send_button_enabled")
            return  # Exit early without sending

        # Fill prompt
        try:
            await self.page.focus(prompt_sel)
            await self.page.eval_on_selector(
                prompt_sel,
                "el => { el.innerText = arguments[0]; }",
                text,
            )
            print(f"✓ Prompt filled: {text[:50]}...")
        except Exception as e:
            print(f"⚠️ Failed to fill prompt: {e}")
            if self.strict_selectors:
                raise
            return

        # Upload files if needed
        if files:
            try:
                await self.upload_file(files)
                print(f"✓ Uploaded {len(files)} file(s)")
            except Exception as e:
                print(f"⚠️ File upload failed: {e}")
                # Continue anyway - prompt may still send

        # Click send button
        try:
            btn = await self.page.wait_for_selector(send_enabled, timeout=self.timeout_ms)
            await btn.click()
            print("✓ Send button clicked")
        except Exception as e:
            print(f"⚠️ Failed to click send button: {e}")
            if self.strict_selectors:
                raise
            return

        # Wait for generation to start
        await self._wait(200)

        # Wait for completion using status detection
        timeout = self.timeout_ms * 6  # 6x default timeout (e.g., 120 seconds)
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout / 1000:
            try:
                status = await self.get_status()
                if status in ("complete", "idle"):
                    print(f"✓ Response generation complete (status: {status})")
                    break
            except Exception as e:
                print(f"⚠️ Error checking status: {e}")
            await self._wait(1000)  # Check every second
        else:
            print(f"⚠️ Timeout waiting for response after {timeout/1000} seconds")

    # -----------------------------
    # File upload
    # -----------------------------
    async def upload_file(self, paths: List[str]):
        """Upload files using the web UI (optional feature)."""
        upload_btn_sel = self.sel("upload_button")
        if not upload_btn_sel:
            print(f"⚠️ Optional selector 'upload_button' missing for {self.current_domain}")
            print(f"   File upload will be skipped")
            return
        
        try:
            upload_btn = await self.page.wait_for_selector(upload_btn_sel, timeout=self.timeout_ms)
            await upload_btn.click()
        except Exception as e:
            print(f"⚠️ Could not click upload button: {e}")
            return
        
        attach_btn_sel = self.sel("attach_file_button")
        if not attach_btn_sel:
            print(f"⚠️ Optional selector 'attach_file_button' missing for {self.current_domain}")
            return
        
        try:
            attach_btn = await self.page.wait_for_selector(attach_btn_sel, timeout=self.timeout_ms)
            await attach_btn.click()
        except Exception as e:
            print(f"⚠️ Could not click attach button: {e}")
            return
        
        # Handle file chooser
        try:
            async with self.page.expect_file_chooser() as fc_info:
                pass  # The click already triggered the chooser
            file_chooser = await fc_info.value
            await file_chooser.set_files(paths)
            print(f"✓ Uploaded {len(paths)} file(s)")
        except Exception as e:
            print(f"⚠️ File chooser error: {e}")

    # -----------------------------
    # Extraction Modes (Option E)
    # -----------------------------
    async def extract_last_assistant_message(self) -> Optional[str]:
        """
        Extract the last assistant message from the conversation.
        
        Critical selector: message_container or assistant_message
        If missing: prints warning but returns None (does NOT exit)
        """
        # Try multiple possible selector keys for assistant messages
        selector = self.sel("assistant_message") or self.sel("message_container")
        
        if not selector:
            print(f"⚠️ WARNING: Neither 'assistant_message' nor 'message_container' selector configured")
            print(f"   for domain '{self.current_domain}'. Cannot extract responses.")
            print(f"   Please add to .doit/selectors/{self.current_domain}.yaml")
            return None
        
        try:
            containers = await self.page.query_selector_all(selector)
            if not containers:
                print(f"⚠️ No assistant messages found on page")
                return None
            
            # Get the last message
            last_message = containers[-1]
            text = await last_message.inner_text()
            
            if text and len(text.strip()) > 0:
                return text.strip()
            else:
                print(f"⚠️ Assistant message found but empty")
                return None
                
        except Exception as e:
            print(f"⚠️ Failed to extract assistant message: {e}")
            return None

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
class BrowserController:
    def __init__(self, config, permissions, logger):
        self.config = config
        self.permissions = permissions
        self.logger = logger
        self.browser = None
        self.page = None

    def ensure_running(self):
        """Launch Edge with persistent profile."""
        pass

    def open_chat_session(self, project_name: str | None):
        """Open or restore a conversation."""
        pass

    def send_prompt(self, text: str, files=None) -> str:
        """Send prompt, wait for response, return text."""
        pass

    def navigate(self, url: str):
        """Navigate to URL after allowlist checks."""
        pass

    def fetch_page_text(self, url: str) -> str:
        """Extract main text."""
        return ""

    def fetch_youtube_transcript(self, url: str) -> str:
        """Extract transcript."""
        return ""

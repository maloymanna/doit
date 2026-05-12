# src/doit/config.py [v2.0]
"""Configuration management for doit workspace."""
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field
from datetime import datetime
import warnings

class ConfigError(Exception):
    """Configuration related errors."""
    pass

@dataclass
class WorkspaceConfig:
    name: str
    created: str
    root_path: Optional[Path] = None
    @classmethod
    def from_dict(cls, data: Dict[str, Any], root_path: Path) -> 'WorkspaceConfig':
        return cls(
            name=data.get('name', 'default-workspace'),
            created=data.get('created', datetime.now().isoformat()),
            root_path=root_path
        )

@dataclass
class AutonomyConfig:
    mode: int = 0
    global_max_iterations: int = 10
    require_approval_for: list = field(default_factory=lambda: ['delete', 'git_push'])
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutonomyConfig':
        return cls(
            mode=data.get('mode', 0),
            global_max_iterations=data.get('global_max_iterations', 10),
            require_approval_for=data.get('require_approval_for', ['delete', 'git_push'])
        )
    def validate(self) -> None:
        if self.mode not in [0, 1, 2]:
            raise ConfigError(f"Invalid autonomy mode: {self.mode}. Must be 0, 1, or 2")
        if self.global_max_iterations < 1:
            raise ConfigError(f"Invalid max iterations: {self.global_max_iterations}. Must be >= 1")

@dataclass
class BrowserConfig:
    default_model: str = "GPT-5.1"
    completion_timeout_ms: int = 120000
    retry_attempts: int = 3
    screenshot_on_error: bool = True
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrowserConfig':
        return cls(
            default_model=data.get('default_model', 'GPT-5.1'),
            completion_timeout_ms=data.get('completion_timeout_ms', 120000),
            retry_attempts=data.get('retry_attempts', 3),
            screenshot_on_error=data.get('screenshot_on_error', True)
        )

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "text"
    max_log_size_mb: int = 100
    keep_logs_days: int = 30
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        return cls(
            level=data.get('level', 'INFO').upper(),
            format=data.get('format', 'text'),
            max_log_size_mb=data.get('max_log_size_mb', 100),
            keep_logs_days=data.get('keep_logs_days', 30)
        )

@dataclass
class GitConfig:
    default_branch: str = "main"
    auto_commit_on_summary: bool = False
    require_commit_message: bool = True
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GitConfig':
        return cls(
            default_branch=data.get('default_branch', 'main'),
            auto_commit_on_summary=data.get('auto_commit_on_summary', False),
            require_commit_message=data.get('require_commit_message', True)
        )

@dataclass
class PlaywrightSelectorConfig:
    data: Dict[str, str] = field(default_factory=dict)
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        value = self.data.get(key, default)
        if value and ',' in value:
            return value.split(',')[0].strip()
        return value
    def get_all(self, key: str) -> list:
        value = self.data.get(key)
        if not value: return []
        return [s.strip() for s in value.split(',')]

@dataclass
class PlaywrightConfig:
    channel: str = "msedge"
    headless: bool = False
    slow_mo: int = 0
    viewport: Dict[str, int] = field(default_factory=lambda: {'width': 1280, 'height': 900})
    timeout_ms: int = 20000
    navigation_timeout_ms: int = 30000
    launch_args: list = field(default_factory=list)
    selectors: PlaywrightSelectorConfig = field(default_factory=PlaywrightSelectorConfig)
    strict_validation: bool = False
    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict_validation: bool = False) -> 'PlaywrightConfig':
        browser_data = data.get('browser', {})
        selectors_data = data.get('selectors', {})
        return cls(
            channel=browser_data.get('channel', 'msedge'),
            headless=browser_data.get('headless', False),
            slow_mo=browser_data.get('slow_mo', 0),
            viewport=browser_data.get('viewport', {'width': 1280, 'height': 900}),
            timeout_ms=browser_data.get('timeout_ms', 20000),
            navigation_timeout_ms=browser_data.get('navigation_timeout_ms', 30000),
            launch_args=browser_data.get('launch_args', []),
            selectors=PlaywrightSelectorConfig(selectors_data),
            strict_validation=strict_validation
        )
    def validate(self) -> None:
        if self.channel not in ['msedge', 'chromium', 'firefox']:
            raise ConfigError(f"Unsupported browser channel: {self.channel}")
        if self.viewport.get('width', 0) <= 0 or self.viewport.get('height', 0) <= 0:
            raise ConfigError(f"Invalid viewport dimensions: {self.viewport}")
        if self.strict_validation:
            required = ['new_chat_button', 'send_enabled', 'prompt_input', 'message_container', 'generating_indicator']
            for s in required:
                if not self.selectors.get(s):
                    raise ConfigError(f"Required selector missing: {s}")

class Config:
    DEFAULT_CONFIG = {
        'autonomy': {'mode': 0, 'global_max_iterations': 10, 'require_approval_for': ['delete', 'git_push', 'git_reset_hard', 'recursive_delete']},
        'browser': {'default_model': 'GPT-5.1', 'completion_timeout_ms': 120000, 'retry_attempts': 3, 'screenshot_on_error': True},
        'logging': {'level': 'INFO', 'format': 'text', 'max_log_size_mb': 100, 'keep_logs_days': 30},
        'git': {'default_branch': 'main', 'auto_commit_on_summary': False, 'require_commit_message': True}
    }

    def __init__(self, workspace_root: Path):
        if workspace_root is None:
            raise ValueError("Workspace path must be provided")
        self.workspace_root = Path(workspace_root).resolve()
        self.doit_dir = self.workspace_root / '.doit'
        if not self.doit_dir.exists():
            raise ConfigError(f"Not a valid doit workspace: {self.workspace_root}\nMissing .doit/ directory.")
        
        self.config_path = self.doit_dir / 'config.yaml'
        self.playwright_config_path = self.doit_dir / 'playwright_config.yaml'
        self._config_data = None
        self._playwright_config = None
        self.load()

    def get_selectors_for_url(self, url: str) -> dict:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        selector_file = self.doit_dir / 'selectors' / f"{domain}.yaml"
        if not selector_file.exists(): return {}
        with open(selector_file, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('selectors', {}) if data else {}

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f) or {}
        else:
            self._config_data = {}
        self._config_data['workspace_root'] = str(self.workspace_root)
        
        if self.playwright_config_path.exists():
            with open(self.playwright_config_path, 'r') as f:
                pw_data = yaml.safe_load(f)
                strict = self._config_data.get('browser', {}).get('strict_selector_validation', False)
                self._playwright_config = PlaywrightConfig.from_dict(pw_data, strict_validation=strict)
        else:
            self._playwright_config = PlaywrightConfig()
        self.validate()

    def validate(self) -> None:
        self.autonomy.validate()
        if self._playwright_config: self._playwright_config.validate()

    @property
    def data(self) -> Dict[str, Any]: return self._config_data
    @property
    def autonomy(self) -> AutonomyConfig: return AutonomyConfig.from_dict(self._config_data.get('autonomy', {}))
    @property
    def browser(self) -> BrowserConfig: return BrowserConfig.from_dict(self._config_data.get('browser', {}))
    @property
    def logging(self) -> LoggingConfig: return LoggingConfig.from_dict(self._config_data.get('logging', {}))
    @property
    def git(self) -> GitConfig: return GitConfig.from_dict(self._config_data.get('git', {}))
    @property
    def playwright(self) -> PlaywrightConfig: return self._playwright_config

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config_data
        for k in keys:
            if isinstance(value, dict): value = value.get(k)
            else: return default
            if value is None: return default
        return value

    def get_workflow_hints(self, url: str) -> Dict[str, Any]:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        selector_file = self.doit_dir / 'selectors' / f"{domain}.yaml"
        if selector_file.exists():
            with open(selector_file, 'r') as f:
                return yaml.safe_load(f).get('workflow', {})
        return {}

if __name__ == "__main__":
    c = Config(Path("."))
    print("Has get_selectors_for_url:", hasattr(c, "get_selectors_for_url"))
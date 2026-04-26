"""Configuration management for doit workspace."""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field
from datetime import datetime


class ConfigError(Exception):
    """Configuration related errors."""
    pass


@dataclass
class WorkspaceConfig:
    """Workspace configuration structure."""
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
    """Autonomy mode configuration."""
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
        """Validate autonomy configuration."""
        if self.mode not in [0, 1, 2]:
            raise ConfigError(f"Invalid autonomy mode: {self.mode}. Must be 0, 1, or 2")
        if self.global_max_iterations < 1:
            raise ConfigError(f"Invalid max iterations: {self.global_max_iterations}. Must be >= 1")


@dataclass
class BrowserConfig:
    """Browser configuration."""
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
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    max_log_size_mb: int = 100
    keep_logs_days: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        return cls(
            level=data.get('level', 'INFO'),
            format=data.get('format', 'json'),
            max_log_size_mb=data.get('max_log_size_mb', 100),
            keep_logs_days=data.get('keep_logs_days', 30)
        )


@dataclass
class GitConfig:
    """Git configuration."""
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
    """Playwright selectors configuration."""
    data: Dict[str, str] = field(default_factory=dict)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get selector with fallback handling for comma-separated values."""
        value = self.data.get(key, default)
        if value and ',' in value:
            # Return first non-empty selector for now, actual implementation
            # will try multiple selectors
            return value.split(',')[0].strip()
        return value
    
    def get_all(self, key: str) -> list:
        """Get all possible selectors for a key (for fallback)."""
        value = self.data.get(key)
        if not value:
            return []
        return [s.strip() for s in value.split(',')]


@dataclass
class PlaywrightConfig:
    """Playwright browser configuration."""
    channel: str = "msedge"
    headless: bool = False
    slow_mo: int = 0
    viewport: Dict[str, int] = field(default_factory=lambda: {'width': 1280, 'height': 900})
    timeout_ms: int = 20000
    navigation_timeout_ms: int = 30000
    launch_args: list = field(default_factory=list)
    selectors: PlaywrightSelectorConfig = field(default_factory=PlaywrightSelectorConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaywrightConfig':
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
            selectors=PlaywrightSelectorConfig(selectors_data)
        )
    
    def validate(self) -> None:
        """Validate browser configuration."""
        if self.channel not in ['msedge', 'chromium', 'firefox']:
            raise ConfigError(f"Unsupported browser channel: {self.channel}")
        if self.viewport.get('width', 0) <= 0 or self.viewport.get('height', 0) <= 0:
            raise ConfigError(f"Invalid viewport dimensions: {self.viewport}")
        
        # Required selectors
        required_selectors = [
            'new_chat_button', 'send_enabled', 'prompt_input',
            'message_container', 'generating_indicator'
        ]
        for selector in required_selectors:
            if not self.selectors.get(selector):
                raise ConfigError(f"Required selector missing: {selector}")


class Config:
    """
    Configuration manager for doit workspace.
    
    Loads configuration from:
    1. Defaults (hardcoded)
    2. User config (~/.doit/config.yaml)
    3. Workspace config (workspace_root/.doit/config.yaml)
    """
    
    DEFAULT_CONFIG = {
        'autonomy': {
            'mode': 0,
            'global_max_iterations': 10,
            'require_approval_for': ['delete', 'git_push', 'git_reset_hard', 'recursive_delete']
        },
        'browser': {
            'default_model': 'GPT-5.1',
            'completion_timeout_ms': 120000,
            'retry_attempts': 3,
            'screenshot_on_error': True
        },
        'logging': {
            'level': 'INFO',
            'format': 'json',
            'max_log_size_mb': 100,
            'keep_logs_days': 30
        },
        'git': {
            'default_branch': 'main',
            'auto_commit_on_summary': False,
            'require_commit_message': True
        }
    }
    
    def __init__(self, workspace_root: Path):
        """
        Initialize configuration for a workspace.
        
        Args:
            workspace_root: Path to workspace root directory
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.doit_dir = self.workspace_root / '.doit'
        self.config_path = self.doit_dir / 'config.yaml'
        self.playwright_config_path = self.doit_dir / 'playwright_config.yaml'
        
        self._config_data = None
        self._playwright_config = None
        
        # Load configurations
        self.load()
    
    def load(self) -> None:
        """Load all configurations from workspace."""
        # Load main config
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f)
        else:
            self._config_data = {}
        
        # Load playwright config
        if self.playwright_config_path.exists():
            with open(self.playwright_config_path, 'r') as f:
                playwright_data = yaml.safe_load(f)
                self._playwright_config = PlaywrightConfig.from_dict(playwright_data)
        else:
            # Create default playwright config?
            self._playwright_config = PlaywrightConfig()
        
        # Validate configurations
        self.validate()
    
    def validate(self) -> None:
        """Validate all configurations."""
        # Validate autonomy
        autonomy = self.autonomy
        if autonomy.mode not in [0, 1, 2]:
            raise ConfigError(f"Invalid autonomy mode: {autonomy.mode}")
        
        # Validate playwright config
        if self._playwright_config:
            self._playwright_config.validate()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get raw configuration data."""
        return self._config_data
    
    @property
    def autonomy(self) -> AutonomyConfig:
        """Get autonomy configuration."""
        return AutonomyConfig.from_dict(self._config_data.get('autonomy', {}))
    
    @property
    def browser(self) -> BrowserConfig:
        """Get browser configuration."""
        return BrowserConfig.from_dict(self._config_data.get('browser', {}))
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return LoggingConfig.from_dict(self._config_data.get('logging', {}))
    
    @property
    def git(self) -> GitConfig:
        """Get git configuration."""
        return GitConfig.from_dict(self._config_data.get('git', {}))
    
    @property
    def playwright(self) -> PlaywrightConfig:
        """Get playwright configuration."""
        return self._playwright_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get nested configuration value by dot notation."""
        keys = key.split('.')
        value = self._config_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def save_main_config(self) -> None:
        """Save main configuration to file."""
        self.doit_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self._config_data, f, default_flow_style=False)
    
    def save_playwright_config(self) -> None:
        """Save playwright configuration to file."""
        self.doit_dir.mkdir(parents=True, exist_ok=True)
        playwright_dict = {
            'browser': {
                'channel': self._playwright_config.channel,
                'headless': self._playwright_config.headless,
                'slow_mo': self._playwright_config.slow_mo,
                'viewport': self._playwright_config.viewport,
                'timeout_ms': self._playwright_config.timeout_ms,
                'launch_args': self._playwright_config.launch_args
            },
            'selectors': self._playwright_config.selectors.data
        }
        with open(self.playwright_config_path, 'w') as f:
            yaml.dump(playwright_dict, f, default_flow_style=False)
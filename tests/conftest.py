"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
import yaml


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def valid_workspace(temp_workspace):
    """Create a valid workspace with .doit and all required configs."""
    # Create .doit directory
    doit_dir = temp_workspace / '.doit'
    doit_dir.mkdir(parents=True)
    
    # Create main config
    config_data = {
        'autonomy': {'mode': 0},
        'browser': {'default_model': 'GPT-5.1'}
    }
    with open(doit_dir / 'config.yaml', 'w') as f:
        yaml.dump(config_data, f)
    
    # Create playwright config with ALL required selectors
    playwright_data = {
        'selectors': {
            'new_chat_button': 'button.new-chat',
            'send_enabled': 'button.send:not([disabled])',
            'prompt_input': '[contenteditable="true"]',
            'message_container': '.assistant-message',
            'generating_indicator': '.generating'
        }
    }
    with open(doit_dir / 'playwright_config.yaml', 'w') as f:
        yaml.dump(playwright_data, f)
    
    # Create allowlist
    with open(doit_dir / 'allowlist.txt', 'w') as f:
        f.write("# Allowed URLs\n")
        f.write("https://usegpt.myorg\n")
        f.write("https://github.com/*\n")
    
    # Create workspace directories
    (temp_workspace / 'projects').mkdir()
    (temp_workspace / 'readonly_input').mkdir()
    
    return temp_workspace


@pytest.fixture
def sample_config_dict():
    """Return a sample configuration dictionary."""
    return {
        'autonomy': {
            'mode': 1,
            'global_max_iterations': 5,
            'require_approval_for': ['delete', 'push']
        },
        'browser': {
            'default_model': 'GPT-4',
            'completion_timeout_ms': 60000
        },
        'logging': {
            'level': 'DEBUG',
            'format': 'json'
        }
    }
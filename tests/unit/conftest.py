"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
import yaml


@pytest.fixture
def sample_workspace():
    """Create a sample workspace with basic configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create .doit directory
        doit_dir = workspace / '.doit'
        doit_dir.mkdir()
        
        # Create basic config
        config = {
            'autonomy': {'mode': 0},
            'browser': {'default_model': 'GPT-5.1'}
        }
        with open(doit_dir / 'config.yaml', 'w') as f:
            yaml.dump(config, f)
        
        # Create playwright config
        playwright_config = {
            'browser': {'channel': 'msedge', 'headless': False},
            'selectors': {
                'new_chat_button': 'button.new-chat',
                'send_enabled': 'button.send:not([disabled])',
                'prompt_input': '[contenteditable="true"]',
                'message_container': '.assistant-message',
                'generating_indicator': '.generating'
            }
        }
        with open(doit_dir / 'playwright_config.yaml', 'w') as f:
            yaml.dump(playwright_config, f)
        
        # Create allowlist
        with open(doit_dir / 'allowlist.txt', 'w') as f:
            f.write("# Allowed URLs\n")
            f.write("https://usegpt.myorg\n")
            f.write("https://github.com/*\n")
        
        # Create projects directory
        (workspace / 'projects').mkdir()
        
        # Create readonly_input directory
        (workspace / 'readonly_input').mkdir()
        
        yield workspace


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
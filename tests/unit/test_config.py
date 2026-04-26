"""Unit tests for configuration management."""

import yaml
import tempfile
from pathlib import Path
import pytest
from datetime import datetime

from doit.config import Config, ConfigError, AutonomyConfig, PlaywrightConfig


class TestConfigLoading:
    """Test configuration loading from workspace."""
    
    def test_config_loading_from_workspace(self, temp_workspace):
        """Should load config from workspace_root/.doit/config.yaml"""
        # Create workspace with config
        config_content = {
            'autonomy': {'mode': 1},
            'browser': {'default_model': 'GPT-4'}
        }
        config_file = temp_workspace / '.doit' / 'config.yaml'
        config_file.parent.mkdir(parents=True)
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        # Load config
        config = Config(temp_workspace)
        
        # Verify
        assert config.autonomy.mode == 1
        assert config.browser.default_model == 'GPT-4'
    
    def test_config_validation(self, temp_workspace):
        """Should validate required fields and types"""
        # Create invalid config
        config_content = {'autonomy': {'mode': 5}}  # Invalid mode
        config_file = temp_workspace / '.doit' / 'config.yaml'
        config_file.parent.mkdir(parents=True)
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        # Should raise error
        with pytest.raises(ConfigError):
            Config(temp_workspace)
    
    def test_config_merging(self, temp_workspace):
        """Should properly merge default, user, and workspace configs"""
        # Create workspace config
        workspace_config = {'autonomy': {'mode': 2}}
        config_file = temp_workspace / '.doit' / 'config.yaml'
        config_file.parent.mkdir(parents=True)
        with open(config_file, 'w') as f:
            yaml.dump(workspace_config, f)
        
        config = Config(temp_workspace)
        
        # Should use workspace mode but default for other values
        assert config.autonomy.mode == 2
        assert config.autonomy.global_max_iterations == 10  # Default
    
    def test_workspace_discovery(self, temp_workspace):
        """Should find .doit directory from subdirectory"""
        # Create workspace with .doit
        (temp_workspace / '.doit').mkdir(parents=True)
        
        # Create config in subdirectory
        subdir = temp_workspace / 'subdir' / 'nested'
        subdir.mkdir(parents=True)
        
        # Config should find workspace by looking upward
        config = Config(subdir)
        assert config.workspace_root == temp_workspace


class TestAutonomyConfig:
    """Test autonomy configuration."""
    
    def test_autonomy_mode_0_validation(self):
        """Mode 0 should be valid"""
        config = AutonomyConfig(mode=0)
        config.validate()
        assert config.mode == 0
    
    def test_autonomy_mode_1_validation(self):
        """Mode 1 should be valid"""
        config = AutonomyConfig(mode=1)
        config.validate()
        assert config.mode == 1
    
    def test_autonomy_mode_2_validation(self):
        """Mode 2 should be valid"""
        config = AutonomyConfig(mode=2)
        config.validate()
        assert config.mode == 2
    
    def test_invalid_autonomy_mode(self):
        """Should reject invalid mode values"""
        config = AutonomyConfig(mode=99)
        with pytest.raises(ConfigError):
            config.validate()
    
    def test_autonomy_approval_list(self):
        """Should maintain approval requirements list"""
        config = AutonomyConfig(require_approval_for=['delete', 'git_push'])
        assert 'delete' in config.require_approval_for
        assert 'git_push' in config.require_approval_for


class TestPlaywrightConfig:
    """Test Playwright configuration."""
    
    def test_playwright_config_from_dict(self):
        """Should create config from dictionary"""
        data = {
            'browser': {
                'channel': 'msedge',
                'headless': True,
                'viewport': {'width': 1920, 'height': 1080}
            },
            'selectors': {
                'new_chat_button': 'button.new-chat',
                'send_enabled': 'button.send'
            }
        }
        
        config = PlaywrightConfig.from_dict(data)
        
        assert config.channel == 'msedge'
        assert config.headless == True
        assert config.viewport['width'] == 1920
        assert config.selectors.get('new_chat_button') == 'button.new-chat'
    
    def test_playwright_selector_fallback(self):
        """Should handle multiple selectors with fallback"""
        data = {
            'selectors': {
                'new_chat_button': 'button.new-chat, [aria-label="New chat"], button:has-text("New chat")'
            }
        }
        
        config = PlaywrightConfig.from_dict(data)
        
        # Should return the first selector
        assert config.selectors.get('new_chat_button') == 'button.new-chat'
        
        # Get all selectors for fallback
        all_selectors = config.selectors.get_all('new_chat_button')
        assert len(all_selectors) == 3
        assert 'button:has-text("New chat")' in all_selectors
    
    def test_playwright_validation_required_selectors(self):
        """Should validate required selectors exist"""
        data = {
            'selectors': {
                'new_chat_button': 'button.new-chat'
                # Missing send_enabled, prompt_input, etc.
            }
        }
        
        config = PlaywrightConfig.from_dict(data)
        
        with pytest.raises(ConfigError):
            config.validate()
    
    def test_playwright_viewport_validation(self):
        """Should validate viewport dimensions"""
        data = {
            'browser': {
                'viewport': {'width': -100, 'height': -100}
            }
        }
        
        config = PlaywrightConfig.from_dict(data)
        
        with pytest.raises(ConfigError):
            config.validate()


class TestConfigGetters:
    """Test configuration property getters."""
    
    def test_get_nested_config(self, temp_workspace):
        """Should get nested config using dot notation"""
        config_content = {
            'browser': {
                'default_model': 'GPT-5.1',
                'timeout': 30000
            }
        }
        
        config_file = temp_workspace / '.doit' / 'config.yaml'
        config_file.parent.mkdir(parents=True)
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        config = Config(temp_workspace)
        
        assert config.get('browser.default_model') == 'GPT-5.1'
        assert config.get('browser.timeout') == 30000
        assert config.get('nonexistent.key', 'default') == 'default'
    
    def test_property_accessors(self, temp_workspace):
        """Should provide typed property accessors"""
        config = Config(temp_workspace)
        
        # Should return properly typed objects
        assert isinstance(config.autonomy, AutonomyConfig)
        assert isinstance(config.playwright, PlaywrightConfig)


# Fixtures
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace
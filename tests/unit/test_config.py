"""Unit tests for configuration management."""

import yaml
import tempfile
from pathlib import Path
import pytest
from datetime import datetime

from doit.config import Config, ConfigError, AutonomyConfig, PlaywrightConfig

class TestWorkspaceRequirements:
    """Tests for workspace directory requirements."""
    
    def test_workspace_must_be_explicitly_provided(self):
        """Should require explicit workspace path - no automatic discovery"""
        # This should fail - no workspace argument provided
        with pytest.raises(TypeError):
            Config()  # Missing required argument
    
    def test_workspace_without_doit_raises_error(self, temp_workspace):
        """Should raise error if workspace exists but has no .doit/"""
        # Create workspace directory but no .doit subdirectory
        workspace = temp_workspace / "some-workspace"
        workspace.mkdir()
        
        with pytest.raises(ConfigError) as exc_info:
            Config(workspace)
        
        assert "Not a valid doit workspace" in str(exc_info.value)
        assert "Missing .doit/ directory" in str(exc_info.value)
    
    def test_workspace_can_be_outside_project_root(self, temp_workspace):
        """Workspace can be anywhere - doesn't need to be near project root"""
        # Create workspace in a completely separate location
        workspace = temp_workspace / "remote-workspace"
        workspace.mkdir()
        
        # Create .doit directory
        (workspace / '.doit').mkdir()
        
        # Create minimal config
        config_file = workspace / '.doit' / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'autonomy': {'mode': 0}}, f)
        
        # This should work even though it's not in project root
        config = Config(workspace)
        assert config.workspace_root == workspace
        assert config.autonomy.mode == 0
    
    def test_workspace_separate_from_project(self):
        """Documentation test: Workspace should NOT be project root"""
        # Get actual project root (where this test file lives)
        test_file = Path(__file__).resolve()
        project_root = test_file.parent.parent.parent
        
        # This is just documentation - not an assertion
        # In real usage, workspace should be different
        print(f"\nNote: Project root is {project_root}")
        print("Workspace should be a different directory, e.g., ~/doit-workspace")

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
        """Should NOT traverse upward - workspace must be explicitly provided"""
        # Create workspace with .doit
        (temp_workspace / '.doit').mkdir(parents=True)
        
        # Create a subdirectory (this should NOT be considered a workspace)
        subdir = temp_workspace / 'subdir' / 'nested'
        subdir.mkdir(parents=True)
        
        # Using subdir should FAIL because it doesn't have .doit/
        with pytest.raises(ConfigError) as exc_info:
            Config(subdir)
        
        assert "Not a valid doit workspace" in str(exc_info.value)
        
        # Using actual workspace root should SUCCEED
        config = Config(temp_workspace)
        assert config.workspace_root == temp_workspace
        assert config.doit_dir == temp_workspace / '.doit'

    def test_workspace_without_doit(self, temp_workspace):
        """Should raise error if .doit doesn't exist"""
        # No .doit directory created
        with pytest.raises(ConfigError) as exc_info:
            Config(temp_workspace)
        
        assert "Missing .doit/ directory" in str(exc_info.value)

    def test_workspace_with_doit(self, temp_workspace):
        """Should work when .doit exists at workspace root"""
        # Create .doit directory
        (temp_workspace / '.doit').mkdir(parents=True)
        
        # This should succeed
        config = Config(temp_workspace)
        assert config.workspace_root == temp_workspace
        assert config.doit_dir == temp_workspace / '.doit'  

    def test_subdirectory_not_workspace(self, temp_workspace):
        """Should NOT treat subdirectory as workspace root"""
        # Create workspace with .doit at root
        (temp_workspace / '.doit').mkdir(parents=True)
        
        # Create a subdirectory
        subdir = temp_workspace / 'subdir' / 'nested'
        subdir.mkdir(parents=True)
        
        # Using subdir should FAIL because it doesn't have .doit/
        with pytest.raises(ConfigError) as exc_info:
            Config(subdir)
        
        assert "Not a valid doit workspace" in str(exc_info.value)
        assert "Missing .doit/ directory" in str(exc_info.value)              

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
        """Should raise ConfigError when required selectors missing in strict mode"""
        data = {
            'selectors': {
                'new_chat_button': 'button.new-chat'
                # Missing send_enabled, prompt_input, etc.
            },
            'strict_validation': True  # Enable strict mode
        }
        
        config = PlaywrightConfig.from_dict(data, strict_validation=True)
        
        # This should raise ConfigError when validate() is called
        with pytest.raises(ConfigError):
            config.validate()
    
    def test_playwright_validation_lenient_mode(self):
        """Should only warn (not raise) in lenient mode"""
        data = {
            'selectors': {
                'new_chat_button': 'button.new-chat'
                # Missing other selectors
            },
            'strict_validation': False  # Lenient mode
        }
        
        config = PlaywrightConfig.from_dict(data, strict_validation=False)
        
        # Should NOT raise an error
        import warnings
        with warnings.catch_warnings(record=True) as w:
            config.validate()
            # Should have warnings about missing selectors
            assert len(w) >= 1
            assert "Missing recommended selectors" in str(w[0].message)
    
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
    
    def test_get_nested_config(self, valid_workspace):
        """Should get nested config using dot notation"""
        # valid_workspace already has .doit and all configs
        config = Config(valid_workspace)
        
        # Update config with nested values for this test
        config_content = {
            'browser': {
                'default_model': 'GPT-5.1',
                'timeout': 30000
            }
        }
        with open(valid_workspace / '.doit' / 'config.yaml', 'w') as f:
            yaml.dump(config_content, f)
        
        # Reload config
        config.load()
        
        assert config.get('browser.default_model') == 'GPT-5.1'
        assert config.get('browser.timeout') == 30000
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_property_accessors(self, valid_workspace):
        """Should provide typed property accessors"""
        config = Config(valid_workspace)
        
        # Should return properly typed objects
        assert isinstance(config.autonomy, AutonomyConfig)
        assert isinstance(config.playwright, PlaywrightConfig)
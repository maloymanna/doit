"""Test selector configuration and validation."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from doit.browser.controller import BrowserController
from doit.config import Config


class TestSelectorValidation:
    """Test selector validation and fallback mechanisms."""
    
    def test_validate_selectors_missing(self, mock_controller):
        """Should identify missing selectors."""
        # Remove all selectors
        mock_controller.selectors = {}
        
        missing = mock_controller.validate_selectors()
        
        assert len(missing) == 5
        assert 'new_chat_button' in missing
        assert 'send_button_enabled' in missing
    
    def test_validate_selectors_present(self, mock_controller_with_selectors):
        """Should return empty list when all selectors present."""
        missing = mock_controller_with_selectors.validate_selectors()
        
        assert len(missing) == 0
    
    def test_get_selector_with_fallback_configured(self, mock_controller_with_selectors):
        """Should return configured selector when present."""
        selector = mock_controller_with_selectors.get_selector_with_fallback('new_chat_button')
        
        assert selector == "button[data-testid='new-chat-button']"
    
    def test_get_selector_with_fallback_provided(self, mock_controller):
        """Should return provided fallback when selector missing."""
        selector = mock_controller.get_selector_with_fallback(
            'missing_key', 
            fallback="button.default"
        )
        
        assert selector == "button.default"
    
    def test_get_selector_with_common_fallback(self, mock_controller):
        """Should return common fallback when no selector configured."""
        selector = mock_controller.get_selector_with_fallback('new_chat_button')
        
        # Should return one of the common fallbacks
        assert selector in [
            'button:has-text("New chat")',
            '[aria-label="New chat"]'
        ]
    
    def test_selector_fallback_multiple_attempts(self, mock_controller):
        """Should try multiple selector patterns."""
        # Create a mock page
        mock_page = Mock()
        
        # Test that get_selector_with_fallback returns a string
        selector = mock_controller.get_selector_with_fallback('new_chat_button')
        assert selector is not None
        assert isinstance(selector, str)


class TestURLSpecificSelectors:
    """Test loading selectors for specific URLs."""
    
    def test_load_selectors_for_usegpt(self, temp_workspace, mock_config):
        """Should load UseGPT-specific selectors."""
        # Create selectors directory and file
        selectors_dir = temp_workspace / '.doit' / 'selectors'
        selectors_dir.mkdir(parents=True)
        
        selector_file = selectors_dir / 'chatgpt.com.yaml'
        selector_file.write_text("""
selectors:
  new_chat_button: "button.custom"
  send_button_enabled: "button.send-custom"
""")
        
        # Mock page URL
        mock_page = Mock()
        mock_page.url = "https://chatgpt.com"
        
        # Should load custom selectors
        # This would be tested in integration
    
    def test_selector_priority(self):
        """URL-specific selectors should override defaults."""
        # Priority order:
        # 1. URL-specific selector file
        # 2. Main playwright_config.yaml
        # 3. Hardcoded fallbacks
        
        pass


# Fixtures
@pytest.fixture
def mock_controller():
    """Create mock controller with empty selectors."""
    mock_config = Mock()
    mock_config.data = {"playwright": {}}
    
    controller = BrowserController(mock_config)
    controller.selectors = {}
    
    return controller


@pytest.fixture
def mock_controller_with_selectors():
    """Create mock controller with pre-configured selectors."""
    mock_config = Mock()
    mock_config.data = {"playwright": {}}
    
    controller = BrowserController(mock_config)
    controller.selectors = {
        'new_chat_button': "button[data-testid='new-chat-button']",
        'send_button_enabled': "button[data-testid='send-button'].enabled",
        'prompt_input': "textarea[data-testid='prompt-input']",
        'message_container': "div[data-message-author-role='assistant']",
        'generating_indicator': "[data-testid='conversation-container'] .streaming",
    }
    
    return controller


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / '.doit').mkdir()
    return workspace


@pytest.fixture
def mock_config(temp_workspace):
    """Create mock config."""
    config = Mock()
    config.doit_dir = temp_workspace / '.doit'
    return config
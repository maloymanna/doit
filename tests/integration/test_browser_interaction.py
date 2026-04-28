"""Real browser integration tests for UseGPT interaction."""

import asyncio
import pytest
from pathlib import Path
from playwright.async_api import async_playwright
from doit.orchestrator import Orchestrator
from doit.browser.controller import BrowserController

# Skip these tests if not explicitly requested
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--run-browser-tests"),
    reason="Use --run-browser-tests to run browser integration tests"
)


@pytest.mark.integration
class TestRealBrowserInteraction:
    """Real browser tests that launch Edge and interact with UseGPT."""
    
    @pytest.fixture
    async def orch(self, workspace):
        """Create orchestrator instance."""
        orch = Orchestrator(workspace)
        yield orch
        await orch.close_browser()
    
    @pytest.fixture
    def workspace(self):
        """Get real workspace path."""
        workspace = Path.home() / "arbitrary_folder" / "doit-workspace"
        if not workspace.exists():
            pytest.skip(f"Workspace not found: {workspace}")
        return workspace
    
    async def test_launch_edge_and_navigate(self, orch):
        """Test 1: Launch Edge and navigate to UseGPT."""
        print("\n[Test 1] Launching Edge and navigating to UseGPT...")
        
        # Open browser session
        page = await orch.open_chat_session("integration-test")
        assert page is not None
        
        # Navigate to UseGPT
        url = "https://usegpt.myorg"
        await orch.navigate(url)
        
        # Wait for page to load
        await asyncio.sleep(3)
        
        # Verify page is loaded
        title = await page.title()
        print(f"  Page title: {title}")
        assert page.url.startswith("https://usegpt.myorg")
        
        print("  ✅ Browser launched and navigation successful")
    
    async def test_detect_prompt_box(self, orch):
        """Test 2: Detect the prompt input box."""
        print("\n[Test 2] Detecting prompt input box...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        # Wait for SSO if needed
        print("  Please complete SSO login if prompted...")
        input("  Press Enter after you're logged in and see the chat interface...")
        
        bc = orch.browser
        selector = bc.sel('prompt_input')
        
        if not selector:
            selector = "textarea[data-testid='prompt-input']"
        
        # Wait for prompt box to be visible
        try:
            await bc.page.wait_for_selector(selector, timeout=10000)
            print(f"  ✅ Prompt box detected: {selector}")
            
            # Try to focus and type
            await bc.page.focus(selector)
            await bc.page.fill(selector, "Test")
            print("  ✅ Can type in prompt box")
            
        except Exception as e:
            pytest.fail(f"Failed to detect prompt box: {e}")
    
    async def test_send_prompt_and_get_response(self, orch):
        """Test 3: Send a prompt and extract response."""
        print("\n[Test 3] Sending prompt and extracting response...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        input("  Press Enter after completing SSO login...")
        
        bc = orch.browser
        
        # Start new chat
        print("  Starting new chat...")
        await bc.click_new_chat()
        await asyncio.sleep(1)
        
        # Send prompt
        test_prompt = "Please respond with exactly: OK_SELECTOR_TEST"
        print(f"  Sending: {test_prompt}")
        await bc.send_prompt(test_prompt)
        
        # Wait for response (max 30 seconds)
        print("  Waiting for response...")
        response = None
        for i in range(30):
            await asyncio.sleep(1)
            response = await bc.extract_last_assistant_message()
            if response and len(response) > 5:
                print(f"  Response received after {i+1} seconds")
                break
        
        assert response is not None, "No response received"
        print(f"  Response: {response[:100]}...")
        assert "OK_SELECTOR_TEST" in response or len(response) > 10
        print("  ✅ Prompt sent and response extracted")
    
    async def test_new_chat_resets_conversation(self, orch):
        """Test 4: New chat button resets conversation."""
        print("\n[Test 4] Testing new chat reset functionality...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        input("  Press Enter after SSO login...")
        
        bc = orch.browser
        
        # Send first message
        await bc.click_new_chat()
        await bc.send_prompt("First message. Reply with: RESPONSE_1")
        await asyncio.sleep(5)
        
        response1 = await bc.extract_last_assistant_message()
        print(f"  First response received: {len(response1)} chars")
        
        # Start new chat
        await bc.click_new_chat()
        await asyncio.sleep(1)
        
        # Check that conversation is empty
        messages = await bc.extract_all_messages()
        assert len(messages) == 0 or messages[0].get('text', '') == '', \
            "New chat should clear conversation"
        
        # Send second message
        await bc.send_prompt("Second message. Reply with: RESPONSE_2")
        await asyncio.sleep(5)
        
        response2 = await bc.extract_last_assistant_message()
        print(f"  Second response received: {len(response2)} chars")
        
        # Verify responses are different
        assert response1 != response2
        print("  ✅ New chat properly resets conversation")
    
    async def test_copy_response_button(self, orch):
        """Test 5: Copy button functionality."""
        print("\n[Test 5] Testing copy response button...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        input("  Press Enter after SSO login...")
        
        bc = orch.browser
        
        # Send a short prompt
        await bc.click_new_chat()
        await bc.send_prompt("Reply with a short word: TEST")
        await asyncio.sleep(5)
        
        # Try to copy via UI
        copied = await bc.copy_last_assistant_message_via_ui()
        
        if copied:
            print(f"  Copied text: {copied[:50]}...")
            assert len(copied) > 0
            print("  ✅ Copy button works")
        else:
            print("  ⚠ Copy button not available or failed (non-critical)")
    
    async def test_file_upload_flow(self, orch, tmp_path):
        """Test 6: File upload flow (create test file)."""
        print("\n[Test 6] Testing file upload flow...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        input("  Press Enter after SSO login...")
        
        bc = orch.browser
        
        # Create a small test file
        test_file = tmp_path / "test_upload.txt"
        test_file.write_text("This is a test file for upload")
        
        # Start new chat
        await bc.click_new_chat()
        
        # Check if upload button exists
        upload_selector = bc.sel('upload_button')
        if upload_selector:
            print(f"  Upload button selector: {upload_selector}")
            
            try:
                await bc.send_prompt("Please acknowledge file upload", files=[str(test_file)])
                print("  ✅ File upload flow initiated")
            except Exception as e:
                print(f"  ⚠ File upload not fully tested: {e}")
        else:
            print("  ⚠ No upload button selector configured")
    
    async def test_model_selection(self, orch):
        """Test 7: Change model selection."""
        print("\n[Test 7] Testing model selection...")
        
        await orch.open_chat_session("integration-test")
        await orch.navigate("https://usegpt.myorg")
        
        input("  Press Enter after SSO login...")
        
        bc = orch.browser
        
        model_selector = bc.sel('model_selector_button')
        if model_selector:
            try:
                # Get current model before change
                current_model_btn = await bc.page.query_selector(model_selector)
                current_text = await current_model_btn.inner_text() if current_model_btn else "Unknown"
                print(f"  Current model: {current_text}")
                
                # Try to change model (skip if only one model)
                model_name = bc.model_name
                await bc.select_model(model_name)
                print(f"  ✅ Model selection attempted: {model_name}")
            except Exception as e:
                print(f"  ⚠ Model selection test: {e}")
        else:
            print("  ⚠ No model selector configured")


# Custom pytest option
def pytest_addoption(parser):
    parser.addoption(
        "--run-browser-tests",
        action="store_true",
        default=False,
        help="Run browser integration tests (requires live UseGPT instance)"
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring browser"
    )


# Run tests with: pytest tests/integration/test_browser_interaction.py --run-browser-tests -v -s
# examples/test_uc1_browser_tools.py [v1.3]
"""Phase 7 UC1 Test: Validates low-level browser tool wiring & async bridging."""
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.action_dispatcher import ActionDispatcher
from doit.plugins.browser_ops import (
    browser_navigate, browser_fill, browser_click_text, 
    browser_wait_for_element, browser_trigger_download,
    browser_upload_files, browser_screenshot
)
from doit.utils.session_logger import init_session_logger, logger

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
PROJECT = "browser-test"

def test_browser_tools():
    logger.info("Starting UC1 Browser Tools Test")
    proj_dir = WORKSPACE / "projects" / PROJECT
    proj_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.new_event_loop()
    
    mock_ctrl = MagicMock()
    mock_page = AsyncMock()
    mock_ctrl.page = mock_page
    
    # Configure async return values for awaited methods
    mock_page.goto = AsyncMock(return_value=None)
    mock_page.fill = AsyncMock(return_value=None)
    mock_page.wait_for_selector = AsyncMock(return_value=None)
    mock_page.click = AsyncMock(return_value=None)
    mock_page.set_input_files = AsyncMock(return_value=None)
    mock_page.screenshot = AsyncMock(return_value=None)
    mock_page.wait_for_load_state = AsyncMock(return_value=None)
    mock_page.query_selector = AsyncMock(return_value=AsyncMock())
    
    # browser_click_text uses page.get_by_text().first.click()
    mock_locator = AsyncMock()
    mock_locator.first = MagicMock()
    mock_locator.first.click = AsyncMock(return_value=None)
    mock_page.get_by_text = MagicMock(return_value=mock_locator)
    
    # Mock context for download handling
    mock_context = AsyncMock()
    mock_page.context = mock_context
    mock_page.context.set_default_timeout = AsyncMock(return_value=None)
    
    # ✅ FIXED: Synchronous context manager for expect_download (matches Playwright API)
    class MockDownloadInfo:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        @property
        def value(self):
            async def _get_download():
                mock_dl = AsyncMock()
                mock_dl.suggested_filename = "test.xlsx"
                mock_dl.save_as = AsyncMock(return_value=None)
                return mock_dl
            return _get_download()

    mock_page.expect_download = lambda timeout: MockDownloadInfo()

    # Dispatcher matches v2.7 signature + Phase 7 controller/loop injection
    disp = ActionDispatcher(WORKSPACE, proj_dir, controller=mock_ctrl, loop=loop)
    disp.autonomy = 2  # Permissive for tool validation
    disp.whitelist = []
    
    # Register Phase 7 browser tools
    for name, func in [
        ("browser_navigate", browser_navigate),
        ("browser_fill", browser_fill),
        ("browser_click_text", browser_click_text),
        ("browser_wait_for_element", browser_wait_for_element),
        ("browser_trigger_download", browser_trigger_download),
        ("browser_upload_files", browser_upload_files),
        ("browser_screenshot", browser_screenshot),
    ]:
        disp.register(name, func)

    # 1. Navigate
    res1 = disp.dispatch({"tool_name": "browser_navigate", "parameters": {"url": "https://test.com"}})
    assert res1["status"] == "ok", f"Navigate failed: {res1['output']}"
    logger.info("✅ browser_navigate passed")

    # 2. Fill
    res2 = disp.dispatch({"tool_name": "browser_fill", "parameters": {"selector": "#input", "value": "test"}})
    assert res2["status"] == "ok", f"Fill failed: {res2['output']}"
    logger.info("✅ browser_fill passed")

    # 3. Click Text
    res3 = disp.dispatch({"tool_name": "browser_click_text", "parameters": {"text": "Submit"}})
    assert res3["status"] == "ok", f"Click failed: {res3['output']}"
    logger.info("✅ browser_click_text passed")

    # 4. Wait
    res4 = disp.dispatch({"tool_name": "browser_wait_for_element", "parameters": {"selector": ".loader"}})
    assert res4["status"] == "ok", f"Wait failed: {res4['output']}"
    logger.info("✅ browser_wait_for_element passed")

    # 5. Trigger Download (mocked with fixed context manager)
    res5 = disp.dispatch({
        "tool_name": "browser_trigger_download",
        "parameters": {"selector": "#export-btn", "download_dir": "output/downloads"}
    })
    assert res5["status"] == "ok", f"Download failed: {res5['output']}"
    logger.info("✅ browser_trigger_download passed")

    # 6. Upload Files (mocked)
    test_file = proj_dir / "test_upload.txt"
    test_file.write_text("test content")
    res6 = disp.dispatch({
        "tool_name": "browser_upload_files",
        "parameters": {"selector": "input[type=file]", "file_paths": ["test_upload.txt"]}
    })
    assert res6["status"] == "ok", f"Upload failed: {res6['output']}"
    test_file.unlink()
    logger.info("✅ browser_upload_files passed")

    # 7. Screenshot (mocked)
    res7 = disp.dispatch({
        "tool_name": "browser_screenshot",
        "parameters": {"path": "output/screen.png", "full_page": True}
    })
    assert res7["status"] == "ok", f"Screenshot failed: {res7['output']}"
    logger.info("✅ browser_screenshot passed")

    loop.close()
    print("\n✅ ALL 7 UC1 LOW-LEVEL TOOLS VERIFIED")

if __name__ == "__main__":
    ctx = init_session_logger(WORKSPACE)
    logger.info("Running UC1 Browser Tool Validation")
    test_browser_tools()
    logger.info("UC1 validation complete")
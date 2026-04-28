#!/usr/bin/env python3
"""Quick test to verify browser launches with configurable workspace and URL."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

# ============================================================
# CONFIGURATION - CHANGE THESE FOR YOUR SETUP
# ============================================================

# Workspace path - where your .doit directory lives
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
# For Windows, use something like:
# WORKSPACE = Path("C:/Users/yourusername/doit-workspace").expanduser()

# Target LLM website URL
URL = "https://chatgpt.com"
# Alternative URLs for testing different AI websites:
# URL = "https://chatgpt.com"
# URL = "https://claude.ai"
# URL = "https://chat.qwen.ai"

# Project name for persistent session
PROJECT_NAME = "quick-test"

# Time to keep browser open after test (seconds)
KEEP_OPEN_SECONDS = 30

# ============================================================
# TEST CODE - NO NEED TO MODIFY BELOW
# ============================================================

async def test_browser_launch():
    """Test browser launch and navigation."""
    
    print("\n" + "="*60)
    print("QUICK BROWSER LAUNCH TEST")
    print("="*60)

    import os
    import getpass
    username = getpass.getuser()
    current_dir = Path.cwd()
    print(f"User: {username}")
    print(f"Current directory: {current_dir}")

    print(f"Workspace: {WORKSPACE}")
    print(f"Workspace exists: {WORKSPACE.exists()}")
    print(f".doit exists: {(WORKSPACE / '.doit').exists()}")
    print(f"Target URL: {URL}")
    print(f"Project: {PROJECT_NAME}")
    print()
    
    # Verify workspace exists
    if not WORKSPACE.exists():
        print(f"❌ ERROR: Workspace not found at: {WORKSPACE}")
        print("   Please update the WORKSPACE variable at the top of this script.")
        return
    
    # Verify .doit directory exists
    doit_dir = WORKSPACE / '.doit'
    if not doit_dir.exists():
        print(f"❌ ERROR: .doit directory not found in workspace")
        print(f"   Expected: {doit_dir}")
        print("   Please run 'doit init-workspace' first.")
        return
    
    # Verify selector file exists for the URL domain
    from urllib.parse import urlparse
    domain = urlparse(URL).netloc.replace('www.', '')
    selector_file = doit_dir / 'selectors' / f"{domain}.yaml"
    if not selector_file.exists():
        print(f"⚠️ WARNING: Selector file not found for domain '{domain}'")
        print(f"   Expected: {selector_file}")
        print("   Browser may not work correctly without selectors.")
        print(f"   Please create {selector_file}")
        print()
    else:
        print(f"✓ Selector file found: {selector_file}")
    
    orch = Orchestrator(WORKSPACE)
    
    try:
        print("\n1. Ensuring browser controller...")
        bc = await orch.ensure_browser()
        print(f"   ✓ Browser controller ready")

        print(f"   Timeout: {bc.timeout_ms}ms")
        print(f"   Navigation timeout: {bc.navigation_timeout_ms}ms")
        print(f"   Headless: {bc.headless}")
        
        print("\n2. Opening chat session...")
        page = await orch.open_chat_session(PROJECT_NAME)
        print(f"   ✓ Session opened for project '{PROJECT_NAME}'")
        
        print("\n3. Navigating to URL...")
        await orch.navigate(URL)
        print(f"   ✓ Navigated to {URL}")
        
        print("\n4. Waiting for manual SSO (if needed)...")
        print("   ┌" + "─" * 56 + "┐")
        print("   │ Please complete SSO login in the browser window.    │")
        print("   │ The browser will stay open for you to log in.       │")
        print("   └" + "─" * 56 + "┘")
        input("\n   Press Enter AFTER you've successfully logged in...")
        
        # Check if we can detect the prompt box
        bc = orch.browser
        prompt_selector = bc.sel('prompt_input')
        if prompt_selector:
            print(f"\n5. Checking prompt input box...")
            try:
                await bc.page.wait_for_selector(prompt_selector, timeout=5000)
                print(f"   ✓ Prompt box detected: {prompt_selector}")
            except Exception as e:
                print(f"   ⚠ Could not detect prompt box: {e}")
        else:
            print(f"\n⚠️ No 'prompt_input' selector configured for {domain}")
        
        print(f"\n✅ Browser launched successfully!")
        print(f"\nBrowser will stay open for {KEEP_OPEN_SECONDS} seconds...")
        await asyncio.sleep(KEEP_OPEN_SECONDS)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        await orch.close_browser()
        print("Done.")


async def test_with_custom_url(url: str):
    """Test browser launch with a custom URL (overrides the URL variable)."""
    
    # Temporarily override the URL
    global URL
    original_url = URL
    URL = url
    
    print(f"\nTesting with custom URL: {url}")
    await test_browser_launch()
    
    # Restore original URL
    URL = original_url


if __name__ == "__main__":
    import sys
    
    # Check if a custom URL was provided as command-line argument
    if len(sys.argv) > 1:
        asyncio.run(test_with_custom_url(sys.argv[1]))
    else:
        asyncio.run(test_browser_launch())
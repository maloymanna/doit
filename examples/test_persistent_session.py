#!/usr/bin/env python3
"""Test that persistent session is reused across runs."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "persistence-test"

async def first_run():
    """First run - should require SSO login."""
    print("\n" + "="*60)
    print("FIRST RUN - You will need to log in")
    print("="*60)
    
    orch = Orchestrator(WORKSPACE)
    try:
        await orch.open_chat_session(PROJECT)
        await orch.navigate(URL)
        
        print("\n🔐 Please complete SSO login in the browser...")
        input("Press Enter AFTER you have successfully logged in...")
        
        print("\n✅ Login complete. Session saved.")
        await asyncio.sleep(2)
    finally:
        await orch.close_browser()
        print("Browser closed. Session preserved.\n")

async def second_run():
    """Second run - should reuse session, no login needed."""
    print("\n" + "="*60)
    print("SECOND RUN - Should NOT require login")
    print("="*60)
    
    orch = Orchestrator(WORKSPACE)
    try:
        await orch.open_chat_session(PROJECT)
        await orch.navigate(URL)
        
        print("\n✅ Browser opened. You should already be logged in!")
        print("If you see the chat interface without logging in, persistence works.\n")
        
        await asyncio.sleep(10)  # Keep open for inspection
    finally:
        await orch.close_browser()

async def main():
    print("\n🧪 Testing Persistent Session Reuse")
    print("This will run the browser twice.\n")
    
    await first_run()
    
    print("\n" + "="*60)
    input("Press Enter to run the second session (should reuse login)...")
    
    await second_run()

if __name__ == "__main__":
    asyncio.run(main())
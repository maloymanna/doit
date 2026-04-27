"""Test selectors for a specific LLM UI URL."""
import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator

async def test_url(workspace: Path, url: str, project: str):
    """Test selectors for a specific URL."""
    print(f"\n{'='*60}")
    print(f"Testing URL: {url}")
    print(f"{'='*60}")
    
    orch = Orchestrator(workspace)
    
    try:
        # Open browser and navigate
        await orch.open_chat_session(project)
        await orch.navigate(url)
        
        print("\nWaiting for SSO/login if needed...")
        print("Press Enter after you've logged in and see the chat interface...")
        input()
        
        # Test a few key selectors
        bc = orch.browser
        
        # Test New Chat button
        try:
            await bc.click_new_chat()
            print("✓ New Chat button works")
        except Exception as e:
            print(f"✗ New Chat button failed: {e}")
        
        # Test Model selector (if configured)
        try:
            await bc.select_model("GPT-5.1")
            print("✓ Model selector works")
        except Exception as e:
            print(f"⚠ Model selector not available or failed: {e}")
        
        # Test prompt sending
        try:
            await bc.send_prompt("Hello! Please respond with 'OK' if you receive this.")
            print("✓ Prompt sending works")
            
            # Wait for response
            await asyncio.sleep(5)
            response = await bc.extract_last_assistant_message()
            if response:
                print(f"✓ Response received: {response[:100]}...")
        except Exception as e:
            print(f"✗ Prompt sending failed: {e}")
        
    finally:
        await asyncio.sleep(3)
        await orch.close_browser()

async def main():
    workspace = Path("~/arbitrary_folder/doit-workspace").expanduser()
    
    # Test different URLs (only those in allowlist)
    urls_to_test = [
        "https://usegpt.myorg",
        # "https://chatgpt.com",  # Uncomment when selectors are created
    ]
    
    for url in urls_to_test:
        await test_url(workspace, url, f"test-{url.replace('https://', '').replace('.', '-')}")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
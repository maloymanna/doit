"""Test script to verify configuration loading."""

from pathlib import Path
from doit.config import Config

def main():
    # Use the actual workspace
    workspace = Path("~/app-workspace").expanduser().resolve()
    
    print(f"Loading configuration from workspace: {workspace}")
    print("-" * 50)
    
    try:
        config = Config(workspace)
        
        print(f"✓ Config loaded successfully")
        print(f"  Autonomy mode: {config.autonomy.mode}")
        print(f"  Max iterations: {config.autonomy.global_max_iterations}")
        print(f"  Browser model: {config.browser.default_model}")
        print(f"  Logging level: {config.logging.level}")
        
        print(f"\n✓ Playwright config loaded")
        print(f"  Browser channel: {config.playwright.channel}")
        print(f"  Headless: {config.playwright.headless}")
        print(f"  Timeout: {config.playwright.timeout_ms}ms")
        
        print(f"\n✓ Selectors loaded:")
        for selector in ['new_chat_button', 'send_enabled', 'prompt_input']:
            value = config.playwright.selectors.get(selector)
            print(f"  {selector}: {value}")
        
        print(f"\n✓ All configurations valid!")
        
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
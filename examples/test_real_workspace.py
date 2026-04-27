"""Test loading configuration from your real workspace."""
from pathlib import Path
from doit.config import Config

# Your actual workspace path
workspace = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()

print(f"Loading workspace: {workspace}")

try:
    config = Config(workspace)
    print(f"✓ Workspace loaded successfully")
    print(f"  Autonomy mode: {config.autonomy.mode}")
    print(f"  Browser model: {config.browser.default_model}")
    print(f"  Workspace root: {config.workspace_root}")
except Exception as e:
    print(f"✗ Error: {e}")
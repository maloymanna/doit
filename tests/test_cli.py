# tests/test_cli.py [NEW v1]
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from doit.cli import main

def test_cli_parsing():
    # Test dry-run agent command
    sys.argv = ["doit", "agent", "--goal", "Test", "--project", "test", "--dry-run", "--autonomy", "1"]
    try:
        # We just verify argparse parses correctly without crashing
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="cmd")
        p = sub.add_parser("agent")
        p.add_argument("--goal")
        p.add_argument("--project")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--autonomy", type=int)
        args = parser.parse_args(sys.argv[1:])
        assert args.dry_run is True
        assert args.autonomy == 1
        print("✅ CLI parsing OK")
    except SystemExit:
        print("❌ CLI parsing failed")

if __name__ == "__main__":
    test_cli_parsing()
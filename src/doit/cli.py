# src/doit/cli.py [NEW v1]
import argparse
import logging
import sys
from pathlib import Path

# Lazy imports to avoid blocking --help if playwright is missing
def get_orchestrator():
    from .core.agent_orchestrator import AgentOrchestrator
    return AgentOrchestrator

def get_browser_page():
    """Returns Playwright page or None for dry-run."""
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True) # Use headless for CLI; override in config later
        return browser.new_page()
    except Exception as e:
        logging.warning(f"Browser unavailable: {e}")
        return None

def setup_workspace(path: Path):
    (path / ".doit").mkdir(parents=True, exist_ok=True)
    (path / "projects").mkdir(exist_ok=True)
    (path / "readonly_input").mkdir(exist_ok=True)
    print(f"✅ Workspace initialized at {path}")

def run_agent(args):
    ws = Path(args.workspace).resolve()
    if not ws.exists():
        print(f"❌ Workspace not found: {ws}"); sys.exit(1)
        
    Orchestrator = get_orchestrator()
    page = get_browser_page() if not args.dry_run else None
    
    orc = Orchestrator(
        workspace_dir=ws,
        llm_client=None,  # Replace with your actual Playwright LLM client function
        page=page,
        prompt_builder=None,
        validator=None
    )
    
    print(f"🤖 Starting agent (Dry-Run: {args.dry_run} | Autonomy: {args.autonomy})")
    result = orc.run(args.goal, args.project, max_steps=args.max_steps)
    print(f"\n🏁 Result: {result}")

def main():
    parser = argparse.ArgumentParser(prog="doit", description="Local agent with web-LLM intelligence")
    parser.add_argument("--workspace", default=str(Path.home() / "doit-workspace"), help="Workspace path")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    sub = parser.add_subparsers(dest="command", required=True)
    
    # init
    init_p = sub.add_parser("init", help="Initialize workspace")
    init_p.add_argument("--path", required=True, help="Directory to initialize")
    
    # agent
    agent_p = sub.add_parser("agent", help="Run autonomous agent loop")
    agent_p.add_argument("--goal", required=True, help="Natural language goal")
    agent_p.add_argument("--project", required=True, help="Project name")
    agent_p.add_argument("--max-steps", type=int, default=15, help="Max iterations")
    agent_p.add_argument("--dry-run", action="store_true", help="Plan only, no execution")
    agent_p.add_argument("--autonomy", type=int, choices=[0, 1, 2], default=0, help="Autonomy level")
    agent_p.set_defaults(func=run_agent)
    
    # status
    sub.add_parser("status", help="View agent state/logs")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
        
    if args.command == "init":
        setup_workspace(Path(args.path))
    elif args.command == "agent":
        args.func(args)
    else:
        print(f"⚠️ Command '{args.command}' not implemented in Phase 3.")

if __name__ == "__main__":
    main()
# src/doit/cli.py [MOD v2.1]
import argparse
import logging
import sys
from pathlib import Path

def get_orchestrator():
    from .core.agent_orchestrator import AgentOrchestrator
    return AgentOrchestrator

def run_agent(args):
    ws = Path(args.workspace).resolve()
    if not ws.exists():
        print(f"❌ Workspace not found: {ws}"); sys.exit(1)

    llm_adapter = None
    llm_send_fn = None

    if not args.dry_run:
        try:
            from .llm.web_llm_adapter import WebLLMSyncAdapter
            llm_adapter = WebLLMSyncAdapter(ws, args.project, args.url)
            llm_send_fn = llm_adapter.send_prompt
        except Exception as e:
            print(f"❌ LLM Adapter init failed: {e}")
            import traceback; traceback.print_exc()
            sys.exit(1)

    Orchestrator = get_orchestrator()
    orc = Orchestrator(
        workspace_dir=ws,
        llm_client=llm_send_fn,  # Callable[[str], str]
        page=None,               # Tools will manage their own browser context later
        prompt_builder=None,
        validator=None,
        autonomy_mode=args.autonomy,
        dry_run=args.dry_run
    )

    try:
        print(f"🤖 Starting agent (Dry-Run: {args.dry_run} | Autonomy: {args.autonomy})")
        result = orc.run(args.goal, args.project, max_steps=args.max_steps)
        print(f"\n🏁 Result: {result}")
    finally:
        # Guarantee browser cleanup on success, error, or Ctrl+C
        if llm_adapter:
            llm_adapter.close()

def setup_workspace(path: Path):
    (path / ".doit").mkdir(parents=True, exist_ok=True)
    (path / ".doit" / "sessions").mkdir(exist_ok=True)
    (path / "projects").mkdir(exist_ok=True)
    (path / "readonly_input").mkdir(exist_ok=True)
    print(f"✅ Workspace initialized at {path}")

def main():
    parser = argparse.ArgumentParser(prog="doit", description="Local agent with web-LLM intelligence")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    sub = parser.add_subparsers(dest="command", required=True)
    
    # init
    init_p = sub.add_parser("init", help="Initialize workspace")
    init_p.add_argument("--path", required=True)
    init_p.set_defaults(func=lambda args: setup_workspace(Path(args.path)))
    
    # agent
    agent_p = sub.add_parser("agent", help="Run autonomous agent loop")
    agent_p.add_argument("--workspace", default=str(Path.home() / "doit-workspace"))
    agent_p.add_argument("--url", default="https://usegpt.myorg", help="Web LLM URL")
    agent_p.add_argument("--goal", required=True)
    agent_p.add_argument("--project", required=True, help="Isolates browser profile")
    agent_p.add_argument("--max-steps", type=int, default=15)
    agent_p.add_argument("--dry-run", action="store_true")
    agent_p.add_argument("--autonomy", type=int, choices=[0, 1, 2], default=0)
    agent_p.set_defaults(func=run_agent)
    
    args = parser.parse_args()
    
    lvl = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=lvl, format="[%(levelname)s] %(message)s")
        
    if hasattr(args, 'func'):
        args.func(args)

if __name__ == "__main__":
    main()
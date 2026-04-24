import argparse
import os
from .orchestrator import Orchestrator

def prompt_user(message: str) -> bool:
    ans = input(f"{message} [y/N]: ").strip().lower()
    return ans in ("y", "yes")

def main():
    parser = argparse.ArgumentParser(prog="doit")
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init-workspace")
    init_p.add_argument("--workspace", default=".")

    list_p = sub.add_parser("list-plugins")
    list_p.add_argument("--workspace", default=".")

    sum_p = sub.add_parser("summarize-file")
    sum_p.add_argument("path")
    sum_p.add_argument("--project", required=True)
    sum_p.add_argument("--workspace", default=".")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    workspace_root = os.path.abspath(getattr(args, "workspace", "."))
    orch = Orchestrator(workspace_root, prompt_user)

    if args.command == "init-workspace":
        cfg = orch.config
        cfg.ensure_dirs()
        if not os.path.exists(cfg.config_path):
            cfg.save_config({"readonly_input_dir": "readonly_input"})
        if not os.path.exists(cfg.allowlist_path):
            with open(cfg.allowlist_path, "w", encoding="utf-8") as f:
                f.write("")
        if not os.path.exists(cfg.playwright_config_path):
            with open(cfg.playwright_config_path, "w", encoding="utf-8") as f:
                f.write("# TODO: fill Playwright+Edge config\n")
        if not os.path.exists(cfg.autonomy_mode_path):
            cfg.set_autonomy_mode(0)
        print(f"Initialized workspace at {workspace_root}")

    elif args.command == "list-plugins":
        for name in orch.plugins.keys():
            print(name)

    elif args.command == "summarize-file":
        result = orch.run_command("summarize_file", {
            "file_path": os.path.join(workspace_root, args.path),
            "project_name": args.project,
        })
        print(result)

if __name__ == "__main__":
    main()

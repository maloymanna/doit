import argparse
import asyncio
from pathlib import Path

from .orchestrator import Orchestrator
from .browser.controller import (
    EdgeUnavailableError,
    AllowlistError,
    BrowserError,
)


def main():
    parser = argparse.ArgumentParser(prog="doit")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--project", default="default")
    parser.add_argument("--url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default="Hello from doit Milestone 2")
    parser.add_argument("--files", nargs="*", default=None)
    args = parser.parse_args()

    async def run():
        orch = Orchestrator(Path(args.workspace))

        # -----------------------------
        # Milestone 2 test command
        # -----------------------------
        if args.command == "chat-test":
            try:
                # Ensure browser + session
                await orch.open_chat_session(args.project)

                if args.url:
                    await orch.navigate(args.url)

                # Start new chat
                await orch.browser.click_new_chat()

                # Select model (default or override)
                await orch.browser.select_model(args.model)

                # Send prompt
                await orch.browser.send_prompt(args.prompt, files=args.files)

                # Poll status
                while True:
                    status = await orch.get_status()
                    if status in ("idle", "complete"):
                        break
                    await asyncio.sleep(0.2)

                # Extract results
                last_msg = await orch.get_last_response()
                tokens = await orch.get_last_response_tokens()
                full_conv = await orch.get_conversation_history()
                copied = await orch.get_last_response_via_copy()

                print("\n=== LAST ASSISTANT MESSAGE ===")
                print(last_msg or "<none>")

                print("\n=== LAST ASSISTANT TOKENS ===")
                print(tokens)

                print("\n=== FULL CONVERSATION ===")
                for msg in full_conv:
                    print(f"[{msg['role']}] {msg['text']}")

                print("\n=== COPY VIA UI ===")
                print(copied or "<none>")

            except EdgeUnavailableError as e:
                print("ERROR: Edge unavailable:", e)
            except AllowlistError as e:
                print("ERROR: URL blocked by allowlist:", e)
            except BrowserError as e:
                print("Browser error:", e)
            except Exception as e:
                print("Unexpected error:", e)

            return

        # -----------------------------
        # Other built-in commands (examples)
        # -----------------------------
        if args.command == "init-workspace":
            # Minimal example: orchestrator/config will create .doit
            orch = Orchestrator(Path(args.workspace))
            print("Initializing workspace:", args.workspace)
            # Accessing config will create .doit and default files
            _ = orch.config.data
            print("Workspace initialized.")
            return

        if args.command == "list-plugins":
            # Placeholder: plugin discovery will be implemented in Milestone 3
            print("Installed plugins: (not implemented yet)")
            return

        if args.command == "summarize-file":
            print("summarize-file not implemented in CLI stub.")
            return

        # -----------------------------
        # Default: non‑browser commands
        # -----------------------------
        result = orch.run(args.command)
        print(result)

    asyncio.run(run())


if __name__ == "__main__":
    main()

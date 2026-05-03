"""Main agent runner - async version."""

import asyncio
from pathlib import Path
from typing import Callable, Dict, Any, Awaitable

from .state_manager import StateManager
from .prompt_builder import build_prompt
from .json_parser import parse_llm_output, JSONParseError
from .action_dispatcher import execute_action


async def run(
    goal: str,
    project: str,
    workspace_root: Path,
    llm_client: Callable[[str], Awaitable[str]],
    max_iterations: int = 10,
    verbose: bool = True
) -> Dict[str, Any]:
    """Main agent loop – async."""
    state_mgr = StateManager(workspace_root, project)
    state = state_mgr.load()
    state["goal"] = goal
    state_mgr.save(state)

    if verbose:
        print(f"\n{'='*60}")
        print(f"🤖 Agent Starting")
        print(f"{'='*60}")
        print(f"📁 Project: {project}")
        print(f"🎯 Goal: {goal}")
        print(f"🔄 Max iterations: {max_iterations}")

    iteration = 0
    final_result = {"status": "not_completed", "iterations": 0}

    while iteration < max_iterations:
        iteration += 1
        state["iteration"] = iteration

        if verbose:
            print(f"\n--- Iteration {iteration}/{max_iterations} ---")

        try:
            prompt = build_prompt(state)
            if verbose:
                print(f"📝 Prompt built ({len(prompt)} chars)")

            raw = await llm_client(prompt)   # ← HERE: await async client
            if verbose:
                print(f"📥 Response received ({len(raw)} chars)")

            action = parse_llm_output(raw)
            if verbose:
                print(f"📋 Parsed action: {action.get('action')}")

            result = execute_action(action)
            if verbose:
                print(f"⚙️ Action result: {result.get('status')}")

            state["last_action"] = action
            state["last_result"] = result

            entry = {
                "iteration": iteration,
                "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "response": raw[:500] + "..." if len(raw) > 500 else raw,
                "action": action,
                "result": result
            }
            state_mgr.append_history(entry)
            state_mgr.save(state)

            if action.get("action") == "FINISH":
                if verbose:
                    print(f"\n✅ GOAL ACHIEVED in {iteration} iterations!")
                final_result = {
                    "status": "completed",
                    "iterations": iteration,
                    "final_action": action,
                    "final_result": result
                }
                break

        except JSONParseError as e:
            if verbose:
                print(f"❌ JSON Parse Error: {e}")
            state["last_result"] = {"status": "error", "error": str(e)}
            state_mgr.save(state)
            continue
        except Exception as e:
            if verbose:
                print(f"❌ Error: {e}")
            state["last_result"] = {"status": "error", "error": str(e)}
            state_mgr.save(state)
            break

    if iteration >= max_iterations and final_result["status"] != "completed":
        if verbose:
            print(f"\n⚠️ STOPPED: Max iterations ({max_iterations}) reached")
        final_result = {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "last_state": state
        }

    return final_result
#!/usr/bin/env python3
"""Test the agent runner with mock LLM (async)."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from doit.core.runner import run
from doit.core.state_manager import StateManager


async def mock_llm_client(prompt: str) -> str:
    """Mock async LLM."""
    if "example.com" in prompt:
        return '{"action": "NAVIGATE", "parameters": {"url": "https://example.com"}, "reason": "Need to navigate"}'
    elif "extract" in prompt.lower():
        return '{"action": "EXTRACT_TEXT", "parameters": {}, "reason": "Extract page content"}'
    elif "done" in prompt.lower():
        return '{"action": "FINISH", "parameters": {}, "reason": "Goal achieved"}'
    else:
        return '{"action": "ALERT_USER", "parameters": {"message": "Working on it"}, "reason": "Processing"}'


async def test_runner_with_mock():
    print("\n" + "="*60)
    print("TEST: Agent Runner (with Mock LLM)")
    print("="*60)

    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)

    try:
        print("\n Running agent with mock LLM...")
        result = await run(
            goal="Navigate to example.com and extract content, then finish",
            project="test_mock",
            workspace_root=workspace,
            llm_client=mock_llm_client,
            max_iterations=5,
            verbose=True
        )

        print(f"\n Final result: {result}")
        assert result["status"] in ["completed", "max_iterations_reached"]

        state_file = workspace / "projects" / "test_mock" / "state.json"
        history_file = workspace / "projects" / "test_mock" / "history.jsonl"
        assert state_file.exists()
        assert history_file.exists()
        print(" ✓ State and history files created")

        sm = StateManager(workspace, "test_mock")
        saved_state = sm.load()
        assert saved_state["goal"] == "Navigate to example.com and extract content, then finish"
        print(" ✓ Goal saved correctly")

        print("\n✅ Runner with mock LLM passed!\n")
    finally:
        shutil.rmtree(temp_dir)


async def main():
    await test_runner_with_mock()


if __name__ == "__main__":
    asyncio.run(main())
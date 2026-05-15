#!/usr/bin/env python3
"""Regression: Verify llm_attach_file is dispatcher-only, not in ||TOOLS|| prompt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.utils.session_logger import init_session_logger

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()

def test_attach_not_in_prompt():
    # 1. Builder should NOT contain llm_attach_file
    builder = SingleLinePromptBuilder()
    builder.register_tool("file_read", "Reads files")
    prompt = builder.build_next_step_prompt("test", "g1", 0, "none", [])
    assert "llm_attach_file" not in prompt, "FAIL: Attach tool leaked into prompt"
    assert "||TOOLS||" in prompt
    print("✅ PASS: llm_attach_file hidden from ||TOOLS||")

    # 2. Agent dispatcher SHOULD contain it
    agent = AgentOrchestrator(workspace_dir=WORKSPACE, project="reg-test")
    assert "llm_attach_file" in agent.dispatcher._tools, "FAIL: Tool not registered in dispatcher"
    print("✅ PASS: llm_attach_file registered in dispatcher")

    # 3. Prompt schema remains intact
    assert '"additionalProperties":false' in prompt
    assert '||SCHEMA||' in prompt
    print("✅ PASS: Strict JSON schema preserved")

if __name__ == "__main__":
    init_session_logger(WORKSPACE)
    print("Running Phase 7 Attachment Regression Suite...")
    test_attach_not_in_prompt()
    print("\n✅ ALL REGRESSIONS PASSED")
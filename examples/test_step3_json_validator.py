#!/usr/bin/env python3
"""
BABY STEP 3: JSONValidator Edge Case Testing
Tests extraction, schema validation, and error handling without browser/LLM.
"""
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.json_validator import JSONValidator, ValidationError

# Schema exactly matching prompt_builder.py v2 injection
TEST_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string"},
        "parameters": {"type": "object"},
        "description": {"type": "string"},
        "goal_status": {"type": "string", "enum": ["in_progress", "completed", "blocked", "requires_user_confirmation"]},
        "rationale": {"type": "string"},
        "fallback_instruction": {"type": "string"}
    },
    "required": ["tool_name", "parameters", "description", "goal_status", "rationale"],
    "additionalProperties": False
}

def run_test(name, raw_input, should_pass=True, expected_error_substring=None):
    validator = JSONValidator()
    print(f"\n🧪 [{name}]")
    print(f"   Input: {raw_input[:80]}...")
    try:
        result = validator.parse_and_validate(raw_input, TEST_SCHEMA)
        if should_pass:
            print(f"   ✅ PASS - Extracted & Validated: {result.get('tool_name')}")
        else:
            print(f"   ❌ FAIL - Expected ValidationError but got result")
    except ValidationError as e:
        if not should_pass:
            if expected_error_substring and expected_error_substring in e.message:
                print(f"   ✅ PASS - Correctly raised ValidationError: {e.message[:60]}")
            else:
                print(f"   ✅ PASS - Raised ValidationError (msg: {e.message[:60]})")
        else:
            print(f"   ❌ FAIL - Unexpected ValidationError: {e.message[:60]}")
    except Exception as e:
        print(f"   ❌ FAIL - Unexpected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("="*60)
    print("BABY STEP 3: JSONValidator Edge Case Testing")
    print("="*60)

    # 1. Valid plain JSON
    run_test("Plain JSON", '{"tool_name":"test","parameters":{},"description":"ok","goal_status":"completed","rationale":"test"}', should_pass=True)

    # 2. Markdown-wrapped JSON (common LLM leak)
    run_test("Markdown Block", 'Sure! Here is the JSON:\n```json\n{"tool_name":"test","parameters":{},"description":"ok","goal_status":"completed","rationale":"test"}\n```', should_pass=True)

    # 3. Conversational prefix/suffix
    run_test("Conversational Text", 'I think you should run the test tool. So here it is: {"tool_name":"test","parameters":{},"description":"ok","goal_status":"completed","rationale":"test"}. Let me know.', should_pass=True)

    # 4. Missing required field (no rationale)
    run_test("Missing Required", '{"tool_name":"test","parameters":{},"description":"ok","goal_status":"completed"}', should_pass=False, expected_error_substring="rationale")

    # 5. Extra property (violates additionalProperties: false)
    run_test("Extra Property", '{"tool_name":"test","parameters":{},"description":"ok","goal_status":"completed","rationale":"test","extra_field":"bad"}', should_pass=False, expected_error_substring="additionalProperties")

    # 6. Invalid enum value
    run_test("Invalid Enum", '{"tool_name":"test","parameters":{},"description":"ok","goal_status":"INVALID_STATUS","rationale":"test"}', should_pass=False, expected_error_substring="enum")

    # 7. Completely invalid text
    run_test("No JSON", 'This is just plain text with no JSON anywhere.', should_pass=False)

    # 8. Broken JSON syntax
    run_test("Broken Syntax", '{"tool_name": "test", "parameters": {, "description": "ok"}', should_pass=False)

    print("\n" + "="*60)
    print("✅ BABY STEP 3 COMPLETE")
    print("="*60)
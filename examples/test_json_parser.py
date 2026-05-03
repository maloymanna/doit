#!/usr/bin/env python3
"""Test JSON Parser - no dependencies on other components."""

import pytest
from doit.core.json_parser import parse_llm_output, validate_action_schema, JSONParseError


def test_parse_valid_json():
    """Test parsing valid JSON from LLM response."""
    print("\n" + "="*60)
    print("TEST 3: JSON Parser")
    print("="*60)
    
    # Test 3.1: Clean JSON
    print("\n3.1 Testing clean JSON...")
    response = '{"action": "NAVIGATE", "parameters": {"url": "https://example.com"}, "reason": "Need to go there"}'
    result = parse_llm_output(response)
    
    assert result["action"] == "NAVIGATE"
    assert result["parameters"]["url"] == "https://example.com"
    assert result["reason"] == "Need to go there"
    print("   ✓ Clean JSON parsed")
    
    # Test 3.2: JSON with extra text before/after
    print("\n3.2 Testing JSON with surrounding text...")
    response = 'Here is the JSON: {"action": "EXTRACT_TEXT", "parameters": {}, "reason": "Extract content"} Thanks!'
    result = parse_llm_output(response)
    
    assert result["action"] == "EXTRACT_TEXT"
    assert result["reason"] == "Extract content"
    print("   ✓ JSON with surrounding text parsed")
    
    # Test 3.3: JSON with markdown code block
    print("\n3.3 Testing JSON in markdown code block...")
    response = '```json\n{"action": "SEARCH", "parameters": {"query": "test"}, "reason": "Find info"}\n```'
    result = parse_llm_output(response)
    
    assert result["action"] == "SEARCH"
    assert result["parameters"]["query"] == "test"
    print("   ✓ JSON in markdown code block parsed")
    
    # Test 3.4: JSON with missing parameters (should add default)
    print("\n3.4 Testing JSON with missing parameters...")
    response = '{"action": "FINISH", "reason": "Done"}'
    result = parse_llm_output(response)
    
    assert result["action"] == "FINISH"
    assert result["parameters"] == {}
    print("   ✓ Missing parameters defaulted to empty dict")
    
    # Test 3.5: JSON with missing reason (should add default)
    print("\n3.5 Testing JSON with missing reason...")
    response = '{"action": "ALERT_USER", "parameters": {"message": "Hello"}}'
    result = parse_llm_output(response)
    
    assert result["action"] == "ALERT_USER"
    assert result["reason"] == "No reason provided"
    print("   ✓ Missing reason defaulted")
    
    # Test 3.6: Validate action schema
    print("\n3.6 Testing schema validation...")
    valid_action = {"action": "NAVIGATE", "parameters": {"url": "test"}}
    invalid_action = {"wrong": "format"}
    
    assert validate_action_schema(valid_action) is True
    assert validate_action_schema(invalid_action) is False
    assert validate_action_schema({"action": "UNKNOWN", "parameters": {}}) is False
    print("   ✓ Schema validation working")
    
    print("\n✅ JSON Parser tests passed!\n")


def test_parse_invalid_json():
    """Test error handling for invalid JSON."""
    print("\n" + "="*60)
    print("TEST 3b: JSON Parser Error Handling")
    print("="*60)
    
    # Test 3.7: Empty response
    print("\n3.7 Testing empty response...")
    try:
        parse_llm_output("")
        assert False, "Should have raised JSONParseError"
    except JSONParseError as e:
        assert "Empty LLM response" in str(e)
        print("   ✓ Empty response caught")
    
    # Test 3.8: No JSON in response
    print("\n3.8 Testing response with no JSON...")
    try:
        parse_llm_output("This is just plain text without any JSON structure")
        assert False, "Should have raised JSONParseError"
    except JSONParseError as e:
        assert "No JSON found" in str(e)
        print("   ✓ No JSON caught")
    
    # Test 3.9: Malformed JSON
    print("\n3.9 Testing malformed JSON...")
    try:
        parse_llm_output('{"action": "NAVIGATE", "parameters": {"url": "test"')
        assert False, "Should have raised JSONParseError"
    except JSONParseError as e:
        # The regex might still find a JSON-like pattern, so either message is acceptable
        error_msg = str(e)
        assert "No JSON found" in error_msg or "Invalid JSON" in error_msg
        print(f"   ✓ Malformed JSON caught: {error_msg[:50]}...")
    
    # Test 3.10: Missing action field
    print("\n3.10 Testing missing action field...")
    try:
        parse_llm_output('{"parameters": {}, "reason": "No action"}')
        assert False, "Should have raised JSONParseError"
    except JSONParseError as e:
        assert "Missing 'action' field" in str(e)
        print("   ✓ Missing action field caught")
    
    print("\n✅ JSON Parser error handling passed!\n")


def test_real_world_scenarios():
    """Test real-world LLM response patterns."""
    print("\n" + "="*60)
    print("TEST 3c: Real-World Scenarios")
    print("="*60)
    
    # Test 3.11: LLM might add explanatory text before JSON
    print("\n3.11 Testing explanatory text before JSON...")
    response = """I'll help you with that. Here's the action:
    {"action": "NAVIGATE", "parameters": {"url": "https://example.com"}, "reason": "Need to access the page"}"""
    result = parse_llm_output(response)
    assert result["action"] == "NAVIGATE"
    print("   ✓ Explanatory text handled")
    
    # Test 3.12: LLM might add conversational text after JSON
    print("\n3.12 Testing conversational text after JSON...")
    response = """{"action": "EXTRACT_TEXT", "parameters": {}, "reason": "Get page content"} Let me know if you need more help."""
    result = parse_llm_output(response)
    assert result["action"] == "EXTRACT_TEXT"
    print("   ✓ Conversational text after JSON handled")
    
    # Test 3.13: Nested JSON in parameters
    print("\n3.13 Testing nested JSON in parameters...")
    response = '{"action": "WRITE_EMAIL", "parameters": {"to": "user@example.com", "subject": "Test", "body": "Hello world"}, "reason": "Send email"}'
    result = parse_llm_output(response)
    assert result["parameters"]["to"] == "user@example.com"
    assert result["parameters"]["body"] == "Hello world"
    print("   ✓ Nested parameters handled")
    
    print("\n✅ Real-world scenarios passed!\n")


if __name__ == "__main__":
    test_parse_valid_json()
    test_parse_invalid_json()
    test_real_world_scenarios()
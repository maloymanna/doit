#!/usr/bin/env python3
"""Test Action Dispatcher - no dependencies on other components."""

from doit.core.action_dispatcher import execute_action


def test_action_dispatcher():
    print("\n" + "="*60)
    print("TEST 4: Action Dispatcher")
    print("="*60)
    
    # Test 4.1: NAVIGATE action
    print("\n4.1 Testing NAVIGATE action...")
    action = {"action": "NAVIGATE", "parameters": {"url": "https://example.com"}, "reason": "Go to page"}
    result = execute_action(action)
    
    assert result["status"] == "navigated"
    assert result["url"] == "https://example.com"
    print("   ✓ NAVIGATE action handled")
    
    # Test 4.2: EXTRACT_TEXT action
    print("\n4.2 Testing EXTRACT_TEXT action...")
    action = {"action": "EXTRACT_TEXT", "parameters": {}, "reason": "Get page content"}
    result = execute_action(action)
    
    assert result["status"] == "extracted"
    assert "page_content" in result
    print("   ✓ EXTRACT_TEXT action handled")
    
    # Test 4.3: SEARCH action
    print("\n4.3 Testing SEARCH action...")
    action = {"action": "SEARCH", "parameters": {"query": "python programming"}, "reason": "Find information"}
    result = execute_action(action)
    
    assert result["status"] == "searched"
    assert result["query"] == "python programming"
    print("   ✓ SEARCH action handled")
    
    # Test 4.4: WRITE_EMAIL action
    print("\n4.4 Testing WRITE_EMAIL action...")
    action = {
        "action": "WRITE_EMAIL",
        "parameters": {
            "to": "user@example.com",
            "subject": "Test Email",
            "body": "Hello, this is a test"
        },
        "reason": "Send notification"
    }
    result = execute_action(action)
    
    assert result["status"] == "email_drafted"
    assert result["to"] == "user@example.com"
    assert result["subject"] == "Test Email"
    print("   ✓ WRITE_EMAIL action handled")
    
    # Test 4.5: ALERT_USER action
    print("\n4.5 Testing ALERT_USER action...")
    action = {"action": "ALERT_USER", "parameters": {"message": "Task completed"}, "reason": "Notify user"}
    result = execute_action(action)
    
    assert result["status"] == "alert_sent"
    assert result["message"] == "Task completed"
    print("   ✓ ALERT_USER action handled")
    
    # Test 4.6: FINISH action
    print("\n4.6 Testing FINISH action...")
    action = {"action": "FINISH", "parameters": {}, "reason": "Goal achieved"}
    result = execute_action(action)
    
    assert result["status"] == "done"
    print("   ✓ FINISH action handled")
    
    print("\n✅ Action Dispatcher tests passed!\n")


def test_action_error_handling():
    """Test error handling for invalid actions."""
    print("\n" + "="*60)
    print("TEST 4b: Action Dispatcher Error Handling")
    print("="*60)
    
    # Test 4.7: Unknown action
    print("\n4.7 Testing unknown action...")
    action = {"action": "UNKNOWN_ACTION", "parameters": {}, "reason": "This shouldn't work"}
    
    try:
        result = execute_action(action)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown action" in str(e)
        print("   ✓ Unknown action caught")
    
    # Test 4.8: NAVIGATE without URL parameter
    print("\n4.8 Testing NAVIGATE without URL...")
    action = {"action": "NAVIGATE", "parameters": {}, "reason": "Missing URL"}
    result = execute_action(action)
    
    assert result["status"] == "error"
    assert "error" in result
    print("   ✓ Missing parameter handled gracefully")
    
    # Test 4.9: SEARCH without query parameter
    print("\n4.9 Testing SEARCH without query...")
    action = {"action": "SEARCH", "parameters": {}, "reason": "Missing query"}
    result = execute_action(action)
    
    assert result["status"] == "error"
    assert "error" in result
    print("   ✓ Missing query handled gracefully")
    
    print("\n✅ Action Dispatcher error handling passed!\n")


def test_result_consistency():
    """Test that all actions return consistent result structure."""
    print("\n" + "="*60)
    print("TEST 4c: Result Structure Consistency")
    print("="*60)
    
    actions = [
        {"action": "NAVIGATE", "parameters": {"url": "https://test.com"}},
        {"action": "EXTRACT_TEXT", "parameters": {}},
        {"action": "SEARCH", "parameters": {"query": "test"}},
        {"action": "WRITE_EMAIL", "parameters": {"to": "a@b.com", "subject": "s", "body": "b"}},
        {"action": "ALERT_USER", "parameters": {"message": "test"}},
        {"action": "FINISH", "parameters": {}},
    ]
    
    for action in actions:
        result = execute_action(action)
        assert "status" in result
        assert isinstance(result["status"], str)
        print(f"   ✓ {action['action']} returns consistent result")
    
    print("\n✅ Result structure consistency passed!\n")


if __name__ == "__main__":
    test_action_dispatcher()
    test_action_error_handling()
    test_result_consistency()
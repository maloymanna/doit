"""JSON parser for LLM responses."""

import json
import re
from typing import Dict, Any


class JSONParseError(Exception):
    """Raised when JSON parsing fails."""
    pass


def parse_llm_output(text: str) -> Dict[str, Any]:
    """
    Parse LLM response into a Python dictionary.
    
    Extracts the first valid JSON block from the response.
    
    Args:
        text: Raw LLM response text
    
    Returns:
        Parsed JSON dictionary
    
    Raises:
        JSONParseError: If no valid JSON found
    """
    if not text or not text.strip():
        raise JSONParseError("Empty LLM response")
    
    # Try to extract JSON block
    json_pattern = r'\{[^{}]*({[^{}]*}[^{}]*)*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    
    if not match:
        # Try a simpler pattern
        match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if not match:
        raise JSONParseError(f"No JSON found in LLM response: {text[:200]}")
    
    json_str = match.group(0)
    
    # Clean up common issues
    json_str = json_str.replace('\n', ' ').replace('\r', '')
    
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Invalid JSON: {e}\nResponse excerpt: {text[:200]}")
    
    # Validate required fields
    if 'action' not in result:
        raise JSONParseError(f"Missing 'action' field in JSON: {result}")
    
    if 'parameters' not in result:
        result['parameters'] = {}
    
    if 'reason' not in result:
        result['reason'] = "No reason provided"
    
    return result


def validate_action_schema(action: Dict[str, Any]) -> bool:
    """
    Validate that an action dictionary has the required structure.
    
    Args:
        action: Action dictionary to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['action', 'parameters']
    
    for field in required_fields:
        if field not in action:
            return False
    
    # Action must be one of the known types
    known_actions = ['NAVIGATE', 'EXTRACT_TEXT', 'SEARCH', 'WRITE_EMAIL', 'ALERT_USER', 'FINISH']
    
    if action['action'] not in known_actions:
        return False
    
    return True
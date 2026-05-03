"""Action dispatcher for executing agent actions."""

from typing import Dict, Any


def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an action and return the result.
    
    Args:
        action: Action dictionary with 'action' and 'parameters' keys
    
    Returns:
        Result dictionary with at least a 'status' field
    """
    name = action.get("action")
    params = action.get("parameters", {})
    
    if name == "NAVIGATE":
        return _navigate(params)
    
    elif name == "EXTRACT_TEXT":
        return _extract_text(params)
    
    elif name == "SEARCH":
        return _search(params)
    
    elif name == "WRITE_EMAIL":
        return _write_email(params)
    
    elif name == "ALERT_USER":
        return _alert_user(params)
    
    elif name == "FINISH":
        return _finish(params)
    
    else:
        raise ValueError(f"Unknown action: {name}")


def _navigate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Navigate to a URL."""
    url = params.get("url", "")
    if not url:
        return {"status": "error", "error": "Missing 'url' parameter"}
    
    print(f"[NAVIGATE] Going to: {url}")
    # TODO: Integrate with browser controller
    return {"status": "navigated", "url": url}


def _extract_text(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text from current page."""
    print("[EXTRACT_TEXT] Reading page content...")
    # TODO: Integrate with browser controller
    # For now, return dummy content
    return {
        "status": "extracted",
        "page_content": "Sample page content. This will be replaced with actual browser extraction."
    }


def _search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for information."""
    query = params.get("query", "")
    if not query:
        return {"status": "error", "error": "Missing 'query' parameter"}
    
    print(f"[SEARCH] Query: {query}")
    # TODO: Implement search (web search or internal)
    return {
        "status": "searched",
        "query": query,
        "results": "Search results would appear here."
    }


def _write_email(params: Dict[str, Any]) -> Dict[str, Any]:
    """Write/draft an email."""
    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")
    
    print(f"[EMAIL] To: {to}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    
    return {
        "status": "email_drafted",
        "to": to,
        "subject": subject
    }


def _alert_user(params: Dict[str, Any]) -> Dict[str, Any]:
    """Send an alert to the user."""
    message = params.get("message", "")
    print(f"[ALERT] {message}")
    
    return {
        "status": "alert_sent",
        "message": message
    }


def _finish(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mark the goal as complete."""
    reason = params.get("reason", "Goal achieved")
    print(f"[FINISH] {reason}")
    
    return {
        "status": "done",
        "reason": reason
    }
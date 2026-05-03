"""Prompt builder for agent LLM interactions."""

from typing import Dict, Any


def build_prompt(state: Dict[str, Any]) -> str:
    """
    Build the full prompt for the LLM based on current state.
    
    Args:
        state: Current agent state with goal, last_action, last_result
    
    Returns:
        Formatted prompt string
    """
    goal = state.get("goal", "")
    last_action = state.get("last_action")
    last_result = state.get("last_result")
    iteration = state.get("iteration", 0)
    conversation_history = state.get("conversation_history", [])
    
    # Format conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n## CONVERSATION HISTORY\n"
        for turn in conversation_history[-5:]:  # Last 5 turns for context
            if isinstance(turn, dict):
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                history_text += f"\n{role.upper()}: {content}\n"
    
    # Format last action and result
    last_action_text = "None"
    if last_action:
        action_name = last_action.get("action", "unknown")
        params = last_action.get("parameters", {})
        last_action_text = f"{action_name} {params}"
    
    last_result_text = "None"
    if last_result:
        last_result_text = str(last_result)
    
    prompt = f"""You are an automation planner. Your job is to break down goals into simple actions.

Return ONLY valid JSON. No explanations, no markdown, just the JSON.

## CURRENT GOAL
{goal}

## ITERATION
{iteration}

## LAST ACTION TAKEN
{last_action_text}

## LAST ACTION RESULT
{last_result_text}
{history_text}
## AVAILABLE ACTIONS

| Action | Description | Parameters |
|--------|-------------|------------|
| NAVIGATE | Navigate to a URL | {{"url": "https://..."}} |
| EXTRACT_TEXT | Extract text from current page | {{}} |
| SEARCH | Search for information | {{"query": "..."}} |
| WRITE_EMAIL | Draft an email | {{"to": "...", "subject": "...", "body": "..."}} |
| ALERT_USER | Send a message to the user | {{"message": "..."}} |
| FINISH | Goal is complete | {{}} |

## RESPONSE FORMAT

{{
  "action": "ACTION_NAME",
  "parameters": {{}},
  "reason": "Brief explanation of why this action"
}}

## RULES
1. Choose ONE action per response
2. Use FINISH only when the goal is fully achieved
3. Be specific with parameters
4. Check last result before repeating failed actions

Now, respond with valid JSON only:"""
    
    return prompt


def build_simple_prompt(goal: str, context: str = "") -> str:
    """
    Build a simplified prompt for testing without full state.
    
    Args:
        goal: The user's goal
        context: Additional context
    
    Returns:
        Simple prompt string
    """
    return f"""Goal: {goal}
Context: {context}

Available actions: NAVIGATE, EXTRACT_TEXT, SEARCH, WRITE_EMAIL, ALERT_USER, FINISH

Return ONLY JSON: {{"action": "...", "parameters": {{}}, "reason": "..."}}"""
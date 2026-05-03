"""State management for agent persistence."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class StateManager:
    """
    Manages agent state persisted in workspace.
    
    Directory structure:
        workspace_root/
        └── projects/
            └── {project_name}/
                ├── state.json      # Current agent state
                └── history.jsonl   # Full conversation history
    """
    
    def __init__(self, workspace_root: Path, project_name: str):
        """
        Initialize state manager for a project.
        
        Args:
            workspace_root: Path to workspace root (must contain .doit/)
            project_name: Name of the project
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.project_name = project_name
        self.project_dir = self.workspace_root / "projects" / project_name
        
        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.project_dir / "state.json"
        self.history_file = self.project_dir / "history.jsonl"
    
    def load(self) -> Dict[str, Any]:
        """
        Load state from disk, or return default if not exists.
        
        Returns:
            State dictionary with default values if file doesn't exist
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[StateManager] Error loading state: {e}")
                return self._get_default_state()
        
        return self._get_default_state()
    
    def _get_default_state(self) -> Dict[str, Any]:
        """Return default empty state."""
        return {
            "goal": "",
            "last_action": None,
            "last_result": None,
            "iteration": 0,
            "conversation_history": []
        }
    
    def save(self, state: Dict[str, Any]) -> None:
        """
        Save state to disk.
        
        Args:
            state: State dictionary to save
        """
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            print(f"[StateManager] Error saving state: {e}")
    
    def append_history(self, entry: Dict[str, Any]) -> None:
        """
        Append a conversation turn to history.
        
        Args:
            entry: Dictionary with turn data (prompt, response, action, result)
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in entry:
                entry['timestamp'] = datetime.now().isoformat()
            
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except IOError as e:
            print(f"[StateManager] Error appending history: {e}")
    
    def load_history(self, limit: Optional[int] = None) -> list:
        """
        Load conversation history.
        
        Args:
            limit: Maximum number of entries to return (None = all)
        
        Returns:
            List of history entries
        """
        history = []
        
        if not self.history_file.exists():
            return history
        
        try:
            with open(self.history_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            history.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except IOError as e:
            print(f"[StateManager] Error loading history: {e}")
        
        if limit and limit > 0:
            return history[-limit:]
        return history
    
    def clear(self) -> None:
        """Clear state and history for this project."""
        if self.state_file.exists():
            self.state_file.unlink()
        if self.history_file.exists():
            self.history_file.unlink()
        print(f"[StateManager] Cleared state for project '{self.project_name}'")
    
    def get_project_path(self) -> Path:
        """Return the project directory path."""
        return self.project_dir
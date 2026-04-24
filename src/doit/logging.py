import json
import os
from datetime import datetime

class ProjectLogger:
    def __init__(self, project_root: str):
        self.project_root = project_root
        os.makedirs(self.project_root, exist_ok=True)
        self.log_path = os.path.join(self.project_root, "agent_log.jsonl")

    def log(self, action_type: str, details: dict,
            autonomy_mode: int, approved: bool | None = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action_type": action_type,
            "details": details,
            "autonomy_mode": autonomy_mode,
            "approved": approved,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

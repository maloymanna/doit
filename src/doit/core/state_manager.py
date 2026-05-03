# src/doit/core/state_manager.py [MOD v1.3]
# Fixed: Explicit connection closing to prevent Win32 PermissionError [32]
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, List

class SQLiteStateManager:
    def __init__(self, workspace_dir: Path):
        self.db_path = workspace_dir / "sqlite" / "doit_state.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        repo_root = Path(__file__).resolve().parents[3]
        schema_path = repo_root / "sql" / "schema.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Database schema missing at {schema_path}")
            
        with schema_path.open("r", encoding="utf-8") as f:
            schema = f.read()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(schema)
        finally:
            conn.close()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _exec_and_close(self, sql: str, params: Optional[tuple] = None, fetch: bool = False):
        conn = self._get_conn()
        try:
            cursor = conn.execute(sql, params) if params else conn.execute(sql)
            conn.commit()
            if fetch:
                return cursor.fetchall()
        finally:
            conn.close()

    def create_goal(self, goal_id: str, project: str, query: str, max_steps: int = 15) -> str:
        self._exec_and_close(
            "INSERT OR IGNORE INTO goals (goal_id, project, query, max_steps) VALUES (?, ?, ?, ?)",
            (goal_id, project, query, max_steps)
        )
        return goal_id

    def update_goal_status(self, goal_id: str, status: str, plan_json: Optional[str] = None, step: Optional[int] = None):
        fields, vals = ["status = ?"], [status]
        if plan_json:
            fields.append("plan_json = ?")
            vals.append(plan_json)
        if step is not None:
            fields.append("current_step = ?")
            vals.append(step)
        fields.append("updated_at = datetime('now')")
        vals.append(goal_id)

        self._exec_and_close(f"UPDATE goals SET {', '.join(fields)} WHERE goal_id = ?", tuple(vals))

    def log_step(self, goal_id: str, step_index: int, tool_name: str, params: dict, result: str, rationale: str, status: str = "completed"):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO steps (goal_id, step_index, tool_name, parameters, result, rationale, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (goal_id, step_index, tool_name, json.dumps(params), result, rationale, status)
            )
            conn.execute("UPDATE goals SET current_step = ?, updated_at = datetime('now') WHERE goal_id = ?", (step_index + 1, goal_id))
            conn.commit()
        finally:
            conn.close()

    def log_audit(self, goal_id: str, event_type: str, prompt_snippet: str, response_snippet: str):
        p_hash = hashlib.sha256(prompt_snippet.encode()).hexdigest()[:12]
        self._exec_and_close(
            "INSERT INTO audit_log (goal_id, event_type, prompt_hash, response_snippet) VALUES (?, ?, ?, ?)",
            (goal_id, event_type, p_hash, response_snippet)
        )

    def get_goal_state(self, goal_id: str) -> Optional[Dict[str, Any]]:
        rows = self._exec_and_close("SELECT * FROM goals WHERE goal_id = ?", (goal_id,), fetch=True)
        return dict(rows[0]) if rows else None

    def get_recent_context(self, goal_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        rows = self._exec_and_close(
            "SELECT step_index, tool_name, parameters, result, rationale, status FROM steps WHERE goal_id = ? ORDER BY step_index DESC LIMIT ?",
            (goal_id, limit), fetch=True
        )
        return [dict(r) for r in rows][::-1]
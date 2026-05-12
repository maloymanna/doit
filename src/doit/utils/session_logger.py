# src/doit/utils/session_logger.py [v1.3]
import logging
import sys
import secrets
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

class SessionContext:
    def __init__(self, session_id: str, log_file: Path):
        self.id = session_id
        self.log_file = log_file

def _load_log_level() -> str:
    cfg_path = Path.home() / ".doit" / "config.yaml"
    if cfg_path.exists():
        try:
            with open(cfg_path) as f:
                data = yaml.safe_load(f)
            return data.get("logging", {}).get("level", "INFO").upper()
        except Exception:
            pass
    return "INFO"

def init_session_logger(workspace_dir: Optional[Path] = None) -> SessionContext:
    level_str = _load_log_level()
    level = getattr(logging, level_str, logging.INFO)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(3)
    session_id = f"{ts}_{rand}"
    
    if workspace_dir:
        base_dir = workspace_dir / ".doit" / "sessions"
    else:
        base_dir = Path.home() / ".doit" / "sessions"
    base_dir.mkdir(parents=True, exist_ok=True)
    log_file = base_dir / f"{session_id}_session.log"

    logger = logging.getLogger("doit")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(level)
    
    # ✅ Added filename, function, line number for precise audit/debugging
    fmt = "%(asctime)s [%(levelname)-5s] %(filename)s:%(funcName)s:%(lineno)d | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=True)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info("Session %s started. Log: %s", session_id, log_file)
    return SessionContext(session_id=session_id, log_file=log_file)

logger = logging.getLogger("doit")
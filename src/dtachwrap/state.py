import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import re

DEFAULT_ROOT = Path.home() / ".dtachwrap"

def get_root(root: Optional[Path] = None) -> Path:
    return root if root else DEFAULT_ROOT

def ensure_dirs(root: Path):
    (root / "sockets").mkdir(parents=True, exist_ok=True)
    (root / "meta").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)

@dataclass
class TaskMeta:
    name: str
    dtach_pid: int
    cmd: str
    argv: List[str]
    workdir: str
    socket_path: str
    stdout_path: str
    stderr_path: str
    started_at: str
    child_pid: Optional[int] = None
    
    def save(self, root: Path):
        path = root / "meta" / f"{self.name}.json"
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, name: str, root: Path) -> Optional['TaskMeta']:
        path = root / "meta" / f"{name}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return cls(**data)
        except Exception:
            return None

    @classmethod
    def list_all(cls, root: Path) -> List['TaskMeta']:
        meta_dir = root / "meta"
        if not meta_dir.exists():
            return []
        metas = []
        for p in meta_dir.glob("*.json"):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                metas.append(cls(**data))
            except:
                pass
        return metas

def sanitize_name(name: str) -> str:
    # [A-Za-z0-9._-]
    # Also replacing invalid chars with _ as requested or just validating?
    # User said: "sanitize (allow ... others to _)"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)

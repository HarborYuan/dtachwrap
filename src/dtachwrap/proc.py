import os
import signal
import subprocess
from typing import Optional, List

def is_alive(pid: int) -> bool:
    if pid <= 0: return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def get_children_pids(ppid: int) -> List[int]:
    """Returns list of child PIDs for a given PPID."""
    try:
        # Use pgrep -P <ppid> which is available on both Linux and macOS
        out = subprocess.check_output(["pgrep", "-P", str(ppid)], text=True)
        return [int(x) for x in out.strip().split() if x.strip()]
    except Exception:
        # fallback or empty
        return []

def kill_process(pid: int, sig=signal.SIGTERM):
    try:
        os.kill(pid, sig)
    except OSError:
        pass

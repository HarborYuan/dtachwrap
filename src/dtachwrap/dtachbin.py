import sys
import os
import stat
import shutil
import subprocess
from pathlib import Path

# Path to the vendor bin directory relative to this file
# src/dtachwrap/dtachbin.py -> src/dtachwrap/_vendor/bin/dtach
PACKAGE_DIR = Path(__file__).parent
INTERNAL_BIN = PACKAGE_DIR / "_vendor" / "bin" / "dtach"

def get_dtach_path() -> str:
    """
    Returns the path to the dtach executable.
    Prioritizes the vendored binary.
    Falls back to system 'dtach'.
    Raises FileNotFoundError if neither is found.
    """
    # 1. Check internal binary
    if INTERNAL_BIN.is_file():
        # Ensure executable
        try:
            st = os.stat(INTERNAL_BIN)
            # Check if executable by owner
            if not (st.st_mode & stat.S_IXUSR):
                os.chmod(INTERNAL_BIN, st.st_mode | stat.S_IXUSR)
        except OSError:
            pass # Best effort
        return str(INTERNAL_BIN.absolute())
    
    # 2. Check system path
    system_dtach = shutil.which("dtach")
    if system_dtach:
        return system_dtach
    
    raise FileNotFoundError("dtach binary not found in package nor in PATH.")

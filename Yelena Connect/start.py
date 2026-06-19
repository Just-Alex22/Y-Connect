#!/usr/bin/env python3
"""Y-Connect launcher — starts the backend bridge + Flutter UI together."""

import subprocess, sys, os, signal, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    # Launch backend bridge (it will launch Flutter itself)
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT_DIR / "backend_bridge.py")],
        cwd=str(SCRIPT_DIR),
    )

    # Forward signals to child
    def _sig(sig, frame):
        proc.send_signal(sig)
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _sig)

    proc.wait()
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
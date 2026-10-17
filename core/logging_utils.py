"""
logging_utils.py
-----------------
Small colour-coded console logger. Generic, reused as-is from the original
script's logging helpers (nothing site-specific or evasive in here).
"""

import os
from datetime import datetime

try:
    import colorama
    colorama.init(autoreset=True)
except ImportError:
    pass

_NO_COLOR = os.getenv("NO_COLOR", "") != ""

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def _c(text, color):
    if _NO_COLOR:
        return text
    return f"{color}{text}{RESET}"


def log(msg, tag=None):
    stamp = f"[{datetime.now():%H:%M:%S}]"
    prefix = f"[{tag}] " if tag else ""
    print(f"{stamp} {prefix}{msg}")


def ok(msg, tag=None):
    log(_c(f"[OK]    {msg}", GREEN), tag)


def err(msg, tag=None):
    log(_c(f"[ERROR] {msg}", RED), tag)


def warn(msg, tag=None):
    log(_c(f"[WARN]  {msg}", YELLOW), tag)


def debug(msg, tag=None):
    log(_c(f"[DEBUG] {msg}", CYAN), tag)

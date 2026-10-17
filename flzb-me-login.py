"""
flzb-me-login.py
----------------
Auto-generated standalone bot script (2026-10-10 03:37).
Source: config/flzb-me-login.yaml

Runs independently of config/*.yaml and run_all.py - just:
    python bots/flzb-me-login.py
    python bots/flzb-me-login.py --headless

Edit CONFIG below directly to change field values, the URL, success/failure
text, etc. - or regenerate this file from an updated YAML with:
    python export_bot.py config/flzb-me-login.yaml
"""

import argparse
import sys
import os

# Make sure "core" is importable whether this file is run from the project
# root or from within bots/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.driver_manager import DriverManager
from core.runner import run_fill_once, run_monitor


CONFIG = {   'name': 'flzb-me-login',
    'url': 'https://flzb.me/login',
    'mode': 'fill_once',
    'profile': 'flzb-me-login',
    'wait_for_text': 'FLZB .ME',
    'fields': [   {   'selector': "[name='password']",
                      'type': 'text',
                      'value': os.getenv('FLZB_PASSWORD', '')}],
    'submit': {'selector': '#searchForm button'},
    'success_if_contains': ['thank', 'success'],
    'failure_if_contains': ['error', 'required', 'invalid', 'failed']}


def main():
    parser = argparse.ArgumentParser(description="Run the 'flzb-me-login' bot.")
    parser.add_argument("--headless", action="store_true", default=None,
                         help="Override the profile's saved headless setting")
    parser.add_argument("--password", default=None,
                         help="FLZB login password (or set via FLZB_PASSWORD env var)")
    args = parser.parse_args()

    # Resolve password
    pwd = args.password or os.getenv("FLZB_PASSWORD") or CONFIG['fields'][0]['value']
    if not pwd:
        pwd = input("Enter FLZB login password: ").strip()
    CONFIG['fields'][0]['value'] = pwd

    profile_name = CONFIG.get("profile", CONFIG["name"])
    mode = CONFIG.get("mode", "fill_once")

    with DriverManager(profile_name=profile_name, headless=args.headless) as driver:
        if mode == "fill_once":
            run_fill_once(driver, CONFIG)
        elif mode == "monitor":
            run_monitor(driver, CONFIG)
        else:
            raise ValueError(f"Unknown mode {mode!r} in CONFIG")


if __name__ == "__main__":
    main()

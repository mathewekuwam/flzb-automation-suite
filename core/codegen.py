"""
codegen.py
----------
Turns a bot config (the same dict that config/*.yaml loads into) into a
standalone Python script that can be run on its own - `python bots/mybot.py`
- with no YAML file and no `-m core.runner` needed.

The generated script still imports the tested engine functions
(run_fill_once / run_monitor / DriverManager) rather than re-implementing
them, so behaviour is identical to running the same config through
core/runner.py - this is just a different, more portable entry point for
the exact same, already-reviewed logic.
"""

import pprint
from datetime import datetime


SCRIPT_TEMPLATE = '''\
"""
{name}.py
{underline}
Auto-generated standalone bot script ({generated_at}).
Source: {source}

Runs independently of config/*.yaml and run_all.py - just:
    python {rel_path}
    python {rel_path} --headless

Edit CONFIG below directly to change field values, the URL, success/failure
text, etc. - or regenerate this file from an updated YAML with:
    python export_bot.py config/{name}.yaml
"""

import argparse
import sys
import os

# Make sure "core" is importable whether this file is run from the project
# root or from within bots/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.driver_manager import DriverManager
from core.runner import run_fill_once, run_monitor


CONFIG = {config_literal}


def main():
    parser = argparse.ArgumentParser(description="Run the '{name}' bot.")
    parser.add_argument("--headless", action="store_true", default=None,
                         help="Override the profile's saved headless setting")
    args = parser.parse_args()

    profile_name = CONFIG.get("profile", CONFIG["name"])
    mode = CONFIG.get("mode", "fill_once")

    with DriverManager(profile_name=profile_name, headless=args.headless) as driver:
        if mode == "fill_once":
            run_fill_once(driver, CONFIG)
        elif mode == "monitor":
            run_monitor(driver, CONFIG)
        else:
            raise ValueError(f"Unknown mode {{mode!r}} in CONFIG")


if __name__ == "__main__":
    main()
'''


def render_bot_script(cfg: dict, source: str = "(generated in-memory)", rel_path: str = None) -> str:
    """Returns the full Python source for a standalone script that runs `cfg`."""
    name = cfg["name"]
    rel_path = rel_path or f"bots/{name}.py"
    config_literal = pprint.pformat(cfg, indent=4, sort_dicts=False, width=100)
    return SCRIPT_TEMPLATE.format(
        name=name,
        underline="-" * (len(name) + 3),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        source=source,
        rel_path=rel_path,
        config_literal=config_literal,
    )

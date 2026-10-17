"""
runner.py
---------
Generic engine that reads a per-site YAML config and executes it, in one of
two modes:

  fill_once  - load a page, fill in configured fields (a single, fixed set of
               values - no looping over guessed IDs/emails), submit, record
               whether the result message indicates success or failure.
               Intended for QA/regression-testing your own forms.

  monitor    - load a public page on an interval and log/alert when
               configured text appears (or disappears). Intended for
               monitoring pages you have permission to poll (stock/price
               trackers, status pages, etc.)

Add a new bot by adding a new YAML config file under config/ - this file
does not need to change.
"""

import argparse
import json
import os
import time
import yaml
from datetime import datetime

from core.driver_manager import DriverManager
from core.logging_utils import ok, err, warn, log
from core.form_fill import (
    type_into, click, click_by_text, select_autocomplete_option,
    read_result_message, field_is_invalid,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _record(name: str, entry: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{name}.json")
    records = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
            if not isinstance(records, list):
                records = []
        except (json.JSONDecodeError, OSError):
            records = []
    records.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# ---------------- fill_once mode ----------------
def run_fill_once(driver, cfg: dict):
    name = cfg["name"]
    driver.get(cfg["url"])
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    ok(f"Loaded {cfg['url']!r} (title: {driver.title!r})")

    wait_for_text = cfg.get("wait_for_text")
    if wait_for_text:
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(normalize-space(text()), '{wait_for_text}')]")
                )
            )
            ok(f"Confirmed page contains {wait_for_text!r}.")
        except TimeoutException:
            warn(f"Expected text {wait_for_text!r} not found - continuing anyway.")

    invalid_fields = []
    for field in cfg.get("fields", []):
        type_into(driver, field["selector"], str(field["value"]))
        if field_is_invalid(driver, field["selector"]):
            invalid_fields.append(field["selector"])

    auto = cfg.get("autocomplete_field")
    if auto:
        select_autocomplete_option(
            driver, auto["selector"], auto["type_text"],
            exact_match=auto.get("exact_match"),
        )

    submit = cfg.get("submit", {})
    if "selector" in submit:
        click(driver, submit["selector"])
    elif "by_text" in submit:
        click_by_text(driver, submit["by_text"])
    else:
        warn("No submit selector/by_text configured - skipping submit click.")

    message = read_result_message(driver)
    log(f"Result message: {message!r}")

    success_markers = [s.lower() for s in cfg.get("success_if_contains", [])]
    failure_markers = [s.lower() for s in cfg.get("failure_if_contains", [])]
    low = (message or "").lower()

    if failure_markers and any(m in low for m in failure_markers):
        status = "failure"
    elif success_markers and any(m in low for m in success_markers):
        status = "success"
    elif invalid_fields:
        status = "field_invalid"
    else:
        status = "unknown"

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "url": cfg["url"],
        "status": status,
        "message": message,
        "invalid_fields": invalid_fields,
    }
    _record(name, entry)

    if status == "success":
        ok(f"[{name}] Submission succeeded: {message!r}")
    elif status == "failure":
        err(f"[{name}] Submission failed: {message!r}")
    elif status == "field_invalid":
        err(f"[{name}] Fields rejected before submit: {invalid_fields}")
    else:
        warn(f"[{name}] Could not determine outcome; message was: {message!r}")

    return entry


# ---------------- monitor mode ----------------
def run_monitor(driver, cfg: dict):
    name = cfg["name"]
    interval = cfg.get("poll_interval_seconds", 300)
    max_checks = cfg.get("max_checks", 0)
    watch = cfg["watch"]
    alert_if_contains = [s.lower() for s in watch.get("alert_if_contains", [])]
    alert_if_not_contains = [s.lower() for s in watch.get("alert_if_not_contains", [])]

    checks = 0
    while True:
        checks += 1
        driver.get(cfg["url"])
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        try:
            el = driver.find_element(By.CSS_SELECTOR, watch["selector"])
            text = el.text.strip()
        except Exception as e:
            text = None
            warn(f"[{name}] Could not read watched element: {e}")

        low = (text or "").lower()
        alerted = False
        if text is not None:
            if any(m in low for m in alert_if_contains):
                alerted = True
            if alert_if_not_contains and not any(m in low for m in alert_if_not_contains):
                alerted = True

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "check": checks,
            "url": cfg["url"],
            "watched_text": text,
            "alerted": alerted,
        }
        _record(name, entry)

        if alerted:
            ok(f"[{name}] ALERT (check {checks}): watched text = {text!r}")
        else:
            log(f"[{name}] check {checks}: {text!r} (no alert)")

        if max_checks and checks >= max_checks:
            break
        time.sleep(interval)


# ---------------- entry point ----------------
def run(config_path: str, headless: bool = None):
    cfg = load_config(config_path)
    name = cfg["name"]
    mode = cfg.get("mode", "fill_once")
    profile_name = cfg.get("profile", name)  # falls back to one profile per bot name

    with DriverManager(profile_name=profile_name, headless=headless) as driver:
        if mode == "fill_once":
            return run_fill_once(driver, cfg)
        elif mode == "monitor":
            return run_monitor(driver, cfg)
        else:
            raise ValueError(f"Unknown mode {mode!r} in {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Run a bot from a YAML config.")
    parser.add_argument("config", help="Path to a bot config YAML file, e.g. config/mysite.yaml")
    parser.add_argument("--headless", action="store_true", default=None,
                         help="Run Chrome headless (overrides the profile's saved setting)")
    args = parser.parse_args()
    run(args.config, headless=args.headless)


if __name__ == "__main__":
    main()

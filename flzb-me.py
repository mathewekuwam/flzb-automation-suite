"""
flzb-me.py
----------
Auto-generated standalone bot script (2026-10-10 01:54).
Source: config/flzb-me.yaml

Runs independently of config/*.yaml and run_all.py - just:
    python bots/flzb-me.py
    python bots/flzb-me.py --headless

Edit CONFIG below directly to change field values, the URL, success/failure
text, etc. - or regenerate this file from an updated YAML with:
    python export_bot.py config/flzb-me.yaml
"""

import argparse
import sys
import os
import time
import json
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import tempmail_client1
except ImportError:
    tempmail_client1 = None

# Make sure "core" is importable whether this file is run from the project
# root or from within bots/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.driver_manager import DriverManager
from core.runner import run_fill_once, run_monitor
from core.logging_utils import log, ok, warn, err
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException



# ---------- Configuration ----------
API_BASE = os.getenv("MORELOGIN_API_URL", "http://127.0.0.1:40000")
PROFILE_ID = os.getenv("MORELOGIN_PROFILE_ID", "").strip()

# ---------- MoreLogin ----------
def start_profile(_retry=True):
    url = f"{API_BASE}/api/env/start"
    log(f"Starting profile {PROFILE_ID} via {url}")
    try:
        r = requests.post(url, json={"envId": PROFILE_ID, "isHeadless": False}, timeout=90)
    except requests.exceptions.ConnectionError:
        err(f"Cannot reach MoreLogin at {API_BASE}. Is the MoreLogin app open and the Local API on 'Normal'?")
        raise SystemExit(1)
    except requests.exceptions.Timeout:
        err("MoreLogin did not answer within 90s.")
        raise SystemExit(1)

    if r.status_code != 200:
        err(f"MoreLogin returned HTTP {r.status_code}.")
        raise SystemExit(1)

    try:
        body = r.json()
    except ValueError:
        err("MoreLogin response was not JSON.")
        raise SystemExit(1)

    if body.get("code") != 0:
        err(f"MoreLogin refused to start the profile: code={body.get('code')} msg={body.get('msg')}")
        raise SystemExit(1)

    data = body.get("data") or {}
    port = data.get("debugPort")
    if not port:
        err(f"No debugPort in response: {body}")
        raise SystemExit(1)
    driver_path = data.get("webdriver") or data.get("webdriverPath")

    if not driver_path and _retry:
        warn("No webdriver path returned - the profile was probably already open. Closing it and starting fresh.")
        close_profile(PROFILE_ID)
        time.sleep(3)
        return start_profile(_retry=False)

    if not driver_path:
        err("MoreLogin still did not return a webdriver path after restarting the profile.")

    ok(f"Profile started. debugPort={port}, driver={driver_path}")
    return port, driver_path


def close_profile(env_id):
    try:
        r = requests.post(f"{API_BASE}/api/env/close", json={"envId": env_id}, timeout=30)
        if r.status_code == 200 and r.json().get("code") == 0:
            ok(f"Profile {env_id} closed.")
            return True
        warn(f"MoreLogin did not confirm the profile closed: HTTP {r.status_code} {r.text[:200]}")
    except Exception as e:
        warn(f"Could not close profile {env_id}: {e}")
    return False


def attach_driver(port, driver_path):
    options = webdriver.ChromeOptions()
    options.debugger_address = f"127.0.0.1:{port}"
    if driver_path and os.path.exists(driver_path):
        service = Service(executable_path=driver_path)
    else:
        service = Service()
    try:
        d = webdriver.Chrome(service=service, options=options)
        ok("Selenium attached to the browser.")
        return d
    except WebDriverException as e:
        err(f"Could not attach: {e}")
        raise SystemExit(1)


CONFIG = {   'name': 'flzb-me',
    'url': 'https://flzb.me/',
    'mode': 'fill_once',
    'profile': 'flzb-me',
    'wait_for_text': '',
    'fields': [   {'selector': '#state', 'value': 'AL'},
                  {'selector': "[name='dob']", 'value': '1998'}],
    'submit': {'by_text': 'Search'}}


LOGS_DIR = os.path.join("logs", "flzb-me")


def is_already_logged(state, year):
    """
    Checks if a valid, non-empty results file exists in logs/flzb-me/ (or logs/).
    Ignores corrupted 106-byte files that have empty result_table.
    """
    check_dirs = [LOGS_DIR, "logs"]
    for d in check_dirs:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.startswith(f"results_{state}_{year}_") and f.endswith(".json"):
                file_path = os.path.join(d, f)
                try:
                    if os.path.getsize(file_path) <= 150:
                        with open(file_path, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            txt = data.get("result_table", "").strip()
                            if not txt or txt == "Name Address City State Zip Phone SSN DOB":
                                continue
                    return True
                except Exception:
                    pass
    return False


def extract_flzb_records(driver):
    """
    Extracts structured individual person records from the #result_table DOM.
    Returns a list of dicts with first_name, last_name, middle_name, full_name,
    address, city, state, zip, phone, ssn, dob, dob_month, dob_day, dob_year.
    """
    js_code = """
    const rows = Array.from(document.querySelectorAll('#result_table tr')).filter(r => r.querySelector('td'));
    return rows.map((r, idx) => {
        const getText = (sel) => {
            const el = r.querySelector(sel);
            return el ? el.innerText.trim() : '';
        };
        const name = getText('.name');
        const parts = name.split(/\\s+/).filter(Boolean);
        const firstName = parts[0] || '';
        const lastName = parts.length > 1 ? parts[parts.length - 1] : '';
        const middleName = parts.length > 2 ? parts.slice(1, -1).join(' ') : '';
        
        const dob = getText('.dob');
        const dobParts = dob ? dob.split('/') : [];
        const dobMonth = (dobParts[0] && dobParts[0] !== 'XX') ? dobParts[0] : null;
        const dobDay = (dobParts[1] && dobParts[1] !== 'XX') ? dobParts[1] : null;
        const dobYear = (dobParts[2] && dobParts[2] !== 'XX') ? dobParts[2] : null;

        const stateEl = r.children.length > 3 ? r.children[3] : null;
        const state = stateEl ? stateEl.innerText.trim() : '';

        return {
            id: idx + 1,
            first_name: firstName,
            last_name: lastName,
            middle_name: middleName,
            full_name: name,
            address: getText('.address'),
            city: getText('.city'),
            state: state,
            zip: getText('.zip'),
            phone: getText('.phone'),
            ssn: getText('.ssn'),
            dob: dob,
            dob_month: dobMonth,
            dob_day: dobDay,
            dob_year: dobYear
        };
    });
    """
    try:
        records = driver.execute_script(js_code)
        if isinstance(records, list):
            return records
    except Exception:
        pass
    return []


def wait_for_flzb_results(driver, timeout=35):
    """
    Waits for the search to complete on flzb.me by monitoring #result, #loader, and #result_table.
    Returns:
        (status, row_count, result_heading)
        status: 'found', 'zero_results', or 'timeout'
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 1. Check loader element
            loader_visible = False
            try:
                loader = driver.find_element(By.ID, "loader")
                loader_visible = loader.is_displayed()
            except NoSuchElementException:
                pass

            # 2. Check heading #result
            heading_text = ""
            try:
                heading_el = driver.find_element(By.ID, "result")
                heading_text = heading_el.text.strip().lower()
            except NoSuchElementException:
                pass

            # 3. Check data rows in #result_table
            data_cells = driver.find_elements(By.CSS_SELECTOR, "#result_table td.name, #result_table td")

            # If loader is done:
            if not loader_visible:
                # If we have actual table rows, search has succeeded!
                if len(data_cells) > 0:
                    return "found", len(data_cells), heading_text

                # If heading explicitly confirms 0 results
                if "0 results" in heading_text or "no results" in heading_text:
                    return "zero_results", 0, heading_text

                # If heading changed away from "Enter parameters and hit Search"
                if heading_text and "enter parameters" not in heading_text and "searching" not in heading_text:
                    m = re.search(r"(\d+)\s+results?", heading_text)
                    if m:
                        count = int(m.group(1))
                        return ("found" if count > 0 else "zero_results"), count, heading_text
        except Exception:
            pass
        time.sleep(1)

    return "timeout", 0, ""


def click_all_load_more(driver):
    """
    Scrolls down and clicks 'Load More' until all pages are loaded.
    """
    attempts = 0
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        try:
            load_more = None
            for sel in ["#load_next_button", "//*[normalize-space(text())='Load More']"]:
                try:
                    if sel.startswith("//"):
                        btn = driver.find_element(By.XPATH, sel)
                    else:
                        btn = driver.find_element(By.CSS_SELECTOR, sel)
                    if btn.is_displayed() and btn.is_enabled():
                        load_more = btn
                        break
                except NoSuchElementException:
                    continue

            if not load_more:
                break

            prev_cells = len(driver.find_elements(By.CSS_SELECTOR, "#result_table td.name, #result_table td"))
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", load_more)
                time.sleep(0.5)
                load_more.click()
            except WebDriverException:
                driver.execute_script("arguments[0].click();", load_more)

            ok("Clicked 'Load More'")
            attempts += 1

            # Wait up to 8s for new rows to load
            start_load = time.time()
            rows_increased = False
            while time.time() - start_load < 8:
                time.sleep(1)
                curr_cells = len(driver.find_elements(By.CSS_SELECTOR, "#result_table td.name, #result_table td"))
                if curr_cells > prev_cells:
                    rows_increased = True
                    break

            if not rows_increased and not load_more.is_displayed():
                break

        except (NoSuchElementException, WebDriverException):
            break


def attach_tempmail_to_records(records):
    """
    Generates disposable email addresses for records using first_name and last_name via tempmail.lol.
    Adds 'email' and 'email_token' keys to each record in-place.
    """
    if tempmail_client1 is None:
        warn("tempmail_client1 module not available; skipping email generation.")
        return records

    log(f"Generating tempmail.lol emails for {len(records)} records using first and last name...")
    created = 0
    for rec in records:
        fn = rec.get("first_name", "")
        ln = rec.get("last_name", "")
        try:
            addr, token = tempmail_client1.create_email_for_name(fn, ln)
            rec["email"] = addr
            rec["email_token"] = token
            created += 1
            log(f"  Record #{rec.get('id', created)}: {fn} {ln} -> {addr}")
        except Exception as e:
            warn(f"  Could not create email for {fn} {ln}: {e}")
    ok(f"Generated {created}/{len(records)} tempmail addresses.")
    return records


def main():
    parser = argparse.ArgumentParser(description="Run the 'flzb-me' bot.")
    parser.add_argument("--headless", action="store_true", default=None,
                         help="Override the profile's saved headless setting")
    parser.add_argument("--create-emails", "--tempmail", dest="create_emails", action="store_true", default=False,
                         help="Automatically generate tempmail.lol email addresses for scraped records using first & last name")
    parser.add_argument("--auto-signup", action="store_true", default=False,
                         help="Automatically run signup-bot for scraped records")
    parser.add_argument("--signup-limit", type=int, default=1,
                         help="Number of records to auto-signup when --auto-signup is set (default: 1)")
    args = parser.parse_args()

    profile_name = CONFIG.get("profile", CONFIG["name"])
    mode = CONFIG.get("mode", "fill_once")

    global PROFILE_ID
    if not PROFILE_ID:
        PROFILE_ID = input("Enter the numeric MoreLogin environment ID: ").strip()

    if not PROFILE_ID.isdigit():
        err("The MoreLogin environment ID must be numeric.")
        sys.exit(1)

    port, driver_path = start_profile()
    driver = None
    try:
        driver = attach_driver(port, driver_path)
        
        # Check login status
        driver.get(CONFIG["url"])
        time.sleep(2)
        if "login" in driver.current_url.lower() or driver.find_elements(By.CSS_SELECTOR, "[name='password']"):
            log("User not logged in. Running flzb-me-login.py...")
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("login_module", os.path.join(os.path.dirname(os.path.abspath(__file__)), "flzb-me-login.py"))
                login_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(login_module)
                LOGIN_CONFIG = login_module.CONFIG
                LOGIN_CONFIG['wait_for_text'] = ''
                run_fill_once(driver, LOGIN_CONFIG)
                log("Login submitted. Waiting for redirect...")
                time.sleep(3)
            except Exception as e:
                err(f"Failed to run login script: {e}")
        else:
            ok("User is already logged in.")
        
        if mode == "fill_once":
            STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                      'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                      'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                      'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                      'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
            
            # Configure year range here as needed
            YEARS = [str(y) for y in range(1980, 2005)]
            
            os.makedirs("logs", exist_ok=True)
            for state in STATES:
                for year in YEARS:
                    if is_already_logged(state, year):
                        log(f"--- Skipping State: {state}, Year: {year} (already logged) ---")
                        continue

                    log(f"--- Processing State: {state}, Year: {year} ---")

                    # Retry loop (up to 3 attempts) to guard against network lags or slow queries
                    max_attempts = 3
                    scrape_successful = False

                    for attempt in range(1, max_attempts + 1):
                        CONFIG['fields'] = [
                            {'selector': '#state', 'value': state},
                            {'selector': "[name='dob']", 'value': year}
                        ]

                        run_fill_once(driver, CONFIG)

                        log(f"Waiting for results to load for {state} {year} (attempt {attempt}/{max_attempts})...")
                        status, count, heading = wait_for_flzb_results(driver, timeout=35)

                        if status == "found":
                            ok(f"Search results loaded for {state} {year} ({count} initial records). Loading all pages...")
                            click_all_load_more(driver)

                            records = extract_flzb_records(driver)
                            if getattr(args, "create_emails", False) or getattr(args, "auto_signup", False):
                                attach_tempmail_to_records(records)

                            result_text = driver.find_element(By.ID, "result_table").text.strip()
                            log(f"All Results Found for {state} {year} ({len(records)} records):\n{result_text[:500]}...")

                            os.makedirs(LOGS_DIR, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            json_path = os.path.join(LOGS_DIR, f"results_{state}_{year}_{timestamp}.json")
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump({
                                    "state": state, 
                                    "year": year, 
                                    "timestamp": timestamp, 
                                    "total_records": len(records),
                                    "records": records,
                                    "result_table": result_text
                                }, f, indent=4)
                            ok(f"Saved {len(records)} structured results to {json_path}")

                            if getattr(args, "auto_signup", False) and records:
                                log(f"Triggering auto-signup for first {args.signup_limit} record(s)...")
                                try:
                                    import importlib.util
                                    spec = importlib.util.spec_from_file_location("signup_bot_module", os.path.join(os.path.dirname(os.path.abspath(__file__)), "signup-bot.py"))
                                    signup_bot_mod = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(signup_bot_mod)
                                    for rec in records[:args.signup_limit]:
                                        log(f"Starting signup flow for {rec.get('full_name')} ({rec.get('email')})...")
                                        signup_bot_mod.run_signup_bot(driver, rec)
                                except Exception as e:
                                    err(f"Error during auto-signup: {e}")

                            scrape_successful = True
                            break

                        elif status == "zero_results":
                            ok(f"Confirmed 0 results found for {state} {year} ({heading}).")
                            os.makedirs(LOGS_DIR, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            json_path = os.path.join(LOGS_DIR, f"results_{state}_{year}_{timestamp}.json")
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump({
                                    "state": state, 
                                    "year": year, 
                                    "timestamp": timestamp, 
                                    "total_records": 0,
                                    "records": [],
                                    "result_table": "0 results found"
                                }, f, indent=4)
                            ok(f"Saved 0-results confirmation to {json_path}")
                            scrape_successful = True
                            break

                        else:  # timeout
                            warn(f"Search results did not load in time for {state} {year} (attempt {attempt}/{max_attempts}).")
                            time.sleep(3)

                    if not scrape_successful:
                        err(f"Could not load results for State: {state}, Year: {year} after {max_attempts} attempts. Moving to next.")
        elif mode == "monitor":
            run_monitor(driver, CONFIG)
        else:
            raise ValueError(f"Unknown mode {mode!r} in CONFIG")
    finally:
        log("Closing the MoreLogin profile...")
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        close_profile(PROFILE_ID)


if __name__ == "__main__":
    main()

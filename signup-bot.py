"""
signup-bot.py
-------------
Auto-generated standalone bot script for StudentAid account creation.

Single Record Usage:
    python signup-bot.py
    python signup-bot.py --record-index 3
    python signup-bot.py --from-log latest --record-index 5
    python signup-bot.py --email user@example.com --first John --last Doe --day 15 --month 05 --year 1990 --ssn 000-00-0000

Batch Mode Usage:
    python signup-bot.py --limit 5                   # Process next 5 records
    python signup-bot.py --range 0..10               # Process record indices 0 through 10
    python signup-bot.py --all                       # Process all records in the log
    python signup-bot.py --limit 10 --skip-completed # Automatically skip already processed records
    python signup-bot.py --limit 5 --dry-run         # Preview batch queue without launching browser
"""

import argparse
import sys
import os
import re
import time
import json
import requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import tempmail_client1
except ImportError:
    tempmail_client1 = None

# Make sure "core" is importable whether this file is run from the project
# root or from within bots/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.driver_manager import DriverManager
    from core.logging_utils import log, ok, warn, err, debug
except ImportError:
    # Standalone fallbacks if core is not in path
    DriverManager = None

    def log(msg):
        print(f"[{datetime.now():%H:%M:%S}] {msg}")

    def ok(msg):
        print(f"[{datetime.now():%H:%M:%S}] [OK]    {msg}")

    def warn(msg):
        print(f"[{datetime.now():%H:%M:%S}] [WARN]  {msg}")

    def err(msg):
        print(f"[{datetime.now():%H:%M:%S}] [ERROR] {msg}")

    def debug(msg):
        print(f"[{datetime.now():%H:%M:%S}] [DEBUG] {msg}")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException,
)


# ---------- Configuration ----------
API_BASE = os.getenv("MORELOGIN_API_URL", "http://127.0.0.1:40000")
PROFILE_ID = os.getenv("MORELOGIN_PROFILE_ID", "").strip()

CONFIG = {
    'name': 'signup-bot',
    'url': 'https://studentaid.gov/fsa-id/create-account/launch',
    'mode': 'signup',
    'profile': 'signup-bot',
    'output_file': 'AutoSignup/results.json',
    'defaults': {
        'email': os.getenv('USER_EMAIL', 'user@example.com'),
        'first_name': os.getenv('USER_FIRST_NAME', 'John'),
        'last_name': os.getenv('USER_LAST_NAME', 'Doe'),
        'dob_month': os.getenv('DOB_MONTH', '01'),
        'dob_day': os.getenv('DOB_DAY', '01'),
        'dob_year': os.getenv('DOB_YEAR', '1995'),
        'ssn': os.getenv('USER_SSN', '000-00-0000'),
        'address': os.getenv('USER_ADDRESS', '123 Main St'),
        'address_line2': os.getenv('USER_ADDRESS_LINE2', ''),
        'city': os.getenv('USER_CITY', 'Phoenix'),
        'state': os.getenv('USER_STATE', 'AZ'),
        'zip': os.getenv('USER_ZIP', '85001'),
        'username': os.getenv('USER_USERNAME', None),
        'password': os.getenv('USER_PASSWORD', 'StudentAid2026!#'),
    },
    'steps': [
        {
            'step': 1,
            'type': 'click',
            'label': 'click “Get Started”',
            'selector': '#fsa_Button_GetStarted',
            'xpath': "//button[@id='fsa_Button_GetStarted' or contains(normalize-space(.), 'Get Started')]",
            'url_path': '/fsa-id/create-account/launch',
        },
        {
            'step': 2,
            'type': 'type',
            'key': 'email',
            'ask': 'Email',
            'label': 'type your email',
            'selector': '#fsa_Input_ContactEmailAddress',
            'xpath': "//input[@id='fsa_Input_ContactEmailAddress' or @name='email']",
            'url_path': '/fsa-id/create-account/email-address',
        },
        {
            'step': 3,
            'type': 'click',
            'label': 'click “Continue”',
            'selector': '#fsa_Button_Continue',
            'xpath': "//button[@id='fsa_Button_Continue' or contains(normalize-space(.), 'Continue')]",
            'url_path': '/fsa-id/create-account/email-address',
        },
        {
            'step': 4,
            'type': 'modal_wait',
            'label': 'wait for “Two-Step Verification” modal',
            'selector': '#fsa_ModalDialog_InfoModal_TwoStepVerificationModal',
            'xpath': "//*[@id='fsa_ModalDialog_InfoModal_TwoStepVerificationModal' or contains(normalize-space(.), 'Secure Code Sent')]",
            'url_path': '/fsa-id/create-account/email-address',
        },
        {
            'step': 5,
            'type': 'type',
            'key': 'code',
            'ask': 'Verification code',
            'label': 'enter verification code',
            'selector': '#fsa_Input_EnterVerificationCode',
            'xpath': "//input[@id='fsa_Input_EnterVerificationCode']",
            'in_dialog': True,
            'max_length': 6,
        },
        {
            'step': 6,
            'type': 'click',
            'label': 'click “Continue” in verification dialog',
            'selector': '#fsa_Button_TwoStepVerificationContinue',
            'xpath': "//button[@id='fsa_Button_TwoStepVerificationContinue' or contains(normalize-space(.), 'Continue')]",
            'in_dialog': True,
        },
        {
            'step': 7,
            'type': 'type',
            'key': 'first_name',
            'ask': 'First Name',
            'label': 'enter first name',
            'selector': '#fsa_Input_CreateAccountFirstName',
            'xpath': "//input[@id='fsa_Input_CreateAccountFirstName']",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 8,
            'type': 'type',
            'key': 'last_name',
            'ask': 'Last Name',
            'label': 'enter last name',
            'selector': '#fsa_Input_CreateAccountLastName',
            'xpath': "//input[@id='fsa_Input_CreateAccountLastName']",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 9,
            'type': 'type',
            'key': 'dob_month',
            'ask': 'Month',
            'label': 'enter month of birth (if required)',
            'selector': '#fsa_Input_DateOfBirthMonth',
            'xpath': "//input[@id='fsa_Input_DateOfBirthMonth' or @aria-label='Month']",
            'optional': True,
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 10,
            'type': 'type',
            'key': 'dob_day',
            'ask': 'Day',
            'label': 'enter day of birth',
            'selector': '#fsa_Input_DateOfBirthDay',
            'xpath': "//input[@id='fsa_Input_DateOfBirthDay' or @aria-label='Day']",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 11,
            'type': 'type',
            'key': 'dob_year',
            'ask': 'Year',
            'label': 'enter year of birth',
            'selector': '#fsa_Input_DateOfBirthYear',
            'xpath': "//input[@id='fsa_Input_DateOfBirthYear' or @aria-label='Year']",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 12,
            'type': 'type',
            'key': 'ssn',
            'ask': 'Social Security Number',
            'label': 'enter social security number',
            'selector': '#fsa_Input_Ssn',
            'xpath': "//input[@id='fsa_Input_Ssn' or @name='fsa_ssn']",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 13,
            'type': 'click',
            'label': 'click “Continue” on personal info',
            'selector': '#fsa_Button_PersonalInformationContinue',
            'xpath': "//button[@id='fsa_Button_PersonalInformationContinue' or contains(normalize-space(.), 'Continue')]",
            'url_path': '/fsa-id/create-account/personal-info',
        },
        {
            'step': 14,
            'type': 'click',
            'label': 'click “I don’t have a mobile phone”',
            'selector': '#fsa_Button_DontHaveMobilePhone',
            'xpath': "//*[(self::button or self::a or @role='button') and (contains(normalize-space(.), \"don't have a mobile phone\") or contains(normalize-space(.), \"don’t have a mobile phone\"))]",
            'url_path': '/fsa-id/create-account/mobile-phone-number',
        },
        {
            'step': 15,
            'type': 'type',
            'key': 'address',
            'ask': 'Address Line 1',
            'label': 'enter address line 1',
            'selector': '#fsa_Input_AddressAddressLine1',
            'xpath': "//input[@id='fsa_Input_AddressAddressLine1' or @aria-label='Address Line 1']",
            'url_path': '/fsa-id/create-account/mailing-address',
        },
        {
            'step': 16,
            'type': 'type',
            'key': 'city',
            'ask': 'City',
            'label': 'enter city',
            'selector': '#fsa_Input_AddressCity',
            'xpath': "//input[@id='fsa_Input_AddressCity' or @aria-label='City']",
            'url_path': '/fsa-id/create-account/mailing-address',
        },
        {
            'step': 17,
            'type': 'typeahead',
            'key': 'state',
            'ask': 'State',
            'label': 'enter state',
            'selector': '#fsa_Typeahead_AddressState',
            'xpath': "//input[@id='fsa_Typeahead_AddressState' or @aria-label='State']",
            'url_path': '/fsa-id/create-account/mailing-address',
        },
        {
            'step': 18,
            'type': 'type',
            'key': 'zip',
            'ask': 'Postal Code',
            'label': 'enter postal code',
            'selector': '#fsa_Input_AddressPostalCode',
            'xpath': "//input[@id='fsa_Input_AddressPostalCode' or @aria-label='Postal Code']",
            'url_path': '/fsa-id/create-account/mailing-address',
        },
        {
            'step': 19,
            'type': 'click',
            'label': 'click “Continue” on mailing address',
            'selector': '#fsa_Button_Continue',
            'xpath': "//button[@id='fsa_Button_Continue' or (contains(normalize-space(.), 'Continue') and not(contains(@id, 'Previous')))]",
            'url_path': '/fsa-id/create-account/mailing-address',
        },
        {
            'step': 20,
            'type': 'copy_and_save',
            'label': 'copy backup code',
            'selector': '#fsa_Button_CopyBackupCode',
            'xpath': "//button[@id='fsa_Button_CopyBackupCode' or contains(normalize-space(.), 'Copy Code')]",
            'url_path': '/fsa-id/create-account/two-step-verification',
        },
        {
            'step': 21,
            'type': 'click',
            'label': 'agree to terms and conditions',
            'selector': "label[for='fsa_Checkbox_termsAndConditionsCheckbox']",
            'xpath': "//label[@for='fsa_Checkbox_termsAndConditionsCheckbox' or contains(., \"I agree to Federal Student Aid's\")]",
            'url_path': '/fsa-id/create-account/two-step-verification',
        },
        {
            'step': 22,
            'type': 'click',
            'label': 'click “Create Account” / “Continue”',
            'selector': '#fsa_Button_MfaStep_Continue',
            'xpath': "//button[@id='fsa_Button_MfaStep_Continue' or @id='fsa_Button_Continue' or contains(normalize-space(.), 'Create Account')]",
            'url_path': '/fsa-id/create-account/two-step-verification',
        },
        {
            'step': 23,
            'type': 'verify_and_save',
            'label': 'verify account created and save record',
            'url_path': '/fsa-id/create-account/account-created',
        },
    ]
}


# ---------- MoreLogin Integration ----------
def start_morelogin_profile(_retry=True):
    if not PROFILE_ID:
        debug("No MORELOGIN_PROFILE_ID configured. Using local Chrome browser session.")
        return None, None
    url = f"{API_BASE}/api/env/start"
    log(f"Starting MoreLogin profile {PROFILE_ID} via {url}")
    try:
        r = requests.post(url, json={"envId": PROFILE_ID, "isHeadless": False}, timeout=90)
    except requests.exceptions.ConnectionError:
        warn(f"Cannot reach MoreLogin at {API_BASE}. Falling back to local browser driver.")
        return None, None
    except requests.exceptions.Timeout:
        warn("MoreLogin did not answer within 90s.")
        return None, None

    if r.status_code != 200:
        warn(f"MoreLogin returned HTTP {r.status_code}.")
        return None, None

    try:
        body = r.json()
    except ValueError:
        warn("MoreLogin response was not JSON.")
        return None, None

    if body.get("code") != 0:
        warn(f"MoreLogin refused to start profile: code={body.get('code')} msg={body.get('msg')}")
        return None, None

    data = body.get("data") or {}
    port = data.get("debugPort")
    if not port:
        warn(f"No debugPort in response: {body}")
        return None, None
    driver_path = data.get("webdriver") or data.get("webdriverPath")

    if not driver_path and _retry:
        warn("No webdriver path returned - closing profile and starting fresh.")
        close_morelogin_profile(PROFILE_ID)
        time.sleep(3)
        return start_morelogin_profile(_retry=False)

    ok(f"MoreLogin profile started. debugPort={port}, driver={driver_path}")
    return port, driver_path


def close_morelogin_profile(env_id):
    try:
        r = requests.post(f"{API_BASE}/api/env/close", json={"envId": env_id}, timeout=30)
        if r.status_code == 200 and r.json().get("code") == 0:
            ok(f"MoreLogin profile {env_id} closed.")
            return True
        warn(f"MoreLogin did not confirm profile closed: HTTP {r.status_code} {r.text[:200]}")
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
        ok("Selenium attached to the MoreLogin browser.")
        return d
    except WebDriverException as e:
        err(f"Could not attach to MoreLogin: {e}")
        return None


def restart_browser_session(driver, used_morelogin=False, args=None):
    """
    Closes all browser windows and starts a fresh browser session.
    Fulfills StudentAid's requirement on 'Account Creation Error':
    'close all browser windows and start over'.
    """
    log("Restarting browser session to comply with StudentAid clean session requirement...")
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass

    if used_morelogin and PROFILE_ID:
        close_morelogin_profile(PROFILE_ID)
        time.sleep(5)
        port, driver_path = start_morelogin_profile()
        if port:
            new_driver = attach_driver(port, driver_path)
            if new_driver:
                return new_driver, True

    # Fallback / Local Chrome
    log("Starting fresh standard Chrome session via DriverManager...")
    if DriverManager is not None:
        dm = DriverManager(profile_name=CONFIG["profile"], headless=args.headless if args else None)
        new_driver = dm.start()
    else:
        options = webdriver.ChromeOptions()
        if args and args.headless:
            options.add_argument("--headless=new")
        new_driver = webdriver.Chrome(service=Service(), options=options)
    ok("Fresh browser session started.")
    return new_driver, False


# ---------- Error Handling & Cleanup Helpers ----------
class SignupFormError(Exception):
    """Raised when StudentAid displays an unrecoverable form error banner or dialog."""
    def __init__(self, error_info):
        self.error_info = error_info
        super().__init__(error_info.get("message") or error_info.get("title") or "Signup Form Error")


def print_form_error_banner(err_info):
    """
    Displays a formatted error banner in the terminal so the user immediately
    sees what error occurred on the form.
    """
    title = err_info.get("title", "Signup Form Error")
    msg = err_info.get("message", "")
    url = err_info.get("url", "")

    border = "=" * 78
    now_str = f"[{datetime.now():%H:%M:%S}]"
    print("\n" + border)
    print(f"{now_str} [ERROR] [!] SIGNUP FORM ERROR DETECTED:")
    print(f"{now_str} [ERROR] Title   : {title}")
    if msg and msg.strip() != title.strip():
        print(f"{now_str} [ERROR] Details :")
        for line in msg.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith("http"):
                print(f"{now_str} [ERROR]    {line_s}")
    if url:
        print(f"{now_str} [ERROR] Page    : {url}")
    print(border + "\n")


def detect_page_error(driver):
    """
    Scans the current page for error banners, failure headings, or alert dialogs
    (such as 'Account Already Exists' or 'Can't Create Your Account').
    Returns dict(type, title, message, url) if found, else None.
    """
    if not driver:
        return None

    try:
        curr_url = driver.current_url.lower()

        # 1. Standard FSA Error Banner (id='fsa_Banner_CreateAccountAlert' or class='fsa-banner-error')
        banner_elements = driver.find_elements(
            By.XPATH,
            "//*[@id='fsa_Banner_CreateAccountAlert' or contains(@class, 'fsa-banner-error') or (contains(@class, 'fsa-banner') and @role='alert')]"
        )
        for b in banner_elements:
            try:
                if b.is_displayed():
                    full_text = b.text.strip()
                    if not full_text or any(x in full_text.lower() for x in ['aidan', 'feedback', 'how much money', 'chatbox']):
                        continue

                    header_text = ""
                    try:
                        h_nodes = b.find_elements(
                            By.XPATH,
                            ".//*[contains(@class, 'fsa-banner-content-header') or self::b or self::strong or self::h2 or self::h3 or self::h4]"
                        )
                        vis_h = [h for h in h_nodes if h.is_displayed() and h.text.strip()]
                        if vis_h:
                            header_text = vis_h[0].text.strip()
                    except Exception:
                        pass

                    body_text = ""
                    try:
                        b_nodes = b.find_elements(
                            By.XPATH,
                            ".//*[contains(@class, 'fsa-banner-content-body') or contains(@class, 'fsa-body-text')]"
                        )
                        vis_b = [bd for bd in b_nodes if bd.is_displayed() and bd.text.strip()]
                        if vis_b:
                            body_text = vis_b[0].text.strip()
                    except Exception:
                        pass

                    title = header_text or "Account Creation Error"
                    body_clean = body_text.replace(header_text, "").strip() if (header_text and header_text in body_text) else body_text
                    detail = body_clean or full_text
                    return {
                        "type": "banner_error",
                        "title": title,
                        "message": detail,
                        "url": driver.current_url
                    }
            except Exception:
                pass

        # 2. Known Critical Error Headings / Phrases
        known_xpaths = [
            "//*[(self::h1 or self::h2 or self::h3 or self::b or self::strong or self::div) and (contains(normalize-space(.), \"Can't Create Your Account\") or contains(normalize-space(.), \"Can’t Create Your Account\"))]",
            "//*[(self::h1 or self::h2 or self::h3 or self::b or self::strong or self::div) and contains(normalize-space(.), 'Account Already Exists')]",
            "//*[(self::h1 or self::h2 or self::h3 or self::b or self::strong or self::div) and (contains(normalize-space(.), \"We're Unable to Create Your Account\") or contains(normalize-space(.), \"We’re Unable to Create Your Account\"))]",
            "//*[(self::h1 or self::h2 or self::h3 or self::b or self::strong or self::div) and contains(normalize-space(.), 'Unable to Verify Your Identity')]",
            "//*[(self::h1 or self::h2 or self::h3 or self::b or self::strong or self::div) and contains(normalize-space(.), 'An account with this Social Security number')]",
        ]
        for xp in known_xpaths:
            try:
                nodes = driver.find_elements(By.XPATH, xp)
                for n in nodes:
                    if n.is_displayed():
                        txt = n.text.strip()
                        if txt and len(txt) < 120 and not any(x in txt.lower() for x in ['aidan', 'chat']):
                            desc = txt
                            try:
                                parent = n.find_element(By.XPATH, "./ancestor::div[contains(@class, 'card') or contains(@class, 'banner') or contains(@class, 'container') or @role='alert']")
                                desc = parent.text.strip()
                            except Exception:
                                pass
                            return {
                                "type": "heading_error",
                                "title": txt,
                                "message": desc,
                                "url": driver.current_url
                            }
            except Exception:
                pass

        # 3. URL-based error detection
        if "unable-to-create" in curr_url:
            return {
                "type": "url_error",
                "title": "We're Unable to Create Your Account",
                "message": "Redirected to unable-to-create URL. Mobile phone verification required for this profile.",
                "url": driver.current_url
            }

        # 4. Page source safety-net check for critical error banners
        try:
            page_src = driver.page_source.lower()
            if "account already exists" in page_src and "social security number" in page_src:
                return {
                    "type": "source_error",
                    "title": "Account Already Exists",
                    "message": "An account with this Social Security number (SSN) already exists. You can’t create a new account with this SSN.",
                    "url": driver.current_url
                }
            if "can't create your account" in page_src or "can’t create your account" in page_src:
                return {
                    "type": "source_error",
                    "title": "Can't Create Your Account",
                    "message": "We're unable to create your account at this time. Contact customer support at 1-800-433-3243 for help.",
                    "url": driver.current_url
                }
        except Exception:
            pass

    except Exception:
        pass

    return None


def clear_browser_site_data(driver):
    """
    Purges cookies, local storage, session storage, and cache for studentaid.gov
    so that subsequent signups start with a completely clean session state.
    """
    if not driver:
        return
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    try:
        driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver.execute_cdp_cmd("Storage.clearDataForOrigin", {
            "origin": "https://studentaid.gov",
            "storageTypes": "all"
        })
    except Exception:
        pass
    try:
        driver.execute_script("try { window.localStorage.clear(); window.sessionStorage.clear(); } catch(e){}")
    except Exception:
        pass


def prepare_clean_signup_tab(driver):
    """
    Prepares a clean, dedicated tab for the signup process.
    Closes or resets any dirty tabs from previous runs (e.g. left open on studentaid.gov),
    purges residual site cookies/storage, and ensures a background tab remains
    so that closing the signup tab upon exit leaves the browser on a fresh, clean page.
    """
    if not driver:
        return None

    try:
        handles = list(driver.window_handles)
        log(f"Inspecting existing browser tabs ({len(handles)} open)...")

        # 1. Close or reset any tab from a previous session currently open on studentaid.gov
        for h in list(handles):
            try:
                driver.switch_to.window(h)
                curr_url = driver.current_url.lower()
                if "studentaid.gov" in curr_url:
                    log(f"Found existing StudentAid tab ({h[:8]}...). Cleaning up before new run...")
                    clear_browser_site_data(driver)
                    if len(driver.window_handles) > 1:
                        driver.close()
                    else:
                        driver.get("about:blank")
                        time.sleep(0.3)
            except Exception:
                pass

        # 2. Ensure at least one clean background tab exists, and open our fresh signup tab
        remaining_handles = list(driver.window_handles)
        if len(remaining_handles) == 1:
            # Open a new tab for the signup, leaving the first tab as a clean background tab
            try:
                driver.switch_to.new_window('tab')
            except Exception:
                driver.execute_script("window.open('about:blank', '_blank');")
                time.sleep(0.5)
                for h in driver.window_handles:
                    if h not in remaining_handles:
                        driver.switch_to.window(h)
                        break
        elif len(remaining_handles) > 1:
            try:
                driver.switch_to.new_window('tab')
            except Exception:
                driver.switch_to.window(remaining_handles[-1])

        clear_browser_site_data(driver)
        signup_handle = driver.current_window_handle
        driver.signup_tab_handle = signup_handle
        ok(f"Ready on clean signup tab ({signup_handle[:8]}...).")
        return signup_handle
    except Exception as e:
        warn(f"Note on tab preparation: {e}")
        try:
            driver.signup_tab_handle = driver.current_window_handle
            return driver.signup_tab_handle
        except Exception:
            return None


def close_signup_tab(driver, signup_handle=None):
    """
    Closes the tab that was used for the signup process and purges site data
    so that a crashed or abandoned session is not restored or leaked on subsequent runs.
    """
    if not driver:
        return
    try:
        handles = driver.window_handles
        target = signup_handle if (signup_handle and signup_handle in handles) else None
        if not target and handles:
            target = getattr(driver, "signup_tab_handle", None)
            if target not in handles:
                target = None
        if not target and handles:
            target = driver.current_window_handle

        if target and target in driver.window_handles:
            try:
                driver.switch_to.window(target)
                log(f"Closing signup tab ({target[:8]}...)...")

                # Clear site cookies & storage before navigating away
                clear_browser_site_data(driver)

                # Navigate away from studentaid to about:blank first so Chrome session store won't reopen it
                try:
                    driver.get("about:blank")
                    time.sleep(0.2)
                except Exception:
                    pass

                if len(driver.window_handles) > 1:
                    driver.close()
                    remaining = [h for h in driver.window_handles if h != target]
                    if remaining:
                        driver.switch_to.window(remaining[0])
                ok("Signup tab successfully closed and cleaned.")
            except Exception as e:
                debug(f"Tab close note: {e}")
    except Exception as e:
        warn(f"Error during tab cleanup: {e}")


# ---------- DOM & Interaction Helpers ----------
def find_element_robust(driver, selector=None, xpath=None, tag=None, text=None, timeout=20, check_errors=True):
    """
    Finds element using multiple selector strategies matching runner.js pick/findEl logic.
    Continuously monitors for page error banners during polling.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if check_errors:
            detected_err = detect_page_error(driver)
            if detected_err:
                raise SignupFormError(detected_err)

        # Try CSS selector
        if selector:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    return visible[0]
            except Exception:
                pass

        # Try XPath
        if xpath:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    return visible[0]
            except Exception:
                pass

        # Try text search if button/link/label
        if text:
            try:
                xp = f"//*[(self::button or self::a or self::label or @role='button') and contains(normalize-space(.), '{text}')]"
                elements = driver.find_elements(By.XPATH, xp)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    return visible[0]
            except Exception:
                pass

        time.sleep(0.3)
    return None


def smart_type(driver, element, value, retries=3):
    """
    Clicks field, clears it, sends keys, and dispatches input/change events
    so Angular/React state updates properly (replicating setValue from runner.js).
    """
    value_str = str(value).strip()
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.2)

    for attempt in range(1, retries + 1):
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", element)

        time.sleep(0.1)
        # Clear using keyboard
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)

        # Type the value
        element.send_keys(value_str)

        # Dispatch JS events to update framework models
        driver.execute_script("""
            var el = arguments[0];
            var val = arguments[1];
            if (el.value !== val) {
                el.value = val;
            }
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        """, element, value_str)

        time.sleep(0.3)
        current_val = element.get_attribute("value") or ""
        if current_val.strip() == value_str:
            return True

        # Handle fields that mask input (e.g. •••-••-8001 or ***-**-8001)
        if any(c in current_val for c in ['•', '*', '●']) and len(value_str) >= 4 and current_val.endswith(value_str[-4:]):
            return True

        warn(f"Value '{current_val}' did not match '{value_str}' - retrying ({attempt}/{retries})...")
        time.sleep(0.5)

    return False


def find_show_ssn_button(driver, ssn_element=None):
    """
    Finds the 'Show SSN' button associated with the SSN input.
    """
    if ssn_element:
        try:
            parent = ssn_element.find_element(
                By.XPATH,
                "./ancestor::div[contains(@class, 'input-group') or contains(@class, 'fsa-input')]"
            )
            btns = parent.find_elements(
                By.XPATH,
                ".//button[contains(@id, 'ShowHide') or contains(@id, 'ShowSsn') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show')]"
            )
            visible = [b for b in btns if b.is_displayed()]
            if visible:
                return visible[0]
        except Exception:
            pass

    for sel in [
        "#fsa_Button_SsnShowHide",
        "#fsa_Button_ShowHideSsn",
        "#fsa_Button_ShowSsn",
        "#fsa_Button_SSNShowHide",
        ".fsa-input-button-show-hide button",
    ]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            visible = [b for b in btns if b.is_displayed()]
            if visible:
                return visible[0]
        except Exception:
            pass

    try:
        btns = driver.find_elements(
            By.XPATH,
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show ssn') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show social')]"
        )
        visible = [b for b in btns if b.is_displayed()]
        if visible:
            return visible[0]
    except Exception:
        pass

    return None


def smart_type_ssn(driver, element, ssn_val, retries=3):
    """
    Robustly types and verifies Social Security Number.
    Handles StudentAid's masked display ('•••-••-XXXX') and clicks 'Show SSN'
    button so the full SSN is confirmed in the DOM.
    """
    digits_only = re.sub(r'\D', '', str(ssn_val))
    if len(digits_only) == 9:
        formatted_ssn = f"{digits_only[:3]}-{digits_only[3:5]}-{digits_only[5:]}"
        last_four = digits_only[5:]
    else:
        formatted_ssn = str(ssn_val).strip()
        last_four = digits_only[-4:] if len(digits_only) >= 4 else digits_only

    masked_display = f"***-**-{last_four}"
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.2)

    for attempt in range(1, retries + 1):
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.1)

        # Clear existing text
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)

        # Type formatted SSN steadily
        for char in formatted_ssn:
            element.send_keys(char)
            time.sleep(0.04)

        # Dispatch events so Angular model updates without breaking mask
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        """, element)
        time.sleep(0.4)

        current_val = (element.get_attribute("value") or "").strip()

        # Check if already showing exact value
        if current_val == formatted_ssn or current_val == digits_only:
            ok(f"Entered Social Security Number ({masked_display}).")
            return True

        # Check if masked properly (e.g. '•••-••-8001' or '***-**-8001')
        is_masked_match = (
            any(c in current_val for c in ['•', '*', '●', 'X'])
            and (current_val.endswith(last_four) or bool(re.search(r'\b' + re.escape(last_four) + r'$', current_val)))
        )

        # Click 'Show SSN' button if present to reveal and verify the unmasked value
        btn_show = find_show_ssn_button(driver, ssn_element=element)
        if btn_show:
            btn_text = btn_show.text.strip().lower()
            if "show" in btn_text:
                smart_click(driver, btn_show)
                time.sleep(0.4)
                unmasked_val = (element.get_attribute("value") or "").strip()
                if unmasked_val == formatted_ssn or unmasked_val == digits_only:
                    ok(f"Verified Social Security Number with 'Show SSN': '{masked_display}'")
                    return True
                current_val = unmasked_val

        if is_masked_match:
            ok(f"Entered Social Security Number (masked format confirmed: '{current_val}').")
            return True

        if current_val == formatted_ssn:
            ok(f"Entered Social Security Number ({masked_display}).")
            return True

        warn(f"SSN value '{current_val}' did not match expected '{masked_display}' - retrying ({attempt}/{retries})...")
        time.sleep(0.5)

    return False


def smart_click(driver, element):
    """
    Scrolls to element, clicks, and uses JS click fallback if intercepted.
    """
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.3)
    try:
        element.click()
        return True
    except (ElementClickInterceptedException, WebDriverException):
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            err(f"Click failed: {e}")
            return False


def split_address_city(addr_city):
    """
    Splits combined address_and_city string (e.g. '16103 W Williams St Goodyear')
    into (address_line1, city).
    """
    if not addr_city:
        return "", ""
    s = str(addr_city).strip()
    # Match standard street suffix + optional directional suffix (N/S/E/W/NE/NW/SE/SW) + City
    m = re.search(
        r'^(.*?\b(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|Way|Ct|Court|Cir|Circle|Loop|Pl|Place|Hwy|Highway|Pkwy|Parkway|Ter|Terrace|Trail|Trl|Box\s+\d+|Apt\s+[\w\-]+|Unit\s+[\w\-]+|#\s*[\w\-]+)(?:\s+(?:[NSEW]|North|South|East|West|NE|NW|SE|SW))?)\s+([A-Za-z\s\.\-]+)$',
        s,
        re.I
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    parts = s.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return s, ""


US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "VI": "Virgin Islands", "GU": "Guam"
}


def smart_typeahead(driver, element, value, retries=3):
    """
    Types value into a combobox/typeahead input, waits for dropdown options,
    clicks the matching dropdown item, or falls back to Arrow Down + Enter.
    """
    val_str = str(value).strip()
    full_name = US_STATES.get(val_str.upper(), val_str)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.2)

    for attempt in range(1, retries + 1):
        # On attempt 1 type the value as-is; on attempt 2 type the full state name if different
        type_val = full_name if attempt > 1 and full_name != val_str else val_str
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.1)

        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)

        # Type steadily to trigger Angular typeahead debounce
        for char in type_val:
            element.send_keys(char)
            time.sleep(0.05)

        time.sleep(0.6)

        # Look for visible dropdown items
        dropdown_items = driver.find_elements(
            By.CSS_SELECTOR,
            "ngb-typeahead-window button, .dropdown-menu button, .dropdown-item, [role='option']"
        )
        clicked = False
        for item in dropdown_items:
            try:
                if item.is_displayed():
                    item_text = item.text.strip().lower()
                    if (val_str.lower() in item_text or full_name.lower() in item_text
                            or item_text.startswith(val_str.lower()) or item_text.startswith(full_name.lower())):
                        smart_click(driver, item)
                        clicked = True
                        break
            except Exception:
                pass

        if not clicked and dropdown_items:
            for item in dropdown_items:
                try:
                    if item.is_displayed():
                        smart_click(driver, item)
                        clicked = True
                        break
                except Exception:
                    pass

        if not clicked:
            element.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.1)
            element.send_keys(Keys.ENTER)

        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        """, element)

        time.sleep(0.3)
        cur_val = element.get_attribute("value") or ""
        if cur_val.strip():
            return True

        warn(f"Typeahead value '{cur_val}' empty for '{val_str}' - retrying ({attempt}/{retries})...")
        time.sleep(0.5)

    return False


def find_dont_have_mobile_button(driver, timeout=25):
    """
    Finds the 'I don't have a mobile phone' button/link on the mobile-phone-number page
    using multiple robust selector strategies.
    """
    end_time = time.time() + timeout
    selectors = [
        "#fsa_Button_DontHaveMobilePhone",
        "#fsa_Button_OptOutMobilePhone",
        "#fsa_Button_NoMobilePhone",
        "#fsa_Link_DontHaveMobilePhone",
        "#fsa_Button_OptOut",
        "#fsa_Button_MobileOptOut",
        "button.fsa-btn-cancel",
        "button.fsa-btn-link",
    ]
    xpaths = [
        "//*[(self::button or self::a or @role='button') and (contains(normalize-space(.), \"don't have a mobile phone\") or contains(normalize-space(.), \"don’t have a mobile phone\") or contains(normalize-space(.), \"dont have a mobile phone\"))]",
        "//*[(self::button or self::a or @role='button') and (contains(normalize-space(.), \"I don't have a mobile phone\") or contains(normalize-space(.), \"I don’t have a mobile phone\"))]",
        "//*[(self::button or self::a or @role='button') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mobile phone') and (contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), \"don't\") or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dont') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'without'))]",
    ]

    while time.time() < end_time:
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        for xp in xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xp)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    return visible[0]
            except Exception:
                pass

        for sel in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    if "fsa-btn" in sel:
                        txt = visible[0].text.lower()
                        if "mobile" in txt or "phone" in txt:
                            return visible[0]
                    else:
                        return visible[0]
            except Exception:
                pass

        try:
            candidates = driver.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
            for c in candidates:
                if c.is_displayed():
                    txt = c.text.lower()
                    if ("don't have" in txt or "dont have" in txt or "no mobile" in txt) and ("mobile" in txt or "phone" in txt):
                        return c
        except Exception:
            pass

        time.sleep(0.5)

    return None


def extract_backup_code(driver, timeout=20):
    """
    Extracts the backup code on the two-step-verification page and clicks 'Copy Code'.
    """
    end_time = time.time() + timeout
    backup_code = None

    while time.time() < end_time:
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        btn_copy = None
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "#fsa_Button_CopyBackupCode")
            visible = [b for b in btns if b.is_displayed()]
            if visible:
                btn_copy = visible[0]
            else:
                btns = driver.find_elements(By.XPATH, "//button[contains(normalize-space(.), 'Copy Code')]")
                visible = [b for b in btns if b.is_displayed()]
                if visible:
                    btn_copy = visible[0]
        except Exception:
            pass

        if btn_copy:
            try:
                # Based on two-step-verification.html structure:
                # <div class="fsa-font-size-18 fsa-color-blue-bright-85">GTMCHQKU91XK</div>
                code_els = driver.find_elements(
                    By.XPATH,
                    "//button[@id='fsa_Button_CopyBackupCode' or contains(normalize-space(.), 'Copy Code')]/ancestor::div[contains(@class, 'fsa-bg-color-blue-light-2') or contains(@class, 'd-md-flex') or contains(@class, 'block-sm')]//div[contains(@class, 'fsa-font-size-18')]"
                )
                for ce in code_els:
                    t = ce.text.strip()
                    if t and re.match(r'^[A-Z0-9]{8,16}$', t):
                        backup_code = t
                        break
            except Exception:
                pass

            if not backup_code:
                try:
                    parent_box = btn_copy.find_element(By.XPATH, "./ancestor::div[contains(@class, 'd-md-flex') or contains(@class, 'block-sm')]")
                    m = re.search(r'\b[A-Z0-9]{10,14}\b', parent_box.text)
                    if m:
                        backup_code = m.group(0)
                except Exception:
                    pass

            # Click the Copy Code button
            smart_click(driver, btn_copy)
            time.sleep(0.5)

            if backup_code:
                return backup_code

        # Fallback: scan page for alphanumeric code near 'Backup Code' heading
        try:
            headings = driver.find_elements(By.XPATH, "//*[contains(normalize-space(.), 'Backup Code')]/ancestor::div[contains(@class, 'col-') or contains(@class, 'd-flex')]")
            for h in headings:
                m = re.search(r'\b[A-Z0-9]{10,14}\b', h.text)
                if m and m.group(0) != "BACKUP":
                    return m.group(0)
        except Exception:
            pass

        time.sleep(0.5)

    return backup_code or "NOT_EXTRACTED"


def agree_terms_and_conditions(driver, timeout=15):
    """
    Clicks the 'I agree to Federal Student Aid's terms and conditions' checkbox/label
    on the two-step-verification page.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        label_el = None
        try:
            labels = driver.find_elements(
                By.XPATH,
                "//label[@for='fsa_Checkbox_termsAndConditionsCheckbox' or contains(., \"I agree to Federal Student Aid's\") or contains(., \"I agree to Federal Student Aid’s\")]"
            )
            visible = [l for l in labels if l.is_displayed()]
            if visible:
                label_el = visible[0]
        except Exception:
            pass

        if label_el:
            smart_click(driver, label_el)
            time.sleep(0.5)

        try:
            cb = driver.find_element(By.ID, "fsa_Checkbox_termsAndConditionsCheckbox")
            if cb.is_selected():
                return True
            driver.execute_script("""
                var el = arguments[0];
                if (!el.checked) {
                    el.click();
                    el.checked = true;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, cb)
            time.sleep(0.3)
            if cb.is_selected():
                return True
        except Exception:
            pass

        if label_el:
            return True

        time.sleep(0.5)

    return False


def wait_for_account_created(driver, timeout=35):
    """
    Waits for the account created page / confirmation to appear.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        curr_url = driver.current_url.lower()
        if "account-created" in curr_url:
            return True
        if "account successfully created" in driver.title.lower():
            return True
        try:
            headings = driver.find_elements(
                By.XPATH,
                "//h1[contains(normalize-space(.), 'Your Account Was Successfully Created') or contains(normalize-space(.), 'Account Successfully Created')]"
            )
            if headings and headings[0].is_displayed():
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def save_signup_result(record, output_file="AutoSignup/results.json"):
    """
    Saves record to AutoSignup/results.json (matching runner.js doSave)
    and logs/signup-bot/signup_results_<timestamp>.json.
    """
    # 1. Update output_file (AutoSignup/results.json)
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    records = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data if isinstance(data, list) else [data]
        except Exception:
            records = []

    records.append(record)
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
        ok(f"Saved result to {output_file}")
    except Exception as e:
        warn(f"Failed to save to {output_file}: {e}")

    # 2. Save timestamped copy in logs/signup-bot/
    signup_log_dir = os.path.join("logs", "signup-bot")
    os.makedirs(signup_log_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(signup_log_dir, f"signup_results_{stamp}.json")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=4)
        ok(f"Saved run record to {log_path}")
    except Exception as e:
        warn(f"Failed to save log copy: {e}")


# ---------- Main Bot Runner ----------
def run_signup_bot(driver, data):
    """
    Executes the automated signup workflow for StudentAid.
    Monitors for form errors (e.g. Account Already Exists, Can't Create Your Account)
    at every step and saves detailed records on failure.
    """
    prepare_clean_signup_tab(driver)

    # Ensure username and password defaults are populated in data upfront
    if not data.get("password"):
        data["password"] = CONFIG["defaults"].get("password", "StudentAid2026!#")
    if not data.get("username"):
        if data.get("email") and "@" in data["email"]:
            data["username"] = data["email"].split("@")[0] + str(data.get("dob_year", "99"))
        else:
            data["username"] = f"{data.get('first_name', '')}{data.get('last_name', '')}{data.get('dob_year', '99')}".lower()

    ssn_val = str(data.get("ssn", "")).strip()
    ssn_masked = f"***-**-{ssn_val[-4:]}" if len(ssn_val) >= 4 else "***"

    log("Starting StudentAid Account Signup Automation...")

    try:
        driver.get(CONFIG["url"])
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        ok(f"Loaded {CONFIG['url']} (title: '{driver.title}')")
        time.sleep(2)

        # Check launch page for errors
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 1: Click "Get Started"
        log("Step 1/14: Looking for 'Get Started' button...")
        btn_start = find_element_robust(driver, selector="#fsa_Button_GetStarted", text="Get Started", timeout=25)
        if not btn_start:
            raise RuntimeError("Could not find 'Get Started' button on launch page.")
        smart_click(driver, btn_start)
        ok("Clicked 'Get Started'. Waiting for email page...")
        time.sleep(2)
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 2: Fill Email
        if not data.get("email") and tempmail_client1 is not None:
            log(f"Generating temporary email for {data.get('first_name')} {data.get('last_name')} via tempmail.lol...")
            gen_addr, gen_tok = tempmail_client1.create_email_for_name(data.get("first_name"), data.get("last_name"))
            data["email"] = gen_addr
            data["email_token"] = gen_tok
            ok(f"Generated email: {gen_addr}")

        log(f"Step 2/14: Entering email '{data['email']}'...")
        email_input = find_element_robust(driver, selector="#fsa_Input_ContactEmailAddress", timeout=25)
        if not email_input:
            raise RuntimeError("Could not find email input field (#fsa_Input_ContactEmailAddress).")
        smart_type(driver, email_input, data["email"])
        ok(f"Filled email: '{data['email']}'")
        time.sleep(1)

        # Step 3: Click "Continue"
        log("Step 3/14: Clicking 'Continue'...")
        btn_continue = find_element_robust(driver, selector="#fsa_Button_Continue", text="Continue", timeout=20)
        if not btn_continue:
            raise RuntimeError("Could not find 'Continue' button on email page.")
        smart_click(driver, btn_continue)
        ok("Clicked 'Continue'. Waiting for Two-Step Verification modal...")
        time.sleep(2)

        # Check immediately after email submission (e.g. Can't Create Your Account)
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 4: Wait for Two-Step Verification Modal
        log("Step 4/14: Waiting for Verification Code modal to appear...")
        modal = find_element_robust(
            driver,
            selector="#fsa_ModalDialog_InfoModal_TwoStepVerificationModal",
            xpath="//*[@id='fsa_ModalDialog_InfoModal_TwoStepVerificationModal' or contains(normalize-space(.), 'Secure Code Sent')]",
            timeout=25
        )
        if modal:
            ok("Verification Code modal is displayed.")
        else:
            warn("Modal container not explicitly detected by ID, checking for verification input directly...")

        # Step 5: Verification Code Input
        code_input = find_element_robust(driver, selector="#fsa_Input_EnterVerificationCode", timeout=25)
        if not code_input:
            raise RuntimeError("Could not find verification code input (#fsa_Input_EnterVerificationCode).")

        v_code = data.get("code")
        if not v_code:
            # Check if email is associated with a tempmail token
            token = data.get("email_token")
            if not token and tempmail_client1 is not None and data.get("email"):
                token = tempmail_client1.get_token_for_address(data.get("email"))

            if token and tempmail_client1 is not None:
                log("═" * 60)
                log(f"Waiting for 6-digit verification code sent to {data['email']} via tempmail.lol...")
                try:
                    v_code = tempmail_client1.wait_for_verification_code(
                        token=token,
                        address=data.get("email"),
                        timeout=data.get("email_timeout", 120),
                        poll_interval=3,
                        log_fn=log,
                    )
                except Exception as e:
                    warn(f"Exception while waiting for tempmail code: {e}")

                if v_code:
                    ok(f"Successfully received verification code automatically: {v_code}")
                else:
                    warn("Automated code extraction timed out. Falling back to manual entry.")
                log("═" * 60)

            if not v_code:
                log("═" * 60)
                log(f"A 6-digit verification code was sent to: {data['email']}")
                v_code = input(">> Enter the verification code: ").strip()
                log("═" * 60)

        log(f"Step 5/14: Entering verification code '{v_code}'...")
        smart_type(driver, code_input, v_code)
        ok("Entered verification code.")
        time.sleep(1)

        # Step 6: Click "Continue" in Verification Dialog
        log("Step 6/14: Submitting verification code modal...")
        btn_modal_continue = find_element_robust(
            driver,
            selector="#fsa_Button_TwoStepVerificationContinue",
            xpath="//button[@id='fsa_Button_TwoStepVerificationContinue' or (contains(normalize-space(.), 'Continue') and ancestor::*[@id='fsa_ModalDialog_InfoModal_TwoStepVerificationModal'])]",
            text="Continue",
            timeout=20
        )
        if not btn_modal_continue:
            raise RuntimeError("Could not find 'Continue' button in verification modal.")
        smart_click(driver, btn_modal_continue)
        ok("Submitted verification code. Waiting for Personal Info page...")
        time.sleep(2)

        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 7: Enter First Name
        log(f"Step 7/14: Entering First Name '{data['first_name']}'...")
        first_name_input = find_element_robust(
            driver,
            selector="#fsa_Input_CreateAccountFirstName",
            xpath="//input[@id='fsa_Input_CreateAccountFirstName']",
            timeout=30
        )
        if not first_name_input:
            raise RuntimeError("Could not find First Name input (#fsa_Input_CreateAccountFirstName).")
        smart_type(driver, first_name_input, data["first_name"])
        ok(f"Filled First Name: '{data['first_name']}'")
        time.sleep(0.5)

        # Step 8: Enter Last Name
        log(f"Step 8/14: Entering Last Name '{data['last_name']}'...")
        last_name_input = find_element_robust(
            driver,
            selector="#fsa_Input_CreateAccountLastName",
            xpath="//input[@id='fsa_Input_CreateAccountLastName']",
            timeout=20
        )
        if not last_name_input:
            raise RuntimeError("Could not find Last Name input (#fsa_Input_CreateAccountLastName).")
        smart_type(driver, last_name_input, data["last_name"])
        ok(f"Filled Last Name: '{data['last_name']}'")
        time.sleep(0.5)

        # Step 9: Enter Month (if present on the page)
        if data.get("dob_month"):
            month_input = find_element_robust(
                driver,
                selector="#fsa_Input_DateOfBirthMonth",
                xpath="//input[@id='fsa_Input_DateOfBirthMonth' or @aria-label='Month']",
                timeout=3
            )
            if month_input:
                log(f"Step 9/14: Entering Month '{data['dob_month']}'...")
                smart_type(driver, month_input, data["dob_month"])
                ok(f"Filled Month: '{data['dob_month']}'")
                time.sleep(0.5)
            else:
                debug("Month field not found or not required on this view - continuing.")

        # Step 10: Enter Day
        log(f"Step 10/14: Entering Day '{data['dob_day']}'...")
        day_input = find_element_robust(
            driver,
            selector="#fsa_Input_DateOfBirthDay",
            xpath="//input[@id='fsa_Input_DateOfBirthDay' or @aria-label='Day']",
            timeout=20
        )
        if not day_input:
            raise RuntimeError("Could not find Day input (#fsa_Input_DateOfBirthDay).")
        smart_type(driver, day_input, data["dob_day"])
        ok(f"Filled Day: '{data['dob_day']}'")
        time.sleep(0.5)

        # Step 11: Enter Year
        log(f"Step 11/14: Entering Year '{data['dob_year']}'...")
        year_input = find_element_robust(
            driver,
            selector="#fsa_Input_DateOfBirthYear",
            xpath="//input[@id='fsa_Input_DateOfBirthYear' or @aria-label='Year']",
            timeout=20
        )
        if not year_input:
            raise RuntimeError("Could not find Year input (#fsa_Input_DateOfBirthYear).")
        smart_type(driver, year_input, data["dob_year"])
        ok(f"Filled Year: '{data['dob_year']}'")
        time.sleep(0.5)

        # Step 12: Enter SSN
        log(f"Step 12/14: Entering Social Security Number (masked)...")
        ssn_input = find_element_robust(
            driver,
            selector="#fsa_Input_Ssn",
            xpath="//input[@id='fsa_Input_Ssn' or @name='fsa_ssn' or @aria-label='Social Security Number']",
            timeout=20
        )
        if not ssn_input:
            raise RuntimeError("Could not find SSN input (#fsa_Input_Ssn).")
        smart_type_ssn(driver, ssn_input, data["ssn"])
        time.sleep(1)

        # Step 13: Click "Continue" on Personal Info
        log("Step 13: Clicking 'Continue' on personal information...")
        btn_personal_continue = find_element_robust(
            driver,
            selector="#fsa_Button_PersonalInformationContinue",
            xpath="//button[@id='fsa_Button_PersonalInformationContinue' or contains(normalize-space(.), 'Continue')]",
            text="Continue",
            timeout=20
        )
        if not btn_personal_continue:
            raise RuntimeError("Could not find 'Continue' button on personal info page.")
        smart_click(driver, btn_personal_continue)
        ok("Clicked 'Continue' on Personal Information page. Waiting for Mobile Phone page...")
        time.sleep(2)

        # Check immediately after personal info (e.g. Account Already Exists)
        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 14: Mobile Phone Number - Click "I don't have a mobile phone"
        log("Step 14: Checking for Mobile Phone Number page...")
        phone_wait_end = time.time() + 25
        while time.time() < phone_wait_end:
            detected_err = detect_page_error(driver)
            if detected_err:
                raise SignupFormError(detected_err)
            curr_url = driver.current_url.lower()
            if "mobile-phone-number" in curr_url or "mailing-address" in curr_url:
                break
            time.sleep(0.5)

        current_url = driver.current_url.lower()

        # If already bypassed mobile to mailing-address
        if "mailing-address" in current_url:
            ok("Bypassed mobile phone step directly to 'mailing-address'.")
        else:
            log("Looking for 'I don't have a mobile phone' button/link...")
            btn_no_phone = find_dont_have_mobile_button(driver, timeout=20)
            if not btn_no_phone:
                warn("Could not find 'I don't have a mobile phone' button; checking current URL...")
            else:
                smart_click(driver, btn_no_phone)
                ok("Clicked 'I don't have a mobile phone'.")
                time.sleep(1.5)

                # Check for possible modal confirmation ("Are you sure you don't have a mobile phone?")
                try:
                    modal_confirm = driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'modal') or @role='dialog']//button[contains(normalize-space(.), 'Continue') or contains(normalize-space(.), 'Confirm') or contains(normalize-space(.), 'Yes') or contains(normalize-space(.), 'Proceed') or contains(normalize-space(.), \"Don't Have\")]"
                    )
                    vis_modal_btn = [b for b in modal_confirm if b.is_displayed()]
                    if vis_modal_btn:
                        log("Confirmation dialog detected. Confirming mobile opt-out...")
                        smart_click(driver, vis_modal_btn[0])
                        time.sleep(2)
                except Exception:
                    pass

            # Check redirection result: unable-to-create VS mailing-address
            log("Checking redirection after mobile phone step...")
            redirect_end = time.time() + 20
            landed_on = None

            while time.time() < redirect_end:
                detected_err = detect_page_error(driver)
                if detected_err:
                    raise SignupFormError(detected_err)

                curr_url = driver.current_url.lower()
                page_src = driver.page_source.lower()

                # Case A: redirected to unable-to-create
                if "unable-to-create" in curr_url or "we're unable to create your account" in page_src or "unable to create" in page_src:
                    landed_on = "unable-to-create"
                    break

                # Case B: redirected to mailing-address
                if "mailing-address" in curr_url or "enter your mailing address" in page_src or driver.find_elements(By.ID, "fsa_Input_AddressAddressLine1"):
                    landed_on = "mailing-address"
                    break

                time.sleep(0.5)

            if landed_on == "unable-to-create":
                warn("Redirected to '/mobile-phone-number/unable-to-create'. Mobile phone number is required to proceed.")
                result_record = {
                    "email": data["email"],
                    "email_token": data.get("email_token"),
                    "username": data.get("username"),
                    "password": data.get("password"),
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "dob": f"{data.get('dob_month', 'XX')}/{data['dob_day']}/{data['dob_year']}",
                    "ssn": ssn_masked,
                    "address": data.get("address"),
                    "address_line2": data.get("address_line2"),
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "zip": data.get("zip"),
                    "backup_code": data.get("backup_code"),
                    "status": "unable to create - mobile required",
                    "url": driver.current_url,
                    "time": datetime.now().isoformat(timespec="seconds"),
                }
                save_signup_result(result_record, output_file=CONFIG["output_file"])
                warn(f"Saved run record with status 'unable to create - mobile required' for '{data['email']}'.")
                return result_record

            if landed_on != "mailing-address":
                warn(f"Did not detect explicit 'mailing-address' redirect. Current URL: {driver.current_url}. Attempting to locate address fields...")

        # Step 15: Fill Mailing Address
        log("Step 15: Entering Mailing Address details...")
        addr1_input = find_element_robust(
            driver,
            selector="#fsa_Input_AddressAddressLine1",
            xpath="//input[@id='fsa_Input_AddressAddressLine1' or @aria-label='Address Line 1']",
            timeout=25
        )
        if not addr1_input:
            raise RuntimeError("Could not find Address Line 1 input (#fsa_Input_AddressAddressLine1).")

        log(f"Entering Address Line 1 '{data['address']}'...")
        smart_type(driver, addr1_input, data["address"])
        ok(f"Filled Address Line 1: '{data['address']}'")
        time.sleep(0.5)

        if data.get("address_line2"):
            log(f"Entering Address Line 2 '{data['address_line2']}'...")
            addr2_input = find_element_robust(
                driver,
                selector="#fsa_Input_AddressAddressLine2",
                xpath="//input[@id='fsa_Input_AddressAddressLine2' or @aria-label='Address Line 2']",
                timeout=3
            )
            if addr2_input:
                smart_type(driver, addr2_input, data["address_line2"])
                ok(f"Filled Address Line 2: '{data['address_line2']}'")
                time.sleep(0.5)

        log(f"Entering City '{data['city']}'...")
        city_input = find_element_robust(
            driver,
            selector="#fsa_Input_AddressCity",
            xpath="//input[@id='fsa_Input_AddressCity' or @aria-label='City']",
            timeout=15
        )
        if not city_input:
            raise RuntimeError("Could not find City input (#fsa_Input_AddressCity).")
        smart_type(driver, city_input, data["city"])
        ok(f"Filled City: '{data['city']}'")
        time.sleep(0.5)

        log(f"Entering State '{data['state']}'...")
        state_input = find_element_robust(
            driver,
            selector="#fsa_Typeahead_AddressState",
            xpath="//input[@id='fsa_Typeahead_AddressState' or @aria-label='State']",
            timeout=15
        )
        if not state_input:
            raise RuntimeError("Could not find State typeahead (#fsa_Typeahead_AddressState).")
        smart_typeahead(driver, state_input, data["state"])
        ok(f"Filled State: '{data['state']}'")
        time.sleep(0.5)

        log(f"Entering Postal Code '{data['zip']}'...")
        zip_input = find_element_robust(
            driver,
            selector="#fsa_Input_AddressPostalCode",
            xpath="//input[@id='fsa_Input_AddressPostalCode' or @aria-label='Postal Code']",
            timeout=15
        )
        if not zip_input:
            raise RuntimeError("Could not find Postal Code input (#fsa_Input_AddressPostalCode).")
        smart_type(driver, zip_input, str(data["zip"]))
        ok(f"Filled Postal Code: '{data['zip']}'")
        time.sleep(1)

        # Step 16: Click "Continue" on Mailing Address
        log("Step 16: Clicking 'Continue' on mailing address page...")
        btn_addr_continue = find_element_robust(
            driver,
            selector="#fsa_Button_Continue",
            xpath="//button[@id='fsa_Button_Continue' or (contains(normalize-space(.), 'Continue') and not(contains(@id, 'Previous')))]",
            text="Continue",
            timeout=20
        )
        if not btn_addr_continue:
            raise RuntimeError("Could not find 'Continue' button on mailing address page.")
        smart_click(driver, btn_addr_continue)
        ok("Clicked 'Continue' on Mailing Address. Waiting for next page...")
        time.sleep(2)

        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Safeguard: Check if Username & Password step appears
        if "password" in driver.current_url.lower() or find_element_robust(driver, selector="#fsa_Input_Password", timeout=4):
            log("Username and Password step detected. Completing credentials...")
            pwd_val = data.get("password") or CONFIG["defaults"]["password"]
            user_val = data.get("username") or (data.get("email", "").split("@")[0] + str(data.get("dob_year", "99")) if data.get("email") else f"{data.get('first_name', '')}{data.get('last_name', '')}{data.get('dob_year', '')}".lower())
            data["username"] = user_val
            data["password"] = pwd_val

            uname_input = find_element_robust(driver, selector="#fsa_Input_Username", timeout=5)
            if uname_input:
                smart_type(driver, uname_input, user_val)
                ok(f"Filled Username: {user_val}")

            pwd_input = find_element_robust(driver, selector="#fsa_Input_Password", timeout=5)
            if pwd_input:
                smart_type(driver, pwd_input, pwd_val)
                ok("Filled Password.")

            confirm_pwd_input = find_element_robust(driver, selector="#fsa_Input_ConfirmPassword", timeout=5)
            if confirm_pwd_input:
                smart_type(driver, confirm_pwd_input, pwd_val)
                ok("Filled Confirm Password.")

            btn_pwd_continue = find_element_robust(driver, selector="#fsa_Button_Continue", text="Continue", timeout=10)
            if btn_pwd_continue:
                smart_click(driver, btn_pwd_continue)
                ok("Submitted Username and Password. Waiting for Two-Step Verification...")
                time.sleep(3)
                detected_err = detect_page_error(driver)
                if detected_err:
                    raise SignupFormError(detected_err)

        # Step 17: Two-Step Verification Page
        log("Step 17: Processing Two-Step Verification page...")
        find_element_robust(
            driver,
            selector="#fsa_Button_CopyBackupCode, #fsa_Checkbox_termsAndConditionsCheckbox",
            xpath="//*[contains(normalize-space(.), 'Backup Code') or contains(normalize-space(.), 'Your Verification Methods') or @id='fsa_Button_CopyBackupCode']",
            timeout=30
        )

        # Copy Backup Code and save it
        log("Extracting and copying Backup Code...")
        backup_code = extract_backup_code(driver, timeout=20)
        data["backup_code"] = backup_code
        ok(f"Backup Code copied and recorded: '{backup_code}'")
        time.sleep(1)

        # Click 'I agree to Federal Student Aid's' terms and conditions
        log("Accepting Terms and Conditions ('I agree to Federal Student Aid's')...")
        agree_ok = agree_terms_and_conditions(driver, timeout=15)
        if agree_ok:
            ok("Agreed to Federal Student Aid's terms and conditions.")
        else:
            warn("Could not confirm terms checkbox selection; proceeding to submit...")
        time.sleep(1)

        # Click Continue / Create Account button
        log("Clicking 'Continue' / 'Create Account' button...")
        btn_mfa_continue = find_element_robust(
            driver,
            selector="#fsa_Button_MfaStep_Continue",
            xpath="//button[@id='fsa_Button_MfaStep_Continue' or @id='fsa_Button_Continue' or contains(normalize-space(.), 'Create Account') or (contains(normalize-space(.), 'Continue') and not(contains(@id, 'Previous')))]",
            text="Create Account",
            timeout=20
        )
        if not btn_mfa_continue:
            raise RuntimeError("Could not find 'Create Account' / 'Continue' button on Two-Step Verification page.")
        smart_click(driver, btn_mfa_continue)
        ok("Clicked 'Create Account'. Waiting for confirmation page (account-created.html)...")
        time.sleep(2)

        detected_err = detect_page_error(driver)
        if detected_err:
            raise SignupFormError(detected_err)

        # Step 18: Verify Account Created & Final Save
        log("Step 18: Verifying Account Creation confirmation...")
        is_created = wait_for_account_created(driver, timeout=35)
        final_url = driver.current_url
        status_str = "account created" if is_created else "signed up"

        result_record = {
            "email": data["email"],
            "email_token": data.get("email_token"),
            "username": data.get("username"),
            "password": data.get("password"),
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "dob": f"{data.get('dob_month', 'XX')}/{data['dob_day']}/{data['dob_year']}",
            "ssn": ssn_masked,
            "address": data.get("address"),
            "address_line2": data.get("address_line2"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip": data.get("zip"),
            "backup_code": data.get("backup_code"),
            "status": status_str,
            "url": final_url,
            "time": datetime.now().isoformat(timespec="seconds"),
        }

        save_signup_result(result_record, output_file=CONFIG["output_file"])
        if is_created:
            ok(f"Signup process successfully completed! Account created for '{data['email']}'. Username: '{data.get('username')}', Password: '{data.get('password')}', Backup code: '{data.get('backup_code')}'")
        else:
            warn(f"Completed signup workflow; final URL: '{final_url}'. Username: '{data.get('username')}', Password: '{data.get('password')}', Backup code: '{data.get('backup_code')}'. Result saved.")
        return result_record

    except SignupFormError as fe:
        print_form_error_banner(fe.error_info)
        err_title = fe.error_info.get("title", "Form Error")
        err_msg = fe.error_info.get("message", "")
        err_url = fe.error_info.get("url") or (driver.current_url if driver else "")

        # Format status slug (e.g. 'failed - account already exists', 'failed - can't create your account')
        clean_title = err_title.replace("’", "'")
        status_slug = re.sub(r"[^\w\s\'-]", "", clean_title).strip().lower()
        status_slug = re.sub(r"[\s_]+", " ", status_slug)
        status_str = f"failed - {status_slug}" if status_slug else "failed - form error"

        result_record = {
            "email": data.get("email"),
            "email_token": data.get("email_token"),
            "username": data.get("username"),
            "password": data.get("password"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "dob": f"{data.get('dob_month', 'XX')}/{data.get('dob_day', 'XX')}/{data.get('dob_year', 'XXXX')}",
            "ssn": ssn_masked,
            "address": data.get("address"),
            "address_line2": data.get("address_line2"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip": data.get("zip"),
            "backup_code": data.get("backup_code"),
            "status": status_str,
            "error_title": err_title,
            "error_message": err_msg,
            "url": err_url,
            "time": datetime.now().isoformat(timespec="seconds"),
        }
        save_signup_result(result_record, output_file=CONFIG["output_file"])
        warn(f"Recorded failure with status '{status_str}' for '{data.get('email')}'.")
        return result_record

    except Exception as e:
        detected_err = detect_page_error(driver)
        if detected_err:
            print_form_error_banner(detected_err)
            err_title = detected_err.get("title", "Form Error")
            err_msg = detected_err.get("message", "")
            err_url = detected_err.get("url") or (driver.current_url if driver else "")
            clean_title = err_title.replace("’", "'")
            status_slug = re.sub(r"[^\w\s\'-]", "", clean_title).strip().lower()
            status_slug = re.sub(r"[\s_]+", " ", status_slug)
            status_str = f"failed - {status_slug}" if status_slug else "failed - form error"

            result_record = {
                "email": data.get("email"),
                "email_token": data.get("email_token"),
                "username": data.get("username"),
                "password": data.get("password"),
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "dob": f"{data.get('dob_month', 'XX')}/{data.get('dob_day', 'XX')}/{data.get('dob_year', 'XXXX')}",
                "ssn": ssn_masked,
                "address": data.get("address"),
                "address_line2": data.get("address_line2"),
                "city": data.get("city"),
                "state": data.get("state"),
                "zip": data.get("zip"),
                "backup_code": data.get("backup_code"),
                "status": status_str,
                "error_title": err_title,
                "error_message": err_msg,
                "url": err_url,
                "time": datetime.now().isoformat(timespec="seconds"),
            }
            save_signup_result(result_record, output_file=CONFIG["output_file"])
            warn(f"Recorded failure with status '{status_str}' for '{data.get('email')}'.")
            return result_record
        raise


def find_flzb_log(file_path=None, state=None, year=None):
    """
    Locates the appropriate results JSON log file produced by flzb-me.py.
    Supports:
      - Direct file path (e.g. logs/flzb-me/results_AZ_1985_20261012_071953.json or relative name)
      - 'latest' or None: automatically finds the most recent file in logs/flzb-me/ (or logs/)
      - state & year filters (e.g. state='AZ', year='1985')
    """
    if file_path and file_path.lower() != "latest":
        if os.path.exists(file_path):
            return file_path
        in_flzb = os.path.join("logs", "flzb-me", file_path)
        if os.path.exists(in_flzb):
            return in_flzb
        in_logs = os.path.join("logs", file_path)
        if os.path.exists(in_logs):
            return in_logs
        warn(f"Specified log file does not exist: {file_path}")
        return None

    # Search in logs/flzb-me/ first, then logs/
    search_dirs = [os.path.join("logs", "flzb-me"), "logs"]
    candidates = []

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".json") and f.startswith("results_"):
                if state and not f.startswith(f"results_{state.upper()}_"):
                    continue
                if year and f"_{year}_" not in f:
                    continue
                full_p = os.path.join(d, f)
                try:
                    # Ignore empty files (< 200 bytes with 0 records)
                    if os.path.getsize(full_p) > 200:
                        candidates.append((os.path.getmtime(full_p), full_p))
                except OSError:
                    pass

    if not candidates:
        warn("No matching flzb-me log files found in logs/flzb-me/.")
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def load_records_from_log(file_path):
    """
    Reads a results JSON file produced by flzb-me.py.
    Returns:
        tuple: (list_of_records, metadata_dict)
    """
    if not file_path or not os.path.exists(file_path):
        return [], {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            try:
                decoder = json.JSONDecoder(strict=False)
                data, _ = decoder.raw_decode(content)
            except Exception:
                data = json.loads(content, strict=False)
    except Exception as e:
        warn(f"Failed to read {file_path}: {e}")
        return [], {}

    import re
    # 1. Use pre-structured "records" list if present
    records = data.get("records")
    if isinstance(records, list) and records:
        for r in records:
            # Ensure DOB month, day, year are available as distinct keys
            if not r.get("dob_month") or not r.get("dob_day") or not r.get("dob_year"):
                dob_str = r.get("dob", "")
                m = re.search(r"\b(?:(\d{2})|XX)/(?:(\d{2})|XX)/(\d{4})\b", dob_str)
                if m:
                    if m.group(1) and not r.get("dob_month"):
                        r["dob_month"] = m.group(1)
                    if m.group(2) and not r.get("dob_day"):
                        r["dob_day"] = m.group(2)
                    if m.group(3) and not r.get("dob_year"):
                        r["dob_year"] = m.group(3)

            # Ensure address and city are populated from address_and_city if present
            if r.get("address_and_city") and (not r.get("address") or not r.get("city")):
                p_addr, p_city = split_address_city(r["address_and_city"])
                if p_addr and not r.get("address"):
                    r["address"] = p_addr
                if p_city and not r.get("city"):
                    r["city"] = p_city

        return records, data

    # 2. Fallback: Parse result_table text for legacy logs
    table_text = data.get("result_table", "")
    lines = [line.strip() for line in table_text.splitlines() if line.strip()]
    data_lines = [l for l in lines if not l.startswith("Name Address") and "0 results found" not in l]
    parsed_records = []

    for idx, row in enumerate(data_lines):
        rec = {"id": idx + 1, "raw": row}
        parts = row.split()
        if len(parts) >= 2:
            rec["first_name"] = parts[0]
            rec["last_name"] = parts[1]

        ssn_match = re.search(r"\b\d{3}-\d{2}-\d{4}\b", row)
        if ssn_match:
            rec["ssn"] = ssn_match.group(0)

        dob_match = re.search(r"\b(?:(\d{2})|XX)/(?:(\d{2})|XX)/(\d{4})\b", row)
        if dob_match:
            if dob_match.group(1):
                rec["dob_month"] = dob_match.group(1)
            if dob_match.group(2):
                rec["dob_day"] = dob_match.group(2)
            if dob_match.group(3):
                rec["dob_year"] = dob_match.group(3)
            rec["dob"] = dob_match.group(0)

        zip_match = re.search(r"\b([A-Z]{2})\s+(\d{5})\b", row)
        if zip_match:
            rec["state"] = zip_match.group(1)
            rec["zip"] = zip_match.group(2)

        parsed_records.append(rec)

    return parsed_records, data


def display_log_records(records, file_path, limit=50):
    """
    Displays a formatted summary table of records for selection.
    """
    print(f"\n{'='*95}")
    print(f" RECORDS IN: {file_path}")
    print(f" Total records found: {len(records)}")
    print(f"{'='*95}")
    print(f"{'Index':<6} | {'Full Name':<22} | {'DOB':<12} | {'SSN':<13} | {'Address / Location':<32}")
    print(f"{'-'*6}-+-{'-'*22}-+-{'-'*12}-+-{'-'*13}-+-{'-'*32}")

    for i, r in enumerate(records[:limit]):
        name = r.get("full_name") or f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
        dob = r.get("dob") or f"{r.get('dob_month','XX')}/{r.get('dob_day','XX')}/{r.get('dob_year','XXXX')}"
        ssn = r.get("ssn", "N/A")
        addr = r.get("address", "")
        city = r.get("city", "")
        state = r.get("state", "")
        zip_code = r.get("zip", "")
        loc_parts = [p for p in [addr, city, f"{state} {zip_code}".strip()] if p]
        loc = ", ".join(loc_parts)
        if not loc:
            loc = r.get("address_and_city", "")
        print(f"[{i:<4}] | {name:<22.22} | {dob:<12} | {ssn:<13} | {loc:<32.32}")

    if len(records) > limit:
        print(f"... and {len(records) - limit} more records (showing first {limit}).")
    print(f"{'='*95}\n")
    print("To run signup-bot with any record above:")
    print(f"    python signup-bot.py --from-log \"{file_path}\" --record-index <INDEX>\n")


def parse_record_from_log(file_path=None, index=0, state=None, year=None):
    """
    Extracts person info from a results log file produced by flzb-me.py.
    """
    target_file = find_flzb_log(file_path, state=state, year=year)
    if not target_file:
        return {}

    records, _ = load_records_from_log(target_file)
    if not records:
        warn(f"No records could be parsed from {target_file}")
        return {}

    if index < 0 or index >= len(records):
        warn(f"Record index {index} out of range (0..{len(records)-1}) in {target_file}")
        return {}

    rec = records[index]
    display_name = rec.get("full_name") or f"{rec.get('first_name')} {rec.get('last_name')}"
    ok(f"Loaded record #{index} ({display_name}) from {target_file}")
    return rec


def load_completed_record_keys(output_file="AutoSignup/results.json", retry_failed=False):
    """
    Returns a set of normalized keys (e.g. 'last_name:ssn_last4')
    for all records already recorded in results.json.
    If retry_failed is True, temporary failures ('failed - account creation error')
    are NOT skipped, allowing them to be retried.
    """
    completed = set()
    if not os.path.exists(output_file):
        return completed
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for it in items:
                status = str(it.get("status", "")).lower()
                # If retry_failed is active and this record only had a temporary glitch, do not skip
                if retry_failed and "account creation error" in status:
                    continue
                ssn = str(it.get("ssn", "")).strip()
                last = str(it.get("last_name", "")).strip().lower()
                ssn_last4 = ssn[-4:] if len(ssn) >= 4 else ssn
                if last and ssn_last4:
                    completed.add(f"{last}:{ssn_last4}")
    except Exception:
        pass
    return completed


def parse_range_spec(range_str, total_count):
    """
    Parses '0..10', '5-15', '0,1,2', or '3' into a list of valid integer indices.
    """
    if not range_str:
        return []
    cleaned = range_str.strip()
    if ".." in cleaned:
        parts = cleaned.split("..")
        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            start = max(0, start)
            end = min(total_count - 1, end)
            if start <= end:
                return list(range(start, end + 1))
        except Exception:
            pass
    elif "-" in cleaned:
        parts = cleaned.split("-")
        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            start = max(0, start)
            end = min(total_count - 1, end)
            if start <= end:
                return list(range(start, end + 1))
        except Exception:
            pass
    elif "," in cleaned:
        try:
            return [int(x.strip()) for x in cleaned.split(",") if 0 <= int(x.strip()) < total_count]
        except Exception:
            pass
    else:
        try:
            idx = int(cleaned)
            if 0 <= idx < total_count:
                return [idx]
        except Exception:
            pass
    return []


def resolve_signup_user_data(log_record, args, defaults):
    """
    Builds the dictionary of signup inputs for a given log record
    or fallback defaults, including per-record unique tempmail creation.
    """
    first_name = args.first_name or log_record.get("first_name") or defaults.get("first_name")
    last_name = args.last_name or log_record.get("last_name") or defaults.get("last_name")

    resolved_email = args.email or log_record.get("email")
    email_token = log_record.get("email_token")

    # Generate fresh email via tempmail.lol for each record if requested or not supplied
    if (not resolved_email or args.use_tempmail) and not args.no_tempmail and tempmail_client1 is not None:
        try:
            gen_email, gen_token = tempmail_client1.create_email_for_name(first_name, last_name)
            resolved_email = gen_email
            email_token = gen_token
        except Exception as e:
            warn(f"Failed to generate tempmail for {first_name} {last_name}: {e}. Falling back to default.")
            resolved_email = defaults.get("email")
    elif not resolved_email:
        resolved_email = defaults.get("email")

    if not email_token and resolved_email and tempmail_client1 is not None:
        email_token = tempmail_client1.get_token_for_address(resolved_email)

    address = args.address or log_record.get("address") or defaults.get("address")
    address_line2 = args.address2 or log_record.get("address_line2") or defaults.get("address_line2", "")
    city = args.city or log_record.get("city") or defaults.get("city")
    state = args.state or log_record.get("state") or defaults.get("state")
    zip_code = args.zip or log_record.get("zip") or defaults.get("zip")
    password = args.password or log_record.get("password") or defaults.get("password")

    dob_month = args.dob_month or (log_record.get("dob_month") if log_record.get("dob_month") not in (None, "XX", "") else None) or defaults.get("dob_month", "01")
    dob_day = args.dob_day or (log_record.get("dob_day") if log_record.get("dob_day") not in (None, "XX", "") else None) or defaults.get("dob_day", "15")
    dob_year = args.dob_year or (log_record.get("dob_year") if log_record.get("dob_year") not in (None, "XX", "") else None) or defaults.get("dob_year", "1988")
    ssn = args.ssn or log_record.get("ssn") or defaults.get("ssn")

    username = getattr(args, "username", None) or log_record.get("username") or defaults.get("username")
    if not username:
        if resolved_email and "@" in resolved_email:
            username = resolved_email.split("@")[0] + str(dob_year or "1988")
        else:
            username = f"{first_name}{last_name}{dob_year}".lower()

    return {
        "email": resolved_email,
        "email_token": email_token,
        "email_timeout": args.email_timeout,
        "first_name": first_name,
        "last_name": last_name,
        "dob_month": str(dob_month).zfill(2) if dob_month else "01",
        "dob_day": str(dob_day).zfill(2) if dob_day else "15",
        "dob_year": str(dob_year) if dob_year else "1988",
        "ssn": ssn,
        "address": address,
        "address_line2": address_line2,
        "city": city,
        "state": state,
        "zip": str(zip_code) if zip_code is not None else "",
        "username": username,
        "password": password,
        "code": args.code or os.getenv("VERIFICATION_CODE"),
    }


def main():
    global PROFILE_ID

    parser = argparse.ArgumentParser(description="Run the 'signup-bot' bot (StudentAid Account Creation).")
    parser.add_argument("--headless", action="store_true", default=None,
                        help="Override the browser headless setting")
    parser.add_argument("--local", action="store_true", default=False,
                        help="Use standard local Selenium Chrome instead of MoreLogin API")
    parser.add_argument("--profile-id", default=PROFILE_ID,
                        help="MoreLogin environment ID")
    parser.add_argument("--from-log", default=None,
                        help="Path to a flzb-me results JSON file or 'latest' to auto-populate record info")
    parser.add_argument("--record-index", type=int, default=0,
                        help="Index of single record to pick from the log file (default: 0)")
    parser.add_argument("--all", action="store_true", default=False,
                        help="Batch mode: process all records from the selected flzb-me log file")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Batch mode: maximum number of records to process in this run (e.g. 5)")
    parser.add_argument("--start-index", type=int, default=0,
                        help="Batch mode: index of first record to process (default: 0)")
    parser.add_argument("--range", default=None,
                        help="Batch mode: range of record indices to process (e.g. '0..10' or '5-15')")
    parser.add_argument("--skip-completed", action="store_true", default=False,
                        help="Batch mode: automatically skip records already recorded in AutoSignup/results.json")
    parser.add_argument("--delay-between", type=int, default=5,
                        help="Batch mode: seconds to wait between successive signups (default: 5)")
    parser.add_argument("--max-consecutive-errors", type=int, default=2,
                        help="Circuit breaker: maximum consecutive 'Account Creation Error' responses before halting batch (default: 2)")
    parser.add_argument("--stop-on-error", action="store_true", default=False,
                        help="Immediately stop batch execution on any form error")
    parser.add_argument("--restart-on-error", action="store_true", default=True,
                        help="Restart browser profile after an Account Creation Error to satisfy 'close all windows' requirement (default: True)")
    parser.add_argument("--retry-failed", action="store_true", default=False,
                        help="Allow --skip-completed to re-attempt records that previously failed with temporary 'account creation error'")
    parser.add_argument("--list-records", "-l", action="store_true", default=False,
                        help="Display parsed records from the selected flzb-me log file and exit")
    parser.add_argument("--state", default=None,
                        help="Filter log file by state (e.g. AZ, AL)")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Display resolved signup data and exit without opening the browser")
    parser.add_argument("--email", default=None,
                        help="User email address")
    parser.add_argument("--first-name", "--first", default=None,
                        help="User first name")
    parser.add_argument("--last-name", "--last", default=None,
                        help="User last name")
    parser.add_argument("--dob-month", "--month", default=None,
                        help="Date of birth month (e.g. 01)")
    parser.add_argument("--dob-day", "--day", default=None,
                        help="Date of birth day (e.g. 24)")
    parser.add_argument("--dob-year", "--year", default=None,
                        help="Date of birth year or log filter year (e.g. 1988)")
    parser.add_argument("--ssn", default=None,
                        help="Social Security Number (e.g. 440-72-8438)")
    parser.add_argument("--address", default=None,
                        help="User street address line 1 (e.g. 16103 W Williams St)")
    parser.add_argument("--address2", default=None,
                        help="User street address line 2 (e.g. Apt 4B)")
    parser.add_argument("--city", default=None,
                        help="User city (e.g. Goodyear)")
    parser.add_argument("--zip", default=None,
                        help="User 5-digit postal code (e.g. 85338)")
    parser.add_argument("--username", default=None,
                        help="Username for account creation")
    parser.add_argument("--password", default=None,
                        help="Password for account creation")
    parser.add_argument("--code", default=None,
                        help="Pre-supplied verification code (optional)")
    parser.add_argument("--tempmail", "--use-tempmail", dest="use_tempmail", action="store_true", default=False,
                        help="Force creating a fresh temporary email via tempmail.lol using first & last name")
    parser.add_argument("--no-tempmail", action="store_true", default=False,
                        help="Disable automatic tempmail generation")
    parser.add_argument("--email-timeout", type=int, default=120,
                        help="Maximum seconds to wait for verification email code (default: 120)")
    args = parser.parse_args()

    if args.profile_id:
        PROFILE_ID = str(args.profile_id).strip()

    is_batch = args.all or (args.limit is not None) or bool(args.range)

    # 1. Resolve log file if requested or running in batch mode
    target_log_file = None
    all_log_records = []
    if is_batch or args.from_log or args.state or (not args.first_name and not args.ssn):
        target_log_file = find_flzb_log(args.from_log or "latest", state=args.state, year=args.dob_year)
        if target_log_file:
            all_log_records, _ = load_records_from_log(target_log_file)

    # Handle --list-records preview mode
    if args.list_records:
        if target_log_file and all_log_records:
            display_log_records(all_log_records, target_log_file)
        else:
            err("No log files found in logs/flzb-me/ to list records from.")
        sys.exit(0)

    # 2. Build the Batch Queue of records to process
    batch_queue = []

    if all_log_records:
        # Determine target indices from range, all, limit, or single record-index
        if args.range:
            target_indices = parse_range_spec(args.range, len(all_log_records))
        elif args.all:
            start_i = max(0, args.start_index)
            target_indices = list(range(start_i, len(all_log_records)))
        elif args.limit is not None:
            start_i = max(0, args.start_index or args.record_index)
            end_i = min(len(all_log_records), start_i + args.limit)
            target_indices = list(range(start_i, end_i))
        elif is_batch:
            target_indices = list(range(0, len(all_log_records)))
        else:
            # Single record mode with specific record-index
            target_indices = [args.record_index]

        # Filter out invalid indices
        target_indices = [i for i in target_indices if 0 <= i < len(all_log_records)]

        # Apply --skip-completed filter if requested
        if args.skip_completed:
            completed_keys = load_completed_record_keys(CONFIG["output_file"], retry_failed=args.retry_failed)
            filtered = []
            for i in target_indices:
                r = all_log_records[i]
                c_last = str(r.get("last_name", "")).strip().lower()
                c_ssn = str(r.get("ssn", "")).strip()
                c_key = f"{c_last}:{c_ssn[-4:] if len(c_ssn) >= 4 else c_ssn}"
                if c_key in completed_keys:
                    log(f"[SKIP] #{i:<3} {r.get('first_name')} {r.get('last_name')} (SSN ***-**-{c_ssn[-4:]}) already recorded in results.json.")
                else:
                    filtered.append(i)
            target_indices = filtered

        if not target_indices:
            warn("No records to process (all selected records may have been completed or filtered).")
            sys.exit(0)

        for i in target_indices:
            u_data = resolve_signup_user_data(all_log_records[i], args, CONFIG["defaults"])
            batch_queue.append((i, u_data))

    else:
        # Standalone manual record (from CLI flags or env)
        u_data = resolve_signup_user_data({}, args, CONFIG["defaults"])
        batch_queue.append((None, u_data))

    # 3. Dry Run Handling
    if args.dry_run:
        print("\n" + "=" * 98)
        if len(batch_queue) > 1:
            print(f" [DRY RUN] BATCH QUEUE ({len(batch_queue)} records selected from {target_log_file or 'inputs'})")
            print("=" * 98)
            print(f"{'#':<4} | {'Idx':<5} | {'Full Name':<22} | {'DOB':<10} | {'SSN':<13} | {'Location':<25}")
            print(f"{'-'*4}-+-{'-'*5}-+-{'-'*22}-+-{'-'*10}-+-{'-'*13}-+-{'-'*25}")
            for item_num, (rec_i, ud) in enumerate(batch_queue, 1):
                idx_str = f"[{rec_i}]" if rec_i is not None else "[N/A]"
                name = f"{ud['first_name']} {ud['last_name']}"
                dob = f"{ud['dob_month']}/{ud['dob_day']}/{ud['dob_year']}"
                ssn = f"***-**-{ud['ssn'][-4:]}" if (ud.get('ssn') and len(ud['ssn']) >= 4) else "***"
                loc = f"{ud.get('city')}, {ud.get('state')} {ud.get('zip')}".strip()
                print(f"{item_num:<4} | {idx_str:<5} | {name:<22.22} | {dob:<10} | {ssn:<13} | {loc:<25.25}")
            print("=" * 98 + "\n")
        else:
            print(" [DRY RUN] Resolved Signup Data (1 record):")
            print("=" * 98)
            _, ud = batch_queue[0]
            for k, v in ud.items():
                if k == "ssn" and v:
                    v_disp = f"***-**-{v[-4:]}" if len(str(v)) >= 4 else "***"
                elif k == "password" and v:
                    v_disp = "********"
                else:
                    v_disp = v
                print(f"  {k:<15}: {v_disp}")
            print("=" * 98 + "\n")
        sys.exit(0)

    # 4. Validate essential fields for single manual record if missing
    if len(batch_queue) == 1 and batch_queue[0][0] is None:
        _, single_data = batch_queue[0]
        for k in ["email", "first_name", "last_name", "dob_day", "dob_year", "ssn", "address", "city", "state", "zip"]:
            if not single_data.get(k):
                val = input(f"Enter {k.replace('_', ' ').title()}: ").strip()
                single_data[k] = val

    driver = None
    used_morelogin = False
    batch_stats = {
        "total": len(batch_queue),
        "success": 0,
        "failed_error": 0,
        "mobile_required": 0,
        "other": 0,
        "results": []
    }

    try:
        # Start browser session once for the batch run
        if not args.local and PROFILE_ID:
            port, driver_path = start_morelogin_profile()
            if port:
                driver = attach_driver(port, driver_path)
                if driver:
                    used_morelogin = True

        if driver is None:
            log("Starting standard Chrome session via DriverManager...")
            if DriverManager is not None:
                dm = DriverManager(profile_name=CONFIG["profile"], headless=args.headless)
                driver = dm.start()
            else:
                options = webdriver.ChromeOptions()
                if args.headless:
                    options.add_argument("--headless=new")
                driver = webdriver.Chrome(service=Service(), options=options)
            ok("Local Chrome session started.")

        consecutive_account_creation_errors = 0

        # Process each record in the queue
        for item_num, (rec_idx, u_data) in enumerate(batch_queue, 1):
            idx_label = f"#{rec_idx}" if rec_idx is not None else "#1"
            display_name = f"{u_data.get('first_name')} {u_data.get('last_name')}"
            ssn_display = f"***-**-{str(u_data.get('ssn', ''))[-4:]}"

            if len(batch_queue) > 1:
                print("\n" + "=" * 78)
                log(f"[BATCH] Processing Record {item_num}/{len(batch_queue)} ({idx_label}): {display_name} | SSN: {ssn_display}")
                print("=" * 78 + "\n")

            try:
                res = run_signup_bot(driver, u_data)
                status = res.get("status", "") if res else "completed"
                batch_stats["results"].append({
                    "index": idx_label,
                    "name": display_name,
                    "ssn": ssn_display,
                    "username": res.get("username") if res else u_data.get("username"),
                    "password": res.get("password") if res else u_data.get("password"),
                    "status": status,
                    "backup_code": res.get("backup_code") if res else None
                })
                if status in ("account created", "signed up"):
                    batch_stats["success"] += 1
                    consecutive_account_creation_errors = 0
                elif "unable to create" in status or "mobile" in status:
                    batch_stats["mobile_required"] += 1
                    consecutive_account_creation_errors = 0
                elif "failed" in status:
                    batch_stats["failed_error"] += 1
                    if "account creation error" in status.lower():
                        consecutive_account_creation_errors += 1
                    else:
                        consecutive_account_creation_errors = 0
                else:
                    batch_stats["other"] += 1

            except SignupFormError as sfe:
                err_title = sfe.error_info.get("title", "Form Error")
                batch_stats["failed_error"] += 1
                status = f"failed - {err_title.lower()}"
                if "account creation error" in status:
                    consecutive_account_creation_errors += 1
                else:
                    consecutive_account_creation_errors = 0
                batch_stats["results"].append({
                    "index": idx_label,
                    "name": display_name,
                    "ssn": ssn_display,
                    "username": u_data.get("username"),
                    "password": u_data.get("password"),
                    "status": status,
                    "backup_code": None
                })

            except Exception as e:
                err(f"Error on record {idx_label} ({display_name}): {e}")
                batch_stats["other"] += 1
                status = f"error: {type(e).__name__}"
                consecutive_account_creation_errors = 0
                batch_stats["results"].append({
                    "index": idx_label,
                    "name": display_name,
                    "ssn": ssn_display,
                    "username": u_data.get("username"),
                    "password": u_data.get("password"),
                    "status": status,
                    "backup_code": None
                })

            # Always clean the signup tab after each record
            try:
                signup_handle = getattr(driver, "signup_tab_handle", None)
                close_signup_tab(driver, signup_handle)
            except Exception:
                pass

            # Circuit Breaker Check: halt immediately if consecutive Account Creation Errors hit threshold
            if consecutive_account_creation_errors >= args.max_consecutive_errors:
                print("\n" + "=" * 80)
                err(f"[CIRCUIT BREAKER] Reached {consecutive_account_creation_errors} consecutive 'Account Creation Error' responses.")
                warn("StudentAid has temporarily throttled this IP / session on the personal-info (SSA) endpoint.")
                warn("Halting batch execution now to prevent burning remaining records!")
                warn("Recommended next steps:")
                warn("  1. Rotate or change the Proxy / IP in your MoreLogin profile.")
                warn("  2. Wait 10-15 minutes for the rate limit to cool down before resuming.")
                warn("  3. Run with --retry-failed when ready to re-process these records.")
                print("=" * 80 + "\n")
                break

            if args.stop_on_error and "failed" in status:
                warn(f"[STOP ON ERROR] Stopping batch because --stop-on-error was requested.")
                break

            # If an Account Creation Error occurred and we still have records,
            # restart the browser profile to fulfill StudentAid's requirement:
            # "close all browser windows and start over"
            if "account creation error" in status.lower() and item_num < len(batch_queue) and args.restart_on_error:
                log("StudentAid requires closing all browser windows after 'Account Creation Error'. Restarting session...")
                driver, used_morelogin = restart_browser_session(driver, used_morelogin, args)

            # If there are more records in the batch, apply cooldown pause
            if item_num < len(batch_queue):
                log(f"Pausing {args.delay_between}s before next record in batch...")
                time.sleep(args.delay_between)

    except Exception as e:
        err(f"Fatal error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        log("Cleaning up browser session...")
        if driver is not None:
            try:
                signup_handle = getattr(driver, "signup_tab_handle", None)
                close_signup_tab(driver, signup_handle)
            except Exception as e:
                debug(f"Tab cleanup error: {e}")
            try:
                driver.quit()
            except Exception:
                pass
        if used_morelogin and PROFILE_ID:
            close_morelogin_profile(PROFILE_ID)

        # Print Batch Summary if multiple records were processed
        if len(batch_queue) > 1:
            print("\n" + "=" * 80)
            print("                         BATCH EXECUTION SUMMARY")
            print("=" * 80)
            print(f" Total Processed  : {len(batch_queue)}")
            print(f" Accounts Created : {batch_stats['success']}")
            print(f" Mobile Required  : {batch_stats['mobile_required']}")
            print(f" Form Errors      : {batch_stats['failed_error']}")
            print(f" Other / Errors   : {batch_stats['other']}")
            print("-" * 80)
            for r in batch_stats["results"]:
                u_info = f" | User: {r.get('username')}" if r.get('username') else ""
                p_info = f" | Pass: {r.get('password')}" if r.get('password') else ""
                b_code = f" | Backup: {r['backup_code']}" if r.get('backup_code') and r['backup_code'] != 'NOT_EXTRACTED' else ""
                print(f"  [{r['index']:<4}] {r['name']:<22.22} | {r['ssn']:<13} | {r['status']}{u_info}{p_info}{b_code}")
            print("=" * 80)
            print(f"Results recorded in {CONFIG['output_file']} and logs/signup-bot/\n")


if __name__ == "__main__":
    main()

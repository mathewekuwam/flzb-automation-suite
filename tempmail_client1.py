"""
tempmail_client1.py
-------------------
TempMail.lol API client for creating disposable inboxes and automatically
retrieving verification codes.

Features:
- Create emails using user first and last name as a prefix.
- Automatically poll and parse 6-digit verification codes from incoming emails.
- Store address-to-token mappings in inboxes.json.
- Easily imported by signup-bot.py, flzb-me.py, and other automation scripts.
- Standalone CLI for testing inbox creation, code extraction, and monitoring.
"""

import argparse
import json
import os
import re
import sys
import time
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = "https://api.tempmail.lol/v2"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE_DIR, "inboxes.json")

# Read the key from the environment or .env file:
#   export TEMPMAIL_API_KEY="tm.xxxxxxxxxx.xxxxxxxx"      (Linux/macOS)
#   setx TEMPMAIL_API_KEY "tm.xxxxxxxxxx.xxxxxxxx"        (Windows)
API_KEY = os.environ.get("TEMPMAIL_API_KEY", "").strip()

session = requests.Session()
if API_KEY:
    session.headers["Authorization"] = f"Bearer {API_KEY}"


def check(r):
    """Raise a clearer error for key/scope problems."""
    if r.status_code in (401, 403):
        raise SystemExit(
            f"API key rejected ({r.status_code}). Check that the key is valid "
            f"and its scope allows this action.\nServer said: {r.text[:200]}"
        )
    r.raise_for_status()
    return r


def clean_prefix_from_name(first_name=None, last_name=None, max_length=20):
    """
    Cleans and combines first and last name into a valid alphanumeric prefix for tempmail.lol.
    Example: ('William', 'Shunk') -> 'williamshunk'
    """
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    raw = f"{fn}{ln}" if (fn or ln) else ""
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw).lower()
    if not cleaned:
        return None
    return cleaned[:max_length]


def new_email(prefix=None, domain=None):
    """
    Creates a new temporary email address.
    If prefix is provided, tempmail.lol will prefix the address with that value.
    Saves address and token to inboxes.json.
    Returns: (address, token)
    """
    body = {}
    if prefix:
        body["prefix"] = prefix
    if domain:
        body["domain"] = domain  # custom domains need Plus/Ultra
    r = check(session.post(f"{BASE}/inbox/create", json=body, timeout=15))
    d = r.json()
    address = d["address"]
    token = d["token"]
    save(address, token)
    return address, token


def create_email_for_name(first_name=None, last_name=None, domain=None):
    """
    Generates a new temporary email address derived from first and last name.
    Falls back to a random email if names are not provided.
    Returns: (address, token)
    """
    prefix = clean_prefix_from_name(first_name, last_name)
    return new_email(prefix=prefix, domain=domain)


def save(address, token):
    """Saves the address and token mapping in inboxes.json."""
    try:
        if os.path.exists(STORE):
            with open(STORE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data[address] = token
    try:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save inbox token to {STORE}: {e}")


def load_inboxes():
    """Loads all address -> token mappings from inboxes.json."""
    if not os.path.exists(STORE):
        return {}
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_token_for_address(address):
    """Retrieves the token for an address from inboxes.json."""
    if not address:
        return None
    inboxes = load_inboxes()
    return inboxes.get(address.strip())


def get_inbox(token):
    """
    Fetches the inbox messages for a given token.
    Returns: {'emails': [...], 'expired': bool}
    """
    r = session.get(f"{BASE}/inbox", params={"token": token}, timeout=15)
    if r.status_code == 404:
        try:
            return r.json()
        except Exception:
            return {"emails": [], "expired": True}
    check(r)
    return r.json()


def extract_verification_code(email_obj):
    """
    Extracts a 6-digit verification code from an email object (subject, text body, html).
    Uses prioritized regex to accurately extract the verification code even when other
    numbers are present.
    """
    if not isinstance(email_obj, dict):
        return None

    subject = str(email_obj.get("subject") or "")
    body = str(email_obj.get("body") or "")
    html = str(email_obj.get("html") or "")
    clean_html = re.sub(r"<[^>]+>", " ", html)

    # 1. Look for explicit keyword patterns (e.g. "secure code is: 123456", "verification code: 123456")
    keyword_patterns = [
        r"(?:secure|verification|confirmation|security|one-time|login|auth)?\s*code\s*(?:is|:|\bis\b)?\s*[:#\-]?\s*([0-9]{6})\b",
        r"(?:enter|use)\s+(?:the\s+)?(?:code\s+)?([0-9]{6})\b",
        r"\b([0-9]{6})\s+is\s+your\s+(?:secure\s*code|verification\s*code|code)",
        r"(?:code|pin)\s*[:#\-]?\s*([0-9]{6})\b",
    ]

    all_texts = [body, clean_html, subject]
    for text in all_texts:
        if not text:
            continue
        for pat in keyword_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)

    # 2. Look in HTML tags (e.g. <strong>123456</strong>, <h1>123456</h1>)
    if html:
        html_tag_patterns = [
            r"<(?:strong|b|h1|h2|h3|span|td|div)[^>]*>\s*([0-9]{6})\s*</(?:strong|b|h1|h2|h3|span|td|div)>",
        ]
        for pat in html_tag_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1)

    # 3. Fallback: Any standalone 6-digit number in subject, body, or clean html
    for text in [subject, body, clean_html]:
        if not text:
            continue
        m = re.search(r"\b([0-9]{6})\b", text)
        if m:
            return m.group(1)

    return None


def wait_for_verification_code(token=None, address=None, timeout=120, poll_interval=3, log_fn=None):
    """
    Polls the inbox for the given token (or address) until an email arrives,
    then parses and extracts the verification code.

    Args:
        token: Inbox token string.
        address: Email address string (used to look up token if token is None).
        timeout: Maximum seconds to wait (default: 120).
        poll_interval: Seconds between inbox checks (default: 3).
        log_fn: Optional callable for logging messages (defaults to print).

    Returns:
        The extracted 6-digit code string, or None if timed out / expired.
    """
    if log_fn is None:
        log_fn = print

    if not token and address:
        token = get_token_for_address(address)

    if not token:
        log_fn(f"[ERROR] No token available to check inbox (address: {address}).")
        return None

    target_label = address if address else f"token {token[:8]}..."
    log_fn(f"[tempmail] Waiting for verification code sent to {target_label} (timeout: {timeout}s)...")

    start_time = time.time()
    last_count = 0

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        try:
            data = get_inbox(token)
            if data.get("expired"):
                log_fn("[tempmail] Inbox has expired.")
                return None

            emails = data.get("emails", [])
            if len(emails) > last_count:
                last_count = len(emails)
                log_fn(f"[tempmail] Received new email ({last_count} total). Parsing for verification code...")
                # Inspect emails from newest to oldest
                for m in reversed(emails):
                    code = extract_verification_code(m)
                    if code:
                        subject = m.get("subject", "<No Subject>")
                        sender = m.get("from", "<Unknown>")
                        log_fn(f"[tempmail] Found verification code: {code} (From: {sender}, Subject: '{subject}')")
                        return code

        except Exception as e:
            log_fn(f"[tempmail] Check error: {e}")

        remaining = int(timeout - (time.time() - start_time))
        if remaining > 0 and elapsed % 15 == 0 and elapsed > 0:
            log_fn(f"[tempmail] Still waiting for code... ({remaining}s remaining)")

        time.sleep(poll_interval)

    log_fn(f"[tempmail] Timed out after {timeout}s waiting for verification code.")
    return None


def wait_for_email(token=None, address=None, timeout=120, poll_interval=3, log_fn=None):
    """
    Waits for any email to arrive in the inbox.
    Returns the newest email dict, or None if timed out.
    """
    if log_fn is None:
        log_fn = print

    if not token and address:
        token = get_token_for_address(address)

    if not token:
        log_fn(f"[ERROR] No token available for address: {address}")
        return None

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data = get_inbox(token)
            if data.get("expired"):
                log_fn("[tempmail] Inbox expired.")
                return None
            emails = data.get("emails", [])
            if emails:
                return emails[-1]
        except Exception as e:
            log_fn(f"[tempmail] Poll error: {e}")
        time.sleep(poll_interval)

    log_fn(f"[tempmail] Timed out waiting for email.")
    return None


def show(token):
    """Prints all emails in an inbox in a human-readable format."""
    data = get_inbox(token)
    if data.get("expired"):
        print("Inbox expired.")
        return
    emails = data.get("emails", [])
    print(f"{len(emails)} email(s)")
    for m in emails:
        print("-" * 40)
        print("From:   ", m.get("from", "<Unknown>"))
        print("Subject:", m.get("subject", "<No Subject>"))
        if "date" in m:
            print("Date:   ", m.get("date"))
        body = m.get("body") or m.get("html") or ""
        print("Body:   ", body)
        code = extract_verification_code(m)
        if code:
            print(f">>> Extracted Code: {code}")


def main():
    parser = argparse.ArgumentParser(description="TempMail.lol client & verification code extractor.")
    parser.add_argument("target", nargs="?", default=None,
                        help="Email address or token to check / view")
    parser.add_argument("--create", action="store_true", default=False,
                        help="Create a new temporary email address")
    parser.add_argument("--first", "--first-name", dest="first_name", default=None,
                        help="User first name to construct email prefix")
    parser.add_argument("--last", "--last-name", dest="last_name", default=None,
                        help="User last name to construct email prefix")
    parser.add_argument("--prefix", default=None,
                        help="Explicit email prefix")
    parser.add_argument("--wait-code", action="store_true", default=False,
                        help="Wait for verification code on the created or specified email")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Wait timeout in seconds (default: 120)")
    parser.add_argument("--list", action="store_true", default=False,
                        help="List all saved email addresses and tokens")
    args = parser.parse_args()

    if args.list:
        inboxes = load_inboxes()
        print(f"\n{'='*70}\nSAVED INBOXES ({len(inboxes)} total) in {STORE}:\n{'='*70}")
        for addr, tok in inboxes.items():
            print(f" {addr:<38} -> {tok}")
        print(f"{'='*70}\n")
        return

    # Case 1: Create email with first & last name
    if args.create or args.first_name or args.last_name or args.prefix:
        if args.prefix:
            addr, token = new_email(prefix=args.prefix)
        else:
            addr, token = create_email_for_name(args.first_name, args.last_name)

        print(f"Address: {addr}")
        print(f"Token:   {token}")

        if args.wait_code:
            code = wait_for_verification_code(token=token, timeout=args.timeout)
            if code:
                print(f"\nSUCCESS: Extracted verification code: {code}\n")
            else:
                print("\nTIMEOUT: No verification code received.\n")
                sys.exit(1)
        return

    # Case 2: Target specified as argument or --wait-code
    if args.target:
        arg = args.target.strip()
        inboxes = load_inboxes()
        if arg in inboxes:
            token = inboxes[arg]
            addr = arg
        elif arg in inboxes.values() or (len(arg) > 20 and "@" not in arg):
            token = arg
            addr = next((k for k, v in inboxes.items() if v == token), None)
        else:
            print(f"Error: Address or token '{arg}' not found in {STORE}.")
            sys.exit(1)

        if args.wait_code:
            code = wait_for_verification_code(token=token, address=addr, timeout=args.timeout)
            if code:
                print(f"\nSUCCESS: Verification code: {code}\n")
            else:
                print("\nTIMEOUT: No verification code received.\n")
                sys.exit(1)
        else:
            show(token)
        return

    # Case 3: Default mode - create random email and wait for incoming mail
    print("Using API key" if API_KEY else "No API key set - using free tier")
    addr, token = new_email()
    print("Address:", addr)
    print("Token:  ", token)
    print("Waiting for mail (Ctrl+C to stop)...")
    try:
        while True:
            data = get_inbox(token)
            if data.get("expired"):
                print("Inbox expired.")
                break
            if data.get("emails"):
                show(token)
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print(f"\nStopped waiting. Inbox saved to {STORE}.")


if __name__ == "__main__":
    main()
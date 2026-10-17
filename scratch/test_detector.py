import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bs4 import BeautifulSoup
import re

def detect_error_in_soup(soup, url=""):
    # 1. Check for FSA Banner Error (id="fsa_Banner_CreateAccountAlert" or class="fsa-banner-error")
    banners = soup.find_all(lambda tag: tag.get('id') == 'fsa_Banner_CreateAccountAlert' or 'fsa-banner-error' in tag.get('class', []))
    for b in banners:
        # Check text
        header_el = b.find(class_=re.compile(r'fsa-banner-content-header|fsa-font-20-px', re.I)) or b.find(['b', 'strong', 'h2', 'h3'])
        body_el = b.find(class_=re.compile(r'fsa-banner-content-body|fsa-body-text', re.I))
        
        header_text = header_el.get_text(strip=True) if header_el else ""
        body_text = body_el.get_text(separator=' ', strip=True) if body_el else ""
        full_text = b.get_text(separator=' ', strip=True)
        
        # Clean up aidan / chat references if accidentally matched
        if any(x in full_text.lower() for x in ['aidan', 'feedback', 'how much money']):
            continue
            
        title = header_text or "Signup Error"
        # If title is in body, avoid duplicating
        msg = body_text or full_text
        return {
            "type": "banner_error",
            "title": title,
            "message": msg,
            "url": url
        }

    # 2. Check for known error headings on page (h1, h2, h3)
    known_error_patterns = [
        r"Account\s+Already\s+Exists",
        r"Can'?t\s+Create\s+Your\s+Account",
        r"We'?re\s+Unable\s+to\s+Create\s+Your\s+Account",
        r"Unable\s+to\s+Create\s+Your\s+Account",
        r"Unable\s+to\s+Verify\s+Your\s+Identity",
        r"An\s+account\s+already\s+exists",
    ]
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'div']):
        h_text = h.get_text(strip=True)
        for pat in known_error_patterns:
            if re.search(pat, h_text, re.I):
                # Make sure it's not a normal label
                if len(h_text) < 100:
                    # Find surrounding container or parent text for context
                    container = h.find_parent('div', class_=re.compile(r'card|banner|container|content|alert', re.I)) or h.parent
                    msg = container.get_text(separator=' ', strip=True) if container else h_text
                    if len(msg) > 400:
                        msg = msg[:400] + "..."
                    return {
                        "type": "heading_error",
                        "title": h_text,
                        "message": msg,
                        "url": url
                    }

    # 3. Check for specific alert roles or danger alerts
    alerts = soup.find_all(attrs={"role": "alert"}) + soup.find_all(class_=re.compile(r'alert-danger|fsa-alert-error', re.I))
    for a in alerts:
        txt = a.get_text(separator=' ', strip=True)
        if not txt or any(x in txt.lower() for x in ['aidan', 'chat', 'feedback', 'do you need help']):
            continue
        if any(err_word in txt.lower() for err_word in ['error', 'already exists', 'unable to', 'invalid', 'failed', 'cannot']):
            if len(txt) > 20 and len(txt) < 400:
                return {
                    "type": "role_alert_error",
                    "title": "Form Alert Error",
                    "message": txt,
                    "url": url
                }

    return None

test_files = [
    "Account Already Exists.html",
    "Can't Create Your Account.html",
    "unable-to-create.html",
    "mobile-phone-number.html",
    "mailing-address.html",
    "two-step-verification.html",
    "account-created.html"
]

for tf in test_files:
    soup = BeautifulSoup(open(tf, encoding='utf-8', errors='ignore').read(), 'html.parser')
    res = detect_error_in_soup(soup, url="https://studentaid.gov/" + tf)
    print(f"=== {tf} ===")
    if res:
        print(f"  FOUND ERROR: [{res['type']}] '{res['title']}'")
        print(f"  MESSAGE: {res['message'][:120]}...")
    else:
        print("  NO ERROR (clean page)")

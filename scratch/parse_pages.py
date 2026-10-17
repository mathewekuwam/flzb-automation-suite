import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bs4 import BeautifulSoup

def inspect_file(filename):
    print("=" * 60)
    print(f"FILE: {filename}")
    print("=" * 60)
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return

    soup = BeautifulSoup(html, 'html.parser')
    print("Title:", soup.title.string.strip() if soup.title and soup.title.string else "No Title")

    # Inputs
    inputs = soup.find_all(['input', 'select', 'textarea'])
    print(f"\n--- Inputs ({len(inputs)}) ---")
    for inp in inputs:
        inp_id = inp.get('id', '')
        inp_name = inp.get('name', '')
        inp_type = inp.get('type', inp.name)
        inp_aria = inp.get('aria-label', '')
        inp_ph = inp.get('placeholder', '')
        # Don't show chat/virtual-assistant inputs if any
        if 'chat' in inp_id.lower() or 'va-' in inp_id.lower():
            continue
        print(f"  Tag: {inp.name} | id: '{inp_id}' | name: '{inp_name}' | type: '{inp_type}' | aria: '{inp_aria}' | ph: '{inp_ph}'")
        if inp.name == 'select':
            opts = [o.get_text(strip=True) for o in inp.find_all('option')]
            print(f"    Options ({len(opts)}): {opts[:10]}")

    # Buttons and Links with buttons
    buttons = soup.find_all(['button', 'a'])
    print(f"\n--- Relevant Buttons & Links ---")
    for btn in buttons:
        btn_id = btn.get('id', '')
        btn_txt = btn.get_text(strip=True)
        if not btn_txt and not btn_id:
            continue
        if any(x in btn_id.lower() for x in ['chat', 'va-', 'audio', 'minimize', 'closeinfo']):
            continue
        if len(btn_txt) > 60:
            btn_txt = btn_txt[:60] + "..."
        if btn_id.startswith('fsa_') or any(w in btn_txt.lower() for w in ['continue', 'phone', 'address', 'agree', 'backup', 'next', 'submit', 'back']):
            print(f"  Tag: {btn.name} | id: '{btn_id}' | text: '{btn_txt}' | class: '{btn.get('class', [])}'")

    # Check for specific headings or key text
    print("\n--- Key text / Headings ---")
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'label']):
        txt = h.get_text(strip=True)
        h_id = h.get('id', '')
        for_id = h.get('for', '')
        if any(k in txt.lower() for k in ['address', 'phone', 'backup', 'verification', 'terms', 'agree', 'unable', 'created', 'city', 'state', 'zip']):
            if len(txt) > 100:
                txt = txt[:100] + "..."
            print(f"  {h.name} (id='{h_id}', for='{for_id}'): {txt}")

for f in ['mobile-phone-number.html', 'unable-to-create.html', 'mailing-address.html', 'two-step-verification.html', 'account-created.html']:
    inspect_file(f)

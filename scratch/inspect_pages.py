import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

def inspect_detail(fn):
    print("="*70)
    print("INSPECTING:", fn)
    print("="*70)
    with open(fn, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    root = soup.find('fsa-root') or soup.body
    # print form controls
    for fc in root.find_all(['input', 'select', 'textarea', 'button', 'a']):
        el_id = fc.get('id', '')
        if any(x in el_id.lower() for x in ['footer', 'header', 'chat', 'audio', 'minimize', 'close', 'survey', 'toggle']):
            continue
        tag = fc.name
        t = fc.get_text(strip=True)
        lbl = ""
        if el_id:
            lbl_el = root.find('label', {'for': el_id})
            if lbl_el:
                lbl = lbl_el.get_text(strip=True)
        print(f"[{tag}] id='{el_id}' name='{fc.get('name')}' type='{fc.get('type')}' label='{lbl}' text='{t[:50]}' placeholder='{fc.get('placeholder')}' class='{fc.get('class')}'")

inspect_detail('mailing-address.html')
inspect_detail('two-step-verification.html')



import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup
import re

with open('two-step-verification.html', 'r', encoding='utf-8', errors='ignore') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print("--- BACKUP CODE SEARCH ---")
for el in soup.find_all(text=re.compile(r'backup', re.I)):
    parent = el.parent
    print("Found text:", repr(str(el).strip()[:100]))
    container = parent.find_parent('div', class_=re.compile(r'card|container|box|row|col', re.I)) or parent.parent
    print("Container HTML:")
    print(container.prettify()[:1500])
    print("="*60)

print("\n--- TERMS & CONDITIONS CHECKBOX ---")
cb = soup.find(id='fsa_Checkbox_termsAndConditionsCheckbox')
if cb:
    parent = cb.find_parent('div') or cb.parent
    print("Checkbox parent HTML:")
    print(parent.prettify()[:1000])

print("\n--- CONTINUE / CREATE ACCOUNT BUTTON ---")
for btn_id in ['fsa_Button_MfaStep_Continue', 'fsa_Button_Continue']:
    b = soup.find(id=btn_id)
    if b:
        print(f"Button {btn_id}:", b.prettify()[:500])

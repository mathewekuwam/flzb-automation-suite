import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bs4 import BeautifulSoup
import re

for filename in ['Account Already Exists.html', "Can't Create Your Account.html"]:
    print("=" * 70)
    print("FILE:", filename)
    print("=" * 70)
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except Exception as e:
        print("Error reading file:", e)
        continue

    soup = BeautifulSoup(html, 'html.parser')
    print("Title:", soup.title.string.strip() if soup.title and soup.title.string else "None")
    
    # Headings
    print("\n--- Headings ---")
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        txt = h.get_text(strip=True)
        if txt and len(txt) < 150:
            print(f"{h.name} (id={h.get('id')}): {txt}")
            
    # Alerts / error banners / error messages
    print("\n--- Alerts & Errors ---")
    alerts = soup.find_all(class_=re.compile(r'alert|error|warn|danger|banner|notification', re.I))
    for a in alerts:
        t = a.get_text(separator=' ', strip=True)
        # Filter out Aidan chat
        if not t or any(x in t.lower() for x in ['aidan', 'chat', 'feedback', 'how much money']):
            continue
        if len(t) < 300:
            print(f"[{a.name} class={a.get('class')} id={a.get('id')}]: {t}")

    # Modal dialogs
    print("\n--- Modals ---")
    modals = soup.find_all(attrs={'role': 'dialog'}) + soup.find_all(class_=re.compile(r'modal', re.I))
    for m in modals:
        t = m.get_text(separator=' ', strip=True)
        if t and not any(x in t.lower() for x in ['aidan', 'chat']):
            print(f"Modal (id={m.get('id')}): {t[:250]}...")

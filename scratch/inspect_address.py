import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup

with open('mailing-address.html', 'r', encoding='utf-8', errors='ignore') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

for inp_id in ['fsa_Typeahead_AddressCountry', 'fsa_Typeahead_AddressState', 'fsa_Input_AddressAddressLine1', 'fsa_Input_AddressCity', 'fsa_Input_AddressPostalCode']:
    el = soup.find(id=inp_id)
    if el:
        parent = el.find_parent('div', class_='form-group') or el.parent.parent
        print(f"=== {inp_id} ===")
        print(parent.prettify()[:1000])

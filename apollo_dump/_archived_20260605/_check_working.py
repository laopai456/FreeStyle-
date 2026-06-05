# _check_working.py
import sys, os
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
sys.stdout.reconfigure(encoding='utf-8')
from repack_pak import PGFNPak

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
XOR_KEY = 0xFF

# Check items that the user says work
working_codes = [50125711, 50122451]
for code in working_codes:
    print(f'\n=== {code} ===')
    for pak_num in [742, 768, 767, 764]:
        ipak_path = os.path.join(GAME, f'item{pak_num}.pak')
        rpak_path = os.path.join(GAME, f'res{pak_num}.pak')
        
        # Check item PAK
        if os.path.exists(ipak_path):
            ipak = PGFNPak(ipak_path)
            bml = [e for e in ipak.entries if str(code) in e['name']]
            if bml:
                print(f'  item{pak_num}.pak BML: {bml}')
        
        # Check res PAK
        if os.path.exists(rpak_path):
            rpak = PGFNPak(rpak_path)
            smds = [e for e in rpak.entries if str(code) in e['name']]
            if smds:
                print(f'  res{pak_num}.pak SMD: {smds}')

# Also check what item PAK has 50120651's BML (if any)
print('\n=== Searching 50120651 in ALL item PAKs ===')
for fn in sorted(os.listdir(GAME)):
    if fn.startswith('item') and fn.endswith('.pak') and '.pak.' not in fn:
        ipak_path = os.path.join(GAME, fn)
        if os.path.getsize(ipak_path) < 500*1024:
            continue  # skip tiny PAKs
        try:
            ipak = PGFNPak(ipak_path)
            for e in ipak.entries:
                if '50120651' in e['name']:
                    print(f'  {fn}: {e}')
        except:
            pass

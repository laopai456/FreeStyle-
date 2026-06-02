# _check_bml.py
import sys, os
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
sys.stdout.reconfigure(encoding='utf-8')
from repack_pak import PGFNPak

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
XOR_KEY = 0xFF

ipak = PGFNPak(os.path.join(GAME, 'item727.pak'))

# Check BML entries related to 501206xx
for target in ['50120611', '50120621', '50120641']:
    for e in ipak.entries:
        if target in e['name']:
            with open(os.path.join(GAME, 'item727.pak'), 'rb') as f:
                f.seek(e['data_offset'])
                raw = f.read(e['data_size'])
            dec = bytes(b ^ XOR_KEY for b in raw)
            print(f'=== {e["name"]} ({len(dec)}B) ===')
            print(dec.decode('utf-8', errors='replace'))
            print()

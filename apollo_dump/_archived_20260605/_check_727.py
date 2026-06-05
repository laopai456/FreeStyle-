# _check_727.py
import sys, os
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
sys.stdout.reconfigure(encoding='utf-8')
from repack_pak import PGFNPak

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
ipak = PGFNPak(os.path.join(GAME, 'item727.pak'))
print('=== item727.pak ===')
for e in ipak.entries:
    print(f'  {e["name"]} ({e["data_size"]}B)')

print()
print('=== res727.pak (items starting with i5012*) ===')
rpak = PGFNPak(os.path.join(GAME, 'res727.pak'))
for e in rpak.entries:
    if 'i5012' in e['name']:
        print(f'  {e["name"]} ({e["data_size"]}B)')

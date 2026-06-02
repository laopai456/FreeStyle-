# _find_bml.py
import sys, os
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
sys.stdout.reconfigure(encoding='utf-8')

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
XOR_KEY = 0xFF

target = 'i50120651.bml'

# Search all item*.pak files
import glob
for pak_path in sorted(glob.glob(os.path.join(GAME, 'item*.pak'))):
    if '.pak.pak' in pak_path:
        continue
    name = os.path.basename(pak_path)
    with open(pak_path, 'rb') as f:
        data = f.read()
    # Try XOR decrypt search
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ XOR_KEY
    if target.encode() in bytes(dec):
        print(f'FOUND in {name}')
        idx = bytes(dec).find(target.encode())
        print(f'  offset: 0x{idx:x}')
        # Show context
        print(f'  context: {bytes(dec)[idx-10:idx+60]}')
        break
else:
    print(f'{target} NOT FOUND in any item*.pak')

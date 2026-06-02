# debug.py
import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8')

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
XOR_KEY = 0xFF

def xor(data):
    return bytes(b ^ XOR_KEY for b in data)

rp = os.path.join(GAME, 'res727.pak')
with open(rp, 'rb') as f:
    raw = f.read()
print(f'Size: {len(raw)} bytes, is_xor: {raw[0] > 0x7F}')
print(f'First 24 bytes: {raw[:24].hex()}')

# Use simple byte search for i50120651 prefix
prefix = b'i50120651'
buf = raw  # res PAK is not XORed

# Scan for the prefix
pos = 0
found = []
while True:
    idx = buf.find(prefix, pos)
    if idx < 0: break
    # Check what comes next  
    after = buf[idx:idx+30]
    # Find null terminator
    null_pos = after.find(b'\x00')
    if null_pos > 0:
        name = after[:null_pos].decode('ascii', errors='replace')
        # Read entry header: 20 bytes before filename
        hdr_start = idx - 20
        if hdr_start >= 0:
            d0 = struct.unpack_from('<I', buf, hdr_start)[0]
            nl = struct.unpack_from('<I', buf, hdr_start+4)[0]
            d1 = struct.unpack_from('<I', buf, hdr_start+8)[0]
            ds = struct.unpack_from('<I', buf, hdr_start+12)[0]
            print(f'\nFound: {name}')
            print(f'  hdr_start=0x{hdr_start:x} d0=0x{d0:x} nl={nl} d1=0x{d1:x} ds={ds}')
            # calc data offset  
            data_start = hdr_start + 20 + nl
            pad = (4 - (data_start % 4)) % 4
            data_start += pad
            print(f'  data_start=0x{data_start:x} expected=off')
    pos = idx + 1

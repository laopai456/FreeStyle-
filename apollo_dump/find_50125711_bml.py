import sys, struct
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
sys.stdout.reconfigure(encoding='utf-8')

XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

pak = PGFNPak(r'C:\Program Files (x86)\T2CN\街头篮球\item768.pak')

# 搜索所有BML，找到包含50125711的
with open(pak.path, 'rb') as f:
    raw_data = f.read()

print(f'item768.pak: {len(pak.entries)} entries')
print()

target = '50125711'

for entry in pak.entries:
    raw = raw_data[entry['data_offset']:entry['data_offset'] + entry['data_size']]
    decoded = xor_crypt(raw)
    text = decoded.decode('utf-8', errors='replace')
    if target in text:
        print(f'=== {entry["name"]}: offset=0x{entry["data_offset"]:X} size={entry["data_size"]} ===')
        print(text)
        print()

# 也检查i50125701.bml
print('\n=== i50125701.bml 检查 ===')
e = pak.find_entry('i50125701.bml')
if e:
    raw = raw_data[e['data_offset']:e['data_offset'] + e['data_size']]
    decoded = xor_crypt(raw)
    text = decoded.decode('utf-8', errors='replace')
    print(f'size={e["data_size"]}B')
    print(text)
    # 提取mesh和texture
    print('\nmesh/texture:')
    for line in text.split('\n'):
        line = line.strip()
        if 'mesh' in line.lower() or 'texture' in line.lower():
            print(f'  {line}')
else:
    print('NOT FOUND')

# 也检查i50125691.bml
print('\n=== i50125691.bml 检查 ===')
e2 = pak.find_entry('i50125691.bml')
if e2:
    raw = raw_data[e2['data_offset']:e2['data_offset'] + e2['data_size']]
    decoded = xor_crypt(raw)
    text = decoded.decode('utf-8', errors='replace')
    print(f'size={e2["data_size"]}B')
    print(text[:500])
"""提取目标发型 SMD"""
import os, sys
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

target = 'i50125711_ms.smd'
pak_path = r'C:\Program Files (x86)\T2CN\街头篮球\res768.pak'
out_path = os.path.join(os.path.dirname(__file__), 'apollo_dump', target)

print(f'Loading {pak_path}...')
pak = PGFNPak(pak_path)
print(f'{pak.file_count} files')

found = pak.find_entry(target)
if found:
    print(f'Found: {found["name"]}  offset=0x{found["data_offset"]:X}  size={found["data_size"]}')
    with open(out_path, 'wb') as f:
        f.write(found['data'])
    print(f'Saved: {out_path}  ({found["data_size"]} bytes)')
else:
    print(f'{target} NOT FOUND')
    print('\nSimilar entries:')
    for e in pak.entries:
        if 'ms.smd' in e['name'].lower() or '501257' in e['name']:
            print(f'  {e["name"]}  size={e["data_size"]}')
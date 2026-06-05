"""compare_paks.py — 比对桌面标准源文件 vs 游戏目录文件"""
import hashlib, os, sys
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
sys.stdout.reconfigure(encoding='utf-8')

DESKTOP_DIR = r'C:\Users\w\Desktop'
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'

for name in ['item768.pak', 'res768.pak']:
    src = os.path.join(DESKTOP_DIR, name)
    dst = os.path.join(GAME_DIR, name)
    
    print(f'=== {name} ===')
    src_data = open(src, 'rb').read()
    dst_data = open(dst, 'rb').read()
    
    src_md5 = hashlib.md5(src_data).hexdigest()
    dst_md5 = hashlib.md5(dst_data).hexdigest()
    
    print(f'  桌面({len(src_data)}B): {src_md5}')
    print(f'  游戏({len(dst_data)}B): {dst_md5}')
    
    if src_data == dst_data:
        print(f'  [OK] 完全相同')
    else:
        print(f'  [!!!] 已修改! MD5不同')
        # 找出第一个不同的字节位置
        for i, (a, b) in enumerate(zip(src_data, dst_data)):
            if a != b:
                print(f'  首个差异: offset 0x{i:X} 桌面=0x{a:02X} 游戏=0x{b:02X}')
                break
        if len(src_data) != len(dst_data):
            print(f'  大小不同: 桌面={len(src_data)} 游戏={len(dst_data)}')
    
    print()

# 也解析桌面标准item768.pak的BML
print('=== 桌面标准 item768.pak BML解析 ===')
src_pak = PGFNPak(src)
print(f'总条目: {len(src_pak.entries)}')
bml_entries = [e for e in src_pak.entries if e['name'].endswith('.bml')]
print(f'BML条目: {len(bml_entries)}')
for e in bml_entries:
    print(f'  {e["name"]}: offset=0x{e["data_offset"]:X} size={e["data_size"]}')
    raw = src_data[e['data_offset']:e['data_offset'] + e['data_size']]
    decoded = bytes(b ^ 0xFF for b in raw)
    text = decoded.decode('utf-8', errors='replace')
    # 提取所有引用的itemcode
    for line in text.split('\n'):
        line = line.strip()
        if 'mesh' in line.lower() or 'texture' in line.lower():
            print(f'    {line}')

# 也解析桌面标准res768.pak
print('\n=== 桌面标准 res768.pak 资源 ===')
res_pak = PGFNPak(os.path.join(DESKTOP_DIR, 'res768.pak'))
res_data = open(os.path.join(DESKTOP_DIR, 'res768.pak'), 'rb').read()
print(f'总条目: {len(res_pak.entries)}')
# 找50125711相关的资源
for e in res_pak.entries:
    if '50125711' in e['name'].lower() or '50125701' in e['name'].lower():
        print(f'  {e["name"]} ({e["data_size"]}B)')

# 对比游戏目录的res768.pak
print('\n=== 游戏目录 res768.pak 50125711资源 ===')
game_res = PGFNPak(os.path.join(GAME_DIR, 'res768.pak'))
for e in game_res.entries:
    if '50125711' in e['name'].lower() or '50125701' in e['name'].lower():
        print(f'  {e["name"]} ({e["data_size"]}B)')

# 关键：在桌面标准item768.pak中搜索50125711的BML数据
print('\n=== 桌面标准item768.pak中50125711搜索 ===')
XOR_KEY = 0xFF
dec = bytes(b ^ XOR_KEY for b in src_data)
idx = dec.find(b'50125711')
if idx >= 0:
    print(f'找到 50125711 在XOR解码偏移 0x{idx:X}')
    # 提取完整<root>段
    rs = dec.rfind(b'<root>', 0, idx)
    re = dec.find(b'</root>', idx) + len(b'</root>')
    section = dec[rs:re]
    text = section.decode('utf-8', errors='replace')
    print(f'XML段: {rs}-{re} ({len(section)}B)')
    print(text)
else:
    print('未找到!')
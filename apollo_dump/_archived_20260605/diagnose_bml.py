"""diagnose_bml.py — 诊断为什么游戏找不到BML"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'

print('=== 1. 游戏目录PAK文件列表 ===')
paks = [f for f in os.listdir(GAME) if f.endswith('.pak')]
for p in sorted(paks):
    sz = os.path.getsize(os.path.join(GAME, p))
    tag = ''
    if 'item' in p.lower(): tag = ' <-- ITEM PAK'
    if 'res' in p.lower(): tag = ' <-- RES PAK'
    print(f'  {p} ({sz}B){tag}')

# 2. 检查item.pak (可能的主item包)
item_pak = os.path.join(GAME, 'item.pak')
if os.path.exists(item_pak):
    print(f'\n=== 2. item.pak 内容 ===')
    pak = PGFNPak(item_pak)
    print(f'  条目: {len(pak.entries)}')
    # 搜索i50125711
    data = open(item_pak, 'rb').read()
    dec = bytes(b ^ 0xFF for b in data)
    if b'50125711' in dec:
        print(f'  [!!!] item.pak 包含 50125711!')
        idx = dec.find(b'50125711')
        rs = dec.rfind(b'<root>', 0, idx)
        re = dec.find(b'</root>', idx) + len(b'</root>')
        print(f'  offset: 0x{rs:X}')
    else:
        print(f'  [---] item.pak 不包含 50125711')
    # 列出前几个条目
    for e in pak.entries[:5]:
        print(f'    {e["name"]} ({e["data_size"]}B)')

# 3. 检查 item_ext.pak
ext_pak = os.path.join(GAME, 'item_ext.pak')
if os.path.exists(ext_pak):
    print(f'\n=== 3. item_ext.pak 内容 ===')
    pak = PGFNPak(ext_pak)
    print(f'  条目: {len(pak.entries)}')
    data = open(ext_pak, 'rb').read()
    dec = bytes(b ^ 0xFF for b in data)
    if b'50125711' in dec:
        print(f'  [!!!] 包含 50125711!')
    else:
        print(f'  [---] 不包含 50125711')

# 4. 检查其他可能的主item PAK
print(f'\n=== 4. 搜索所有PAK中的50125711 ===')
for p in sorted(os.listdir(GAME)):
    if p.endswith('.pak'):
        full = os.path.join(GAME, p)
        with open(full, 'rb') as f:
            data = f.read()
        dec = bytes(b ^ 0xFF for b in data)
        if b'50125711' in dec or b'50125711.bml' in dec:
            print(f'  [!!!] {p} 包含 50125711!')
        elif b'50125711' in data:
            print(f'  [RAW] {p} 原始数据含50125711')

# 5. 检查游戏是否查松散文件: 检查item\（相对于游戏根目录）
print(f'\n=== 5. 松散文件目录检查 ===')
test_dirs = [
    os.path.join(GAME, 'item'),
    os.path.join(GAME, 'Resource', 'item'),
    os.path.join(GAME, 'data', 'item'),
]
for d in test_dirs:
    if os.path.exists(d):
        bmls = [f for f in os.listdir(d) if '50125711' in f]
        print(f'  [OK] {d}')
        print(f'    50125711文件: {bmls}')
    else:
        print(f'  [---] {d} 不存在')

# 6. 换个位置试试：游戏根目录\item\
item_dir = os.path.join(GAME, 'item')
print(f'\n=== 6. 尝试部署到游戏根目录\\item\\ ===')
if os.path.exists(item_dir):
    print(f'  [OK] item\\目录存在')
    existing = [f for f in os.listdir(item_dir) if f.endswith('.bml')]
    print(f'  已有BML: {existing[:5]}')
else:
    print(f'  目录不存在，这是可用的目标')
    # 列出根目录下可能的相关子目录
    dirs = [d for d in os.listdir(GAME) if os.path.isdir(os.path.join(GAME, d))]
    print(f'  根目录子目录: {[d for d in dirs if "item" in d.lower() or "resource" in d.lower() or "data" in d.lower()]}')
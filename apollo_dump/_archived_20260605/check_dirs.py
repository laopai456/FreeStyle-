import os, sys
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'

print('=== 目录检查 ===')
for p in ['item', r'Resource\item', r'data\item']:
    d = os.path.join(GAME, p)
    if os.path.exists(d):
        bmls = [f for f in os.listdir(d) if f.endswith('.bml')]
        print(f'  [OK] {p}: {len(bmls)} BMLs')
        for f in bmls:
            if '50125' in f:
                print(f'    -> {f}')
    else:
        print(f'  [---] {p} 不存在')

print()
print('=== item.pak BML格式分析 ===')
pak = PGFNPak(os.path.join(GAME, 'item.pak'))
bmls = [e for e in pak.entries if e['name'].endswith('.bml')]
print(f'总条目: {len(pak.entries)}, BML: {len(bmls)}')

# 前10个BML
print('前10个BML:')
for e in bmls[:10]:
    print(f'  {e["name"]} ({e["data_size"]}B)')

# 检查BML命名模式：c开头 vs i开头
c_bmls = [e for e in bmls if e['name'].startswith('c')]
i_bmls = [e for e in bmls if e['name'].startswith('i')]
print(f'\nc* BMLs: {len(c_bmls)}')
print(f'i* BMLs: {len(i_bmls)}')

# 查找i50421开头的
i50421 = [e for e in i_bmls if 'i50421' in e['name']]
print(f'i50421* BMLs: {i50421}')

# 关键：item.pak中的BML是什么格式？
if c_bmls:
    # 抽查一个c开头的BML
    data = open(os.path.join(GAME, 'item.pak'), 'rb').read()
    e = c_bmls[0]
    raw = data[e['data_offset']:e['data_offset']+e['data_size']]
    dec = bytes(b ^ 0xFF for b in raw)
    print(f'\nc开头BML示例 ({e["name"]}, {e["data_size"]}B):')
    print(dec.decode('utf-8', errors='replace')[:300])

print()
print('=== item768.pak 在游戏中的注册 ===')
# item.pak中是否有引用item768的条目？
data = open(os.path.join(GAME, 'item.pak'), 'rb').read()
dec = bytes(b ^ 0xFF for b in data)
for s in [b'item768', b'res768', b'50125711']:
    idx = dec.find(s)
    print(f'  item.pak中含{s.decode()}: {idx >= 0}')
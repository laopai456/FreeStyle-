"""check_state.py — 检查item768.pak和当前BML状态"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF

# 1. item768.pak条目
print('=== item768.pak 所有条目 ===')
ipak = PGFNPak(os.path.join(GAME, 'item768.pak'))
for e in ipak.entries:
    print(f'  {e["name"]} ({e["data_size"]}B) @0x{e["data_offset"]:X}')

# 2. item768.pak中50125711的位置
print('\n=== item768.pak中50125711出现位置 ===')
with open(os.path.join(GAME, 'item768.pak'), 'rb') as f:
    data = f.read()
dec = bytes(b ^ XOR_KEY for b in data)

pos = 0
while True:
    idx = dec.find(b'50125711', pos)
    if idx < 0:
        break
    ctx = dec[max(0,idx-15):min(len(dec),idx+90)]
    try:
        ctx_str = ctx.decode('utf-8', errors='replace')
        print(f'  @0x{idx:X}: ...{ctx_str}...')
    except:
        print(f'  @0x{idx:X}: (binary)')
    pos = idx + 1

# 3. 从item768.pak提取原始的50125711 BML片段
print('\n=== item768.pak原始50125711 BML (完整) ===')
idx = dec.find(b'50125711', dec.find(b'50125701') + 1)
if idx >= 0:
    rs = dec.rfind(b'<root>', 0, idx)
    re_end = dec.find(b'</root>', idx)
    if rs >= 0 and re_end >= 0:
        re_end += len(b'</root>')
        raw_bml = dec[rs:re_end]
        print(f'  偏移: 0x{rs:X}-0x{re_end:X} ({re_end-rs}B)')
        print(raw_bml.decode('utf-8', errors='replace'))

# 4. res768.pak中所有SMD（直接解析文件名）
print('\n=== res768.pak中50125711 SMD (PGFNPak) ===')
try:
    rpak = PGFNPak(os.path.join(GAME, 'res768.pak'))
    for e in rpak.entries:
        if '50125711' in e['name']:
            print(f'  {e["name"]} ({e["data_size"]}B, {e["data_size"]/1024:.1f}KB) @0x{e["data_offset"]:X}')
except Exception as ex:
    print(f'  解析失败: {ex}')

# 5. 搜索res768.pak中是否有i50125711.png纹理
print('\n=== res768.pak中搜索i50125711.png ===')
with open(os.path.join(GAME, 'res768.pak'), 'rb') as f:
    rdata = f.read()
if b'i50125711.png' in rdata:
    idx = rdata.find(b'i50125711.png')
    print(f'  找到 @0x{idx:X}')
else:
    print('  未找到!')

# 6. 搜索所有PAK中是否有i50125711.png
print('\n=== 在所有res PAK中搜索i50125711.png ===')
import glob
for pak_path in sorted(glob.glob(os.path.join(GAME, 'res*.pak'))):
    try:
        with open(pak_path, 'rb') as f:
            d = f.read()
        if b'i50125711.png' in d or b'i50125711' in d:
            # 具体检查.png
            if b'i50125711.png' in d:
                print(f'  {os.path.basename(pak_path)}: 找到 i50125711.png')
    except:
        pass
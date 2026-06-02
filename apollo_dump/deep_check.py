"""deep_check.py — 深度检查item768.pak结构"""
import sys, struct, re
sys.stdout.reconfigure(encoding='utf-8')

DESKTOP = r'C:\Users\w\Desktop'
GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

# 1. 检查文件头和原始结构
print('=== item768.pak 文件头分析 ===')
for label, path in [('桌面', DESKTOP), ('游戏', GAME)]:
    fpath = path + r'\item768.pak'
    data = open(fpath, 'rb').read()
    print(f'\n[{label}] {fpath}')
    print(f'  大小: {len(data)}B')
    print(f'  前64字节 hex: {data[:64].hex()}')
    print(f'  前64字节 ascii: {data[:64]}')
    
    # PGFN header check
    if data[:4] == b'PGFN':
        print(f'  文件类型: PGFN (PAK)')
    
    # 搜索所有可能的BML相关内容
    dec = xor_crypt(data)
    
    # 搜索50125711 (多种方式)
    for search in [b'50125711', b'i50125711', b'res768']:
        idx = dec.find(search)
        if idx >= 0:
            print(f'  [{search.decode()}] 在XOR解码数据中偏移 0x{idx:X}')
            ctx_start = max(0, idx - 50)
            ctx_end = min(len(dec), idx + 100)
            ctx = dec[ctx_start:ctx_end]
            print(f'    上下文: {ctx[:200]}')
        else:
            print(f'  [{search.decode()}] 在XOR解码数据中未找到')
    
    # 也搜索原始数据
    for search in [b'50125711', b'i50125711']:
        idx = data.find(search)
        if idx >= 0:
            print(f'  [{search.decode()}] 在原始数据中偏移 0x{idx:X}')
        else:
            print(f'  [{search.decode()}] 在原始数据中未找到')

# 2. PGFNPak 两次解析对比
print('\n\n=== PGFNPak 解析对比 ===')
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

for label, path in [('桌面', DESKTOP), ('游戏', GAME)]:
    fpath = path + r'\item768.pak'
    pak = PGFNPak(fpath)
    print(f'\n[{label}] {fpath}')
    print(f'  条目数: {len(pak.entries)}')
    
    bml_entries = [e for e in pak.entries if 'bml' in e['name'].lower()]
    print(f'  BML条目: {len(bml_entries)}')
    
    # 列出前10个条目名称
    print(f'  前15个条目:')
    for e in pak.entries[:15]:
        print(f'    {e["name"]}  off=0x{e["data_offset"]:X}  sz={e["data_size"]}')
    
    # 列出所有含50125的条目
    ic_entries = [e for e in pak.entries if '50125' in e['name']]
    print(f'  含50125的条目: {len(ic_entries)}')
    for e in ic_entries[:10]:
        print(f'    {e["name"]}  off=0x{e["data_offset"]:X}  sz={e["data_size"]}')

# 3. 手动搜索BML文件签名
print('\n\n=== 手动扫描item768.pak中的BML ===')
data = open(DESKTOP + r'\item768.pak', 'rb').read()
dec = xor_crypt(data)

# 搜索所有 <root> 标签
root_positions = [m.start() for m in re.finditer(b'<root>', dec)]
print(f'在XOR解码数据中找到 {len(root_positions)} 个 <root> 标签')
for i, pos in enumerate(root_positions):
    end = dec.find(b'</root>', pos)
    if end > 0:
        end += len(b'</root>')
        section = dec[pos:end]
        try:
            text = section.decode('utf-8', errors='replace')
            # 提取mesh引用判断哪个item
            meshes = re.findall(r'i50\d{6}', text)
            if meshes:
                print(f'  #{i}: offset 0x{pos:X} ({len(section)}B) items={set(meshes)}')
                if '50125711' in text:
                    print(f'    *** TARGET! ***')
        except:
            pass
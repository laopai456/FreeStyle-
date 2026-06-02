"""analyze_super_saiyan.py — 分析超赛系列的资源完整度"""
import sys, os
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

# 候选原始模型
candidates = [
    ('50125651', '767', '闪耀金超赛发型', 'pak767中,与紫色最近'),
    ('50119961', '723', '最强超赛发型', '最早的"最强"版本,可能是源模型'),
    ('50120651', '727', '极限超赛发型', '描述提到"极限赛亚人"'),
    ('50124241', '758', '金色超赛发型', '金色系'),
    ('50125711', '768', '紫色超赛发型', '当前目标,基准对照'),
]

for ic, pak_num, name, note in candidates:
    item_pak = os.path.join(GAME, f'item{pak_num}.pak')
    res_pak = os.path.join(GAME, f'res{pak_num}.pak')
    
    print(f'=== {ic} {name} (pak{pak_num}) {note} ===')
    
    # 检查PAK是否存在
    if not os.path.exists(item_pak):
        print(f'  item{pak_num}.pak 不存在!')
        continue
    if not os.path.exists(res_pak):
        print(f'  res{pak_num}.pak 不存在!')
        continue
    
    # 解析res PAK中的SMD资源
    rpak = PGFNPak(res_pak)
    smds = [e for e in rpak.entries if ic in e['name'] and e['name'].endswith('.smd')]
    pngs = [e for e in rpak.entries if ic in e['name'] and e['name'].endswith('.png')]
    
    print(f'  SMD文件 ({len(smds)}):')
    for s in smds:
        # 提取variant后缀
        name = s['name'].replace('.smd', '')
        # 提取_M后面的部分
        suffix = ''
        if '_' in name:
            parts = name.split('_')
            for p in parts[1:]:
                suffix += p + ' '
        print(f'    {s["name"]} ({s["data_size"]}B) variant={suffix.strip()}')
    
    print(f'  纹理文件 ({len(pngs)}):')
    for p in pngs:
        print(f'    {p["name"]} ({p["data_size"]}B)')
    
    # 解析item PAK中的BML
    ipak = PGFNPak(item_pak)
    with open(item_pak, 'rb') as f:
        ipak_data = f.read()
    
    # 搜索BML
    bml_entries = [e for e in ipak.entries if 'bml' in e['name'].lower() and ic in e['name']]
    if bml_entries:
        print(f'  BML条目:')
        for e in bml_entries:
            raw = ipak_data[e['data_offset']:e['data_offset']+e['data_size']]
            dec = xor_crypt(raw)
            text = dec.decode('utf-8', errors='replace')
            # 提取mesh路径
            import re
            meshes = set(re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', text))
            texs = set(re.findall(r'i5\d{7}[A-Za-z_]*\.png', text))
            print(f'    {e["name"]} ({e["data_size"]}B)')
            print(f'      引用mesh: {meshes}')
            print(f'      引用texture: {texs}')
    else:
        # 在XOR解码后的PAK中搜索BML内容
        dec = xor_crypt(ipak_data)
        idx = dec.find(ic.encode())
        if idx >= 0:
            rs = dec.rfind(b'<root>', 0, idx)
            re = dec.find(b'</root>', idx) + len(b'</root>')
            if rs >= 0 and re > rs:
                text = dec[rs:re].decode('utf-8', errors='replace')
                import re
                meshes = set(re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', text))
                texs = set(re.findall(r'i5\d{7}[A-Za-z_]*\.png', text))
                print(f'  BML in gap (0x{rs:X}, {g_re-rs}B):')
            g_re = re
                print(f'    引用mesh: {meshes}')
                print(f'    引用texture: {texs}')
                # 检查character type
                char_types = re.findall(r'<character type="(\d+)"', text)
                print(f'    character types: {char_types}')
            else:
                print(f'  BML未找到')
        else:
            print(f'  BML未找到')
    
    print()
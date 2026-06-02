"""analyze_super_saiyan2.py — 分析超赛系列资源完整度"""
import sys, os
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
import regex as re_module
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

candidates = [
    ('50125651', '767', '闪耀金超赛', '与紫色最近,同属pak767已加载'),
    ('50119961', '723', '最强超赛', '最早的最强版本,270KB SMD'),
    ('50120651', '727', '极限超赛', '描述中极限赛亚人来源'),
    ('50124241', '758', '金色超赛', '另一个金色版本'),
    ('50125711', '768', '紫色超赛', '目标,基准对照'),
]

for ic, pak_num, name, note in candidates:
    item_pak_path = os.path.join(GAME, f'item{pak_num}.pak')
    res_pak_path = os.path.join(GAME, f'res{pak_num}.pak')
    
    print(f'=== {ic} {name} (pak{pak_num}) {note} ===')
    
    if not os.path.exists(item_pak_path):
        print(f'  item{pak_num}.pak 不存在!')
        continue
    if not os.path.exists(res_pak_path):
        print(f'  res{pak_num}.pak 不存在!')
        continue
    
    # Res PAK: SMD和texture
    rpak = PGFNPak(res_pak_path)
    smds = [(e['name'], e['data_size']) for e in rpak.entries 
            if ic in e['name'] and e['name'].endswith('.smd')]
    pngs = [(e['name'], e['data_size']) for e in rpak.entries 
            if ic in e['name'] and e['name'].endswith('.png')]
    
    print(f'  Res PAK SMD ({len(smds)}):')
    for sname, sz in smds:
        suffix = '_'.join(sname.replace('.smd','').split('_')[1:])
        print(f'    {sname} ({sz}B) [{suffix}]')
    
    print(f'  Res PAK PNG ({len(pngs)}):')
    for pname, sz in pngs:
        print(f'    {pname} ({sz}B)')
    
    # Item PAK: BML
    ipak = PGFNPak(item_pak_path)
    with open(item_pak_path, 'rb') as f:
        ipak_data = f.read()
    
    bml_entries = [e for e in ipak.entries if 'bml' in e['name'].lower() and ic in e['name']]
    if bml_entries:
        for e in bml_entries:
            raw = ipak_data[e['data_offset']:e['data_offset']+e['data_size']]
            dec = xor_crypt(raw)
            text = dec.decode('utf-8', errors='replace')
            meshes = set(re_module.findall(r'i5\d{7}_[A-Za-z_]+\.smd', text))
            texs = set(re_module.findall(r'i5\d{7}[A-Za-z_]*\.png', text))
            chars = re_module.findall(r'<character type="(\d+)"', text)
            print(f'  BML: {e["name"]} ({e["data_size"]}B) [独立条目]')
            print(f'    mesh引用({len(meshes)}): {sorted(meshes)}')
            print(f'    texture引用: {texs}')
            print(f'    character types: {chars}')
    else:
        # Gap BML
        dec = xor_crypt(ipak_data)
        idx = dec.find(ic.encode())
        if idx >= 0:
            rs = dec.rfind(b'<root>', 0, idx)
            g_re_end = dec.find(b'</root>', idx) + len(b'</root>')
            if rs >= 0 and g_re_end > rs:
                text = dec[rs:g_re_end].decode('utf-8', errors='replace')
                meshes = set(re_module.findall(r'i5\d{7}_[A-Za-z_]+\.smd', text))
                texs = set(re_module.findall(r'i5\d{7}[A-Za-z_]*\.png', text))
                chars = re_module.findall(r'<character type="(\d+)"', text)
                print(f'  BML: gap (0x{rs:X}, {g_re_end-rs}B) [间隙数据]')
                print(f'    mesh引用({len(meshes)}): {sorted(meshes)}')
                print(f'    texture引用: {texs}')
                print(f'    character types: {chars}')
            else:
                print(f'  BML: 未找到')
        else:
            print(f'  BML: 未找到')
    
    print()

# 特别对比: 闪耀金 vs 紫色 的SMD大小
print('=== 关键对比: SMD大小 ===')
for ic, pak_num, name, note in candidates:
    res_pak_path = os.path.join(GAME, f'res{pak_num}.pak')
    if os.path.exists(res_pak_path):
        rpak = PGFNPak(res_pak_path)
        smds = [(e['name'], e['data_size']) for e in rpak.entries 
                if ic in e['name'] and e['name'].endswith('.smd')]
        if smds:
            for sname, sz in smds:
                print(f'  {name}({ic}): {sname} = {sz}B = {sz/1024:.1f}KB')
        else:
            print(f'  {name}({ic}): 无SMD')
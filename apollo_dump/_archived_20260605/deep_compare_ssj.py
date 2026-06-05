"""deep_compare_ssj.py — 深入对比超赛系列资源，确定紫色超赛的原始模型"""
import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF
DB_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'


def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)


def find_bml_from_pak(pak_path, item_code):
    """直接从item PAK中搜索BML数据"""
    with open(pak_path, 'rb') as f:
        data = f.read()
    dec = xor_crypt(data)
    target = item_code.encode()
    idx = dec.find(target)
    if idx < 0:
        return None
    rs = dec.rfind(b'<root>', 0, idx)
    if rs < 0:
        return None
    re_end = dec.find(b'</root>', idx)
    if re_end < 0:
        return None
    re_end += len(b'</root>')
    return dec[rs:re_end].decode('utf-8', errors='replace')


def find_smd_entries_in_res(pak_path, item_code):
    """在res PAK中搜索SMD文件，通过SSKF魔数定位"""
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    # SMD文件以SSKF开头
    # 在文件中搜索 item_code (作为字符串出现)
    target = item_code.encode()
    results = []
    seen = set()
    
    pos = 0
    while True:
        idx = data.find(target, pos)
        if idx < 0:
            break
        
        # 尝试找SMD文件名：往前后扩展
        # 文件名可能在之前某处，通常格式是 i50120651_F.smd
        # 在data中，文件名通常在偏移量之前的entry table里
        
        # 方法：从idx往前搜索"SSKF"魔数
        search_start = max(0, idx - 500)  # 文件名通常在500字节内
        sskf = data.rfind(b'SSKF', search_start, idx + 100)
        
        if sskf >= 0:
            # 从SSKF往后找下一个SSKF或者合理的结束
            next_sskf = data.find(b'SSKF', sskf + 4)
            if next_sskf < 0:
                next_sskf = sskf + 1000000  # 最多1MB
            
            # 但从SSKF往后，合理的大小应该在数据范围内
            # SMD文件通常几KB到几百KB
            # 尝试读取SMD header来确定大小
            if sskf + 8 <= len(data):
                # SMD header: SSKF(4) + version(4) 
                # 之后可能有总大小信息
                # 保守估计：从SSKF到下一个SSKF或下一个不同文件名之间的区域
                smd_size = min(next_sskf - sskf, 500000)
            
            # 从SSKF位置往前找文件名
            # 文件名通常在entry table里，格式为 name\0
            name_start = sskf
            while name_start > 0 and data[name_start-1:name_start] != b'\x00':
                name_start -= 1
            
            # 向前扩展
            fname_search = data[name_start-100:name_start]
            # 找最后一个\0
            last_null = fname_search.rfind(b'\x00')
            if last_null >= 0:
                try:
                    fname = fname_search[last_null+1:].decode('utf-8', errors='replace')
                except:
                    fname = ''
            else:
                try:
                    fname = fname_search.decode('utf-8', errors='replace')
                except:
                    fname = ''
            
            fname = fname.strip('\x00').strip()
            
            if fname and item_code in fname and fname.endswith('.smd'):
                if fname not in seen:
                    seen.add(fname)
                    results.append((fname, smd_size, sskf))
        
        pos = idx + len(target)
    
    # 去重，按偏移排序
    results.sort(key=lambda x: x[2])
    return results


def find_texture_entries_in_res(pak_path, item_code):
    """在res PAK中搜索PNG纹理"""
    # 直接搜索PNG魔数附近的文件名
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    target = item_code.encode()
    results = []
    seen = set()
    
    # 搜索PNG文件头(\x89PNG)附近的item_code
    png_pos = 0
    while True:
        png_pos = data.find(b'\x89PNG', png_pos)
        if png_pos < 0:
            break
        
        # 在PNG头前后500字节内搜索item_code
        search_region = data[max(0, png_pos-500):png_pos+500]
        if target in search_region:
            # 找到文件名
            name_start = png_pos
            while name_start > 0 and data[name_start-1:name_start] != b'\x00':
                name_start -= 1
            fname_search = data[max(0, name_start-100):name_start]
            last_null = fname_search.rfind(b'\x00')
            if last_null >= 0:
                try:
                    fname = fname_search[last_null+1:].decode('utf-8', errors='replace')
                except:
                    fname = ''
            else:
                try:
                    fname = fname_search.decode('utf-8', errors='replace')
                except:
                    fname = ''
            
            fname = fname.strip('\x00').strip()
            if fname and item_code in fname and fname.endswith('.png'):
                if fname not in seen:
                    # 估算PNG大小：找到IEND
                    iend = data.find(b'IEND', png_pos)
                    if iend > 0:
                        png_size = iend + 8 - png_pos
                    else:
                        png_size = 500000
                    seen.add(fname)
                    results.append((fname, png_size))
        
        png_pos += 1
    
    return results


def fast_analyze(ic, pak_num, name, note=''):
    """快速分析单个超赛物品"""
    item_pak = os.path.join(GAME, f'item{pak_num}.pak')
    res_pak = os.path.join(GAME, f'res{pak_num}.pak')
    
    print(f'\n{"="*60}')
    print(f'  {ic} - {name} (pak{pak_num}) {note}')
    print(f'{"="*60}')
    
    # 1. BML分析
    if os.path.exists(item_pak):
        ipsize = os.path.getsize(item_pak)
        print(f'  item{pak_num}.pak size: {ipsize/1024:.1f}KB')
        bml_text = find_bml_from_pak(item_pak, ic)
        if bml_text:
            meshes = set(re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', bml_text))
            texs = set(re.findall(r'i5\d{7}[A-Za-z_]*\.png', bml_text))
            chars = re.findall(r'<character type="(\d+)"', bml_text)
            print(f'  [BML] ({len(bml_text)} chars)')
            print(f'    mesh引用({len(meshes)}):')
            for m in sorted(meshes):
                print(f'      - {m}')
            print(f'    texture引用: {texs}')
            print(f'    character types: {chars}')
            # 显示完整character段
            char_sections = re.findall(r'<character[^>]*>.*?</character>', bml_text, re.DOTALL)
            for cs in char_sections:
                ctype = re.search(r'type="(\d+)"', cs)
                ctype = ctype.group(1) if ctype else '?'
                cname = re.search(r'name="([^"]*)"', cs)
                cname = cname.group(1) if cname else '?'
                cmeshes = re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', cs)
                print(f'      char[{ctype}] {cname}: {cmeshes}')
        else:
            print(f'  [BML] 未找到')
    else:
        print(f'  [BML] item{pak_num}.pak 不存在!')
    
    # 2. Res PAK SMD/纹理分析
    if os.path.exists(res_pak):
        rsize = os.path.getsize(res_pak)
        print(f'  res{pak_num}.pak size: {rsize/1024/1024:.1f}MB')
        print(f'  [Res] 搜索SMD和PNG...')
        
        smds = find_smd_entries_in_res(res_pak, ic)
        pngs = find_texture_entries_in_res(res_pak, ic)
        
        print(f'  [Res] SMD ({len(smds)}):')
        for sname, sz, off in smds:
            variant = sname.replace('.smd','').split('_')
            var_suffix = '_'.join(variant[1:]) if len(variant) > 1 else '(base)'
            print(f'    {sname}  ~{sz}B ({sz/1024:.1f}KB)  [{var_suffix}]  @0x{off:X}')
        
        print(f'  [Res] PNG ({len(pngs)}):')
        for pname, sz in pngs:
            print(f'    {pname}  ~{sz}B ({sz/1024:.1f}KB)')
    else:
        print(f'  [Res] res{pak_num}.pak 不存在!')


# ====== 主流程 ======
print('=' * 60)
print('  紫色超赛发型(50125711)原始模型分析')
print('=' * 60)

# 从itemshop获取关键信息
print('\n=== 从itemshop获取超赛系列信息 ===')
with open(DB_PATH, 'r', encoding='utf-8') as f:
    db = json.load(f)

all_ssj = [(k, v) for k, v in db.items() if '超赛' in v.get('name', '')]
print(f'超赛系列共 {len(all_ssj)} 个物品:\n')
for k, v in all_ssj:
    desc = v.get('desc', '?')
    pak = v.get('pak', '?')
    print(f'  [{k}] {v["name"]:16s}  pak{pak:>3s}  "{desc}"')

# 重点对比：极限赛亚人系列
print('\n\n=== 关键线索："染成X色的极限赛亚人发型" ===')
for k, v in all_ssj:
    desc = v.get('desc', '')
    if '染成' in desc and '极限' in desc:
        print(f'  >>> {k} {v["name"]}: "{desc}"')

# 资源分析 - 先分析item PAK（小文件，快）
print('\n\n=== Item PAK: BML配置对比 ===')
candidates = [
    ('50119961', '723', '最强超赛发型', '最早发布的"最强"版本'),
    ('50120651', '727', '极限超赛发型', '可能是紫色/淡粉的原型'),
    ('50124241', '758', '金色超赛发型', '金色版本'),
    ('50125651', '767', '闪耀金超赛发型', '最新金色版本'),
    ('50125711', '768', '紫色超赛发型', '目标物品'),
]

for ic, pak, name, note in candidates:
    item_pak = os.path.join(GAME, f'item{pak}.pak')
    if os.path.exists(item_pak):
        print(f'\n--- {ic} {name} (item{pak}) ---')
        bml_text = find_bml_from_pak(item_pak, ic)
        if bml_text:
            meshes = set(re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', bml_text))
            texs = set(re.findall(r'i5\d{7}[A-Za-z_]*\.png', bml_text))
            chars = re.findall(r'<character type="(\d+)"', bml_text)
            print(f'  mesh: {sorted(meshes)}')
            print(f'  texture: {texs}')
            print(f'  chars: {chars}')
            # 逐个角色
            char_sections = re.findall(r'<character[^>]*>.*?</character>', bml_text, re.DOTALL)
            for cs in char_sections:
                ctype = re.search(r'type="(\d+)"', cs).group(1)
                cmeshes = re.findall(r'i5\d{7}_[A-Za-z_]+\.smd', cs)
                print(f'    [{ctype}] -> {cmeshes}')
        else:
            print(f'  BML未找到')
    else:
        print(f'\n--- {ic} {name} - item{pak}.pak 不存在!')

# Res PAK分析 - 逐个处理（可能较慢）
print('\n\n=== Res PAK: SMD模型文件对比 ===')
for ic, pak, name, note in candidates:
    res_pak = os.path.join(GAME, f'res{pak}.pak')
    if os.path.exists(res_pak):
        print(f'\n--- {ic} {name} (res{pak}, {os.path.getsize(res_pak)/1024/1024:.1f}MB) ---')
        smds = find_smd_entries_in_res(res_pak, ic)
        for sname, sz, off in smds:
            variant = sname.replace('.smd','').split('_')
            var_suffix = '_'.join(variant[1:]) if len(variant) > 1 else '(base)'
            print(f'  {sname} ~{sz}B ({sz/1024:.1f}KB) [{var_suffix}]')
        pngs = find_texture_entries_in_res(res_pak, ic)
        for pname, sz in pngs:
            print(f'  {pname} ~{sz}B ({sz/1024:.1f}KB)')
    else:
        print(f'\n--- {ic} {name} - res{pak}.pak 不存在!')

print('\n\n' + '=' * 60)
print('  分析总结')
print('=' * 60)
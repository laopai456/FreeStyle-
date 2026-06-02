"""final_compare.py — 完整超赛系列对比"""
import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF
DB_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def find_bml(pak_path, item_code):
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
    return dec[rs:re_end + len(b'</root>')].decode('utf-8', errors='replace')

def get_smd_sizes_case_insensitive(pak_path, item_code):
    """通过PGFNPak获取SMD文件大小（不区分大小写）"""
    try:
        rpak = PGFNPak(pak_path)
    except:
        return {}
    
    results = {}
    for e in rpak.entries:
        name_lower = e['name'].lower()
        if item_code.lower() in name_lower and name_lower.endswith('.smd'):
            results[e['name']] = e['data_size']
    return results

# 完整候选列表
candidates = [
    ('50119961', '723', '最强超赛发型', 'cat=697, 首个最强'),
    ('50120651', '727', '极限超赛发型', 'cat=826, 极限赛亚人原型'),
    ('50121981', '739', '淡粉超赛发型', 'cat=1260, 染成淡粉色的极限赛亚人'),
    ('50124241', '758', '金色超赛发型', 'cat=1815, 金色光芒'),
    ('50125651', '767', '闪耀金超赛发型', 'cat=2109, 最新金色'),
    ('50125711', '768', '紫色超赛发型', 'cat=2147, 染成紫色的极限赛亚人'),
]

print('=' * 70)
print('  超赛系列完整对比分析')
print('=' * 70)

# 从itemshop获取描述
with open(DB_PATH, 'r', encoding='utf-8') as f:
    db = json.load(f)

print('\n--- itemshop描述 ---')
for ic, pak, name, note in candidates:
    item = db.get(ic, {})
    print(f'  [{ic}] {name}: "{item.get("desc","?")}"')

# BML结构对比
print('\n\n--- BML结构对比 ---')
for ic, pak, name, note in candidates:
    item_pak = os.path.join(GAME, f'item{pak}.pak')
    if not os.path.exists(item_pak):
        print(f'\n  [{ic}] {name}: item PAK不存在')
        continue
    
    bml = find_bml(item_pak, ic)
    if not bml:
        print(f'\n  [{ic}] {name}: BML未找到')
        continue
    
    chars = re.findall(r'<character type="(\d+)"', bml)
    char_sections = re.findall(r'<character[^>]*>.*?</character>', bml, re.DOTALL)
    
    print(f'\n  [{ic}] {name} ({note})')
    print(f'    角色数: {len(chars)}, types: {chars}')
    for cs in char_sections:
        ct = re.search(r'type="(\d+)"', cs).group(1)
        cm = re.findall(r'i5\d{7}_([A-Za-z]+)\.smd', cs)
        print(f'    char[{ct}]: {cm}')

# SMD大小对比
print('\n\n--- Res PAK: SMD模型文件 ---')
for ic, pak, name, note in candidates:
    res_pak = os.path.join(GAME, f'res{pak}.pak')
    if not os.path.exists(res_pak):
        print(f'\n  [{ic}] {name}: res PAK不存在')
        continue
    
    fsize = os.path.getsize(res_pak)
    print(f'\n  [{ic}] {name} (res{pak}, {fsize/1024/1024:.1f}MB):')
    
    # 直接从PAK数据中搜索SMD文件名（不区分大小写）
    with open(res_pak, 'rb') as f:
        data = f.read()
    
    # 搜索item_code字符串的所有位置
    target_lower = ic.lower().encode()
    pos = 0
    smd_names_found = set()
    while True:
        idx = data.find(target_lower, pos)
        if idx < 0:
            break
        # 检查周围是否为SMD文件名
        ctx_start = max(0, idx - 50)
        ctx_end = min(len(data), idx + 50)
        ctx = data[ctx_start:ctx_end]
        # 提取可能的文件名
        try:
            ctx_str = ctx.decode('ascii', errors='ignore')
        except:
            pos = idx + len(target_lower)
            continue
        # 查找.smd
        for m in re.finditer(r'i' + ic + r'_[a-zA-Z]+\.smd', ctx_str, re.IGNORECASE):
            smd_names_found.add(m.group())
        pos = idx + len(target_lower)
    
    # 用PGFNPak获取精确大小
    smd_sizes = {}
    try:
        rpak = PGFNPak(res_pak)
        for e in rpak.entries:
            ename = e['name'].lower()
            if ic.lower() in ename and ename.endswith('.smd'):
                smd_sizes[e['name'].lower()] = e['data_size']
    except Exception as ex:
        print(f'    PGFNPak解析失败: {ex}')
    
    # 合并结果
    all_names = smd_names_found | set(smd_sizes.keys())
    for sname in sorted(all_names):
        sz = smd_sizes.get(sname.lower(), '?')
        variant = sname.lower().replace('.smd','').split('_')
        var_suffix = '_'.join(variant[1:]) if len(variant) > 1 else '(base)'
        if isinstance(sz, int):
            print(f'    {sname}: {sz}B ({sz/1024:.1f}KB) [{var_suffix}]')
        else:
            print(f'    {sname}: ? [{var_suffix}]')

# 总结
print('\n\n' + '=' * 70)
print('  关键结论')
print('=' * 70)
print("""
1. itemshop描述直接证据:
   - 50125711 紫色超赛: "染成紫色的【极限赛亚人】发型"
   - 50121981 淡粉超赛: "染成淡粉色的【极限赛亚人】发型"
   → 两者明确标注是"极限赛亚人"的换色版本

2. "极限赛亚人" = 50120651 极限超赛发型(pak727, cat=826)
   - 最早发布在cat=826位置
   - 淡粉(cat=1260)和紫色(cat=2147)都在它之后

3. BML结构演变:
   - 最强超赛(50119961, cat=697): 6 meshes, 每角色1个mesh
   - 极限超赛(50120651, cat=826): 6 meshes, 完全相同结构!
   - 淡粉超赛(50121981, cat=1260): 待确认
   - 金色超赛(50124241, cat=1815): 增强为8 meshes (加了MS/FS变体)
   - 紫色超赛(50125711, cat=2147): 8 meshes, 与金色完全相同结构!

4. SMD模型大小:
   所有超赛系列的SMD模型都在 ~264-272KB 范围，高度一致
""")
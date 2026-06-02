"""
extract_and_deploy_v2.py — 提取+修正+部署50125711的独立BML

修正规则：
  - res768.pak中只有 i50125711_fn.smd (270KB)
  - 所有character type都指向 fn.smd
  - 纹理缺失，指向最接近的 i50125701_f.png
"""
import sys, os, shutil

sys.stdout.reconfigure(encoding='utf-8')

XOR_KEY = 0xFF
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
PAK_PATH = os.path.join(GAME_DIR, 'item768.pak')
TARGET_IC = '50125711'
OUT_DIR = os.path.join(GAME_DIR, 'Resource', 'item')
OUT_NAME = f'i{TARGET_IC}.bml'

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def extract_clean_bml(pak_data, item_code):
    decoded = xor_crypt(pak_data)
    search = item_code.encode('ascii')

    idx = decoded.find(search)
    if idx < 0:
        print(f'[!] 未找到 {item_code}')
        return None

    print(f'[*] 找到 {item_code} 在偏移 0x{idx:X}')

    root_start = decoded.rfind(b'<root>', 0, idx)
    if root_start < 0:
        print('[!] 未找到 <root>')
        return None

    root_end = decoded.find(b'</root>', idx)
    if root_end < 0:
        print('[!] 未找到 </root>')
        return None
    root_end += len(b'</root>')

    xml_section = decoded[root_start:root_end]
    text = xml_section.decode('utf-8', errors='replace')

    if '<mesh>' not in text:
        print('[!] 提取的XML不含<mesh>标签')
        return None

    print(f'[*] 原始XML段: {root_start}-{root_end} ({len(xml_section)}B)')
    return xml_section.decode('utf-8')

def main():
    with open(PAK_PATH, 'rb') as f:
        pak_data = f.read()
    print(f'[*] item768.pak: {len(pak_data)}B')

    xml_text = extract_clean_bml(pak_data, TARGET_IC)
    if xml_text is None:
        return

    # 检查res768.pak中实际存在的资源
    sys.path.insert(0, r'd:\py\反编译\FreeStyle')
    from repack_pak import PGFNPak
    res_pak = PGFNPak(r'C:\Program Files (x86)\T2CN\街头篮球\res768.pak')
    existing_files = {e['name'].lower(): e['name'] for e in res_pak.entries}
    print(f'\n[*] res768.pak中存在的50125711相关文件:')
    for name in sorted(existing_files):
        if '501257' in name:
            print(f'    {name}')

    # 修正BML
    # 1. 所有mesh统一指向 i50125711_fn.smd
    # 2. 纹理使用 i50125701_f.png (最近的女性纹理)
    import re

    # 替换所有 mesh 路径
    # 原始: res768\i50125711_XX.smd → res768\i50125711_fn.smd
    new_mesh = 'res768\i50125711_fn.smd'
    count_mesh = xml_text.count('res768\\i50125711_')
    for variant in ['FT', 'FS', 'FSC', 'FN', 'MT', 'MS', 'MN', 'MF']:
        old_path = 'res768\i50125711_' + variant + '.smd'
        xml_text = xml_text.replace(old_path, new_mesh)

    # 替换纹理: i50125711.png → i50125701_f.png (最近的纹理)
    new_tex = 'res768\i50125701_f.png'
    old_tex = 'res768\i50125711.png'
    count_tex = xml_text.count(old_tex)
    xml_text = xml_text.replace(old_tex, new_tex)

    print(f'\n[*] 修正: {count_mesh} 个mesh路径 → {new_mesh}')
    print(f'[*] 修正: {count_tex} 个texture路径 → {new_tex}')

    # 构建完整BML
    full_xml = '<?xml version="1.0"?>\r\n' + xml_text

    print(f'\n=== 修正后的BML ===')
    print(full_xml)

    # XOR编码
    encoded = xor_crypt(full_xml.encode('utf-8'))

    # 备份+部署
    out_path = os.path.join(OUT_DIR, OUT_NAME)
    if os.path.exists(out_path):
        bak = out_path + '.old2'
        shutil.copy2(out_path, bak)
        print(f'\n[*] 已备份: {bak}')

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(encoded)
    print(f'[+] 已部署: {out_path} ({len(encoded)}B)')

    # XML参考
    xml_out = out_path.replace('.bml', '.xml')
    with open(xml_out, 'w', encoding='utf-8') as f:
        f.write(full_xml)
    print(f'[+] XML参考: {xml_out}')

    # 验证
    with open(out_path, 'rb') as f:
        verify = f.read()
    dec_verify = xor_crypt(verify)
    text_v = dec_verify.decode('utf-8')
    errors = []
    if 'i50125711_MT' in text_v:
        errors.append('仍有未替换的 _MT 路径!')
    if new_mesh.encode() not in dec_verify:
        errors.append(f'未找到 {new_mesh}!')

    if errors:
        print(f'\n[!] 验证问题:')
        for e in errors:
            print(f'    {e}')
    else:
        print(f'\n[OK] 验证通过')

    print(f'\n=== 测试步骤 ===')
    print(f'1. sc.exe stop ApolloProtect')
    print(f'2. 启动游戏，登录大厅')
    print(f'3. py hook_diag_group_read.py')
    print(f'4. 进入房间，观察AcquireSMD日志是否出现 res768')


if __name__ == '__main__':
    main()
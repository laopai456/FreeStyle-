"""
extract_and_deploy.py — 从item768.pak提取50125711独立BML并部署到Resource\item\
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

    # 向前找最近的 <root>
    root_start = decoded.rfind(b'<root>', 0, idx)
    if root_start < 0:
        print('[!] 未找到 <root>')
        return None

    # 向后找对应的 </root>
    root_end = decoded.find(b'</root>', idx)
    if root_end < 0:
        print('[!] 未找到 </root>')
        return None
    root_end += len(b'</root>')

    xml_section = decoded[root_start:root_end]

    # 验证有效性
    text = xml_section.decode('utf-8', errors='replace')
    if '<mesh>' not in text:
        print('[!] 提取的XML不含<mesh>标签，可能不完整')
        return None

    print(f'[*] 提取XML段: {root_start}-{root_end} ({len(xml_section)}B)')

    # 构建完整BML XML
    full_xml = b'<?xml version="1.0"?>\r\n' + xml_section

    # 提取mesh/texture信息
    meshes = []
    textures = []
    for line in text.split('\n'):
        line = line.strip()
        if '<mesh>' in line.lower():
            m = line.replace('<mesh>','').replace('</mesh>','').strip()
            meshes.append(m)
        if '<texture>' in line.lower():
            t = line.replace('<texture>','').replace('</texture>','').strip()
            textures.append(t)

    return full_xml, meshes, textures

def main():
    # 1. 读取PAK
    with open(PAK_PATH, 'rb') as f:
        pak_data = f.read()
    print(f'[*] item768.pak: {len(pak_data)}B')

    # 2. 提取干净BML
    result = extract_clean_bml(pak_data, TARGET_IC)
    if result is None:
        return
    full_xml, meshes, textures = result

    # 3. 显示提取结果
    print(f'\n=== 提取的BML ({len(full_xml)}B) ===')
    print(full_xml.decode('utf-8'))
    print(f'\n=== Mesh文件 ({len(meshes)}): ===')
    for m in meshes:
        print(f'  {m}')
    print(f'\n=== 纹理文件 ({len(textures)}): ===')
    for t in set(textures):
        print(f'  {t}')

    # 4. 检查SMD资源是否存在
    print(f'\n=== SMD资源验证 ===')
    res768 = os.path.join(GAME_DIR, 'res768.pak')
    if os.path.exists(res768):
        with open(res768, 'rb') as f:
            res_data = f.read()
        missing = []
        for m in meshes:
            if m.encode('ascii') in res_data:
                print(f'  [OK] {m}')
            else:
                print(f'  [MISSING] {m}')
                missing.append(m)
        if missing:
            print(f'\n[!] {len(missing)} 个SMD文件缺失!')
            return
    else:
        print(f'[!] res768.pak 不存在!')
        return

    # 5. XOR编码
    encoded = xor_crypt(full_xml)

    # 6. 备份旧文件
    out_path = os.path.join(OUT_DIR, OUT_NAME)
    if os.path.exists(out_path):
        bak = out_path + '.old'
        shutil.copy2(out_path, bak)
        print(f'\n[*] 已备份旧文件: {bak}')

    # 7. 写入新BML
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(encoded)
    print(f'[+] 已部署: {out_path} ({len(encoded)}B)')

    # 8. 同时保存一份解码XML供参考
    xml_out = out_path.replace('.bml', '.xml')
    with open(xml_out, 'w', encoding='utf-8') as f:
        f.write(full_xml.decode('utf-8'))
    print(f'[+] XML参考: {xml_out}')

    # 9. 验证部署的文件
    with open(out_path, 'rb') as f:
        verify = f.read()
    dec_verify = xor_crypt(verify)
    if TARGET_IC.encode() in dec_verify:
        print(f'\n[OK] 部署验证通过: 文件包含 {TARGET_IC}')
    else:
        print(f'\n[!] 部署验证失败!')

    print(f'\n=== 下一步 ===')
    print(f'1. sc.exe stop ApolloProtect')
    print(f'2. 启动游戏并进大厅')
    print(f'3. py hook_diag_group_read.py')
    print(f'4. 进入房间，观察是否加载 res768\\i{TARGET_IC}_*.smd')


if __name__ == '__main__':
    main()
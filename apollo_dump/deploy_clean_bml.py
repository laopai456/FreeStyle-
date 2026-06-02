"""
deploy_clean_bml.py — 生成与原始格式完全一致的独立BML并部署
- 不添加XML声明（与原始item768.pak中的BML一致）
- 从原始BML提取结构，修正路径指向res768.pak中实际存在的资源
- 监控脚本monitor_bml_smd.js通过ReadFile hook检测<root>开头
"""
import sys, os, shutil

sys.stdout.reconfigure(encoding='utf-8')

XOR_KEY = 0xFF
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
# 正确部署位置：根据 DFileGPack 查找链，group=item768 → Resource\item768\
OUT_DIR = os.path.join(GAME_DIR, 'Resource', 'item768')
OUT_NAME = 'i50125711.bml'

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def main():
    # 1. 从item768.pak提取原始BML
    with open(os.path.join(GAME_DIR, 'item768.pak'), 'rb') as f:
        pak_data = f.read()
    dec = bytes(b ^ XOR_KEY for b in pak_data)

    idx = dec.find(b'50125711')
    rs = dec.rfind(b'<root>', 0, idx)
    re = dec.find(b'</root>', idx) + len(b'</root>')
    orig_xml = dec[rs:re].decode('utf-8')

    print(f'原始BML: {rs}-{re} ({re-rs}B)')
    print(f'原始BML以<root>开头: {orig_xml.lstrip().startswith("<root>")}')

    # 2. 路径替换：保持原始路径（资源已完整部署到 Resource\res768\）
    # 不再替换，直接使用原始 BML 引用
    # 所有 SMD 和 PNG 已通过 deploy_resources.py 部署
    text = orig_xml

    print(f'\n=== 原始BML保持不变 (资源已完整部署) ===')
    print(text)

    assert text.lstrip().startswith('<root>'), 'BML不以<root>开头！'
    assert '50125711' in text, 'BML不含50125711！'
    assert 'FN.smd' in text or 'fn.smd' in text, 'BML不含FN.smd！'

    # 3. XOR编码（无XML声明，与原始格式完全一致）
    encoded = xor_crypt(text.encode('utf-8'))

    # 4. 备份 + 部署
    out_path = os.path.join(OUT_DIR, OUT_NAME)
    if os.path.exists(out_path):
        bak = out_path + '.bak'
        shutil.copy2(out_path, bak)
        print(f'\n[*] 已备份: {bak}')

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(encoded)
    print(f'[+] 已部署: {out_path} ({len(encoded)}B)')

    # 5. 验证：XOR解码后以<root>开头
    with open(out_path, 'rb') as f:
        verify = f.read()
    dec_verify = bytes(b ^ XOR_KEY for b in verify)
    vt = dec_verify.decode('utf-8')
    print(f'[+] 验证: 以<root>开头={vt.lstrip().startswith("<root>")}')
    print(f'[+] 验证: 含fn.smd={"fn.smd" in vt}')

    # 6. 也保存解码参考
    xml_out = out_path.replace('.bml', '.xml')
    with open(xml_out, 'w', encoding='utf-8') as f:
        f.write(vt)
    print(f'[+] XML参考: {xml_out}')

    print(f'\n=== 测试步骤 ===')
    print(f'1. sc.exe stop ApolloProtect')
    print(f'2. 启动游戏登录大厅')
    print(f'3. py monitor_bml_smd.py 50125711    ← 用这个！可以监控ReadFile')
    print(f'4. 进入房间触发角色加载')
    print(f'5. 查看输出: 如果出现 [BML] 50125711 → BML被成功读取')
    print(f'   如果不出现 → BML没有被读取,需要进一步诊断')

if __name__ == '__main__':
    main()
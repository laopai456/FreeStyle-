"""verify_deployed_bml.py — 验证部署的BML并诊断问题"""
import sys, os, struct
sys.stdout.reconfigure(encoding='utf-8')

XOR_KEY = 0xFF
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
BML_PATH = os.path.join(GAME_DIR, 'Resource', 'item', 'i50125711.bml')

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

# 1. 检查文件是否存在
print('=== 1. 文件存在性 ===')
print(f'路径: {BML_PATH}')
if os.path.exists(BML_PATH):
    print(f'[OK] 文件存在 ({os.path.getsize(BML_PATH)}B)')
    mtime = os.path.getmtime(BML_PATH)
    import datetime
    print(f'修改时间: {datetime.datetime.fromtimestamp(mtime)}')
else:
    print('[!!!] 文件不存在!')
    sys.exit(1)

# 2. 读取并验证
with open(BML_PATH, 'rb') as f:
    data = f.read()

# XOR解码
decoded = bytes(b ^ XOR_KEY for b in data)
text = decoded.decode('utf-8', errors='replace')

print(f'\n=== 2. 内容验证 ===')
print(f'编码大小: {len(data)}B')
print(f'解码大小: {len(decoded)}B')

# 检查XML有效性
checks = [
    ('以<?xml开头', text.startswith('<?xml')),
    ('包含<root>', '<root>' in text),
    ('包含</root>', '</root>' in text),
    ('包含50125711', '50125711' in text),
    ('包含fn.smd', 'fn.smd' in text or 'FN.smd' in text),
    ('包含<mesh>', '<mesh>' in text),
    ('包含<channel>', '<channel>' in text),
]
for label, result in checks:
    print(f'  [{("OK" if result else "FAIL")}] {label}')

# 显示完整XML
print(f'\n=== 3. 完整XML ===')
print(text)

# 4. 检查驼峰vs大小写
print(f'\n=== 4. 大小写检查 ===')
for variant in ['i50125711_FN.smd', 'i50125711_fn.smd', 'i50125711_FT.smd', 'i50125711_MT.smd']:
    found = variant in text
    print(f'  [{("OK" if found else "NO")}] {variant}')

# 5. 检查资源目录结构
print(f'\n=== 5. 游戏目录结构 ===')
dirs_to_check = [
    (os.path.join(GAME_DIR, 'Resource', 'item'), 'Resource\\item\\'),
    (os.path.join(GAME_DIR, 'customize', 'item'), 'customize\\item\\'),
    (os.path.join(GAME_DIR, 'Resource'), 'Resource\\'),
]
for d, label in dirs_to_check:
    if os.path.exists(d):
        bmls = [f for f in os.listdir(d) if f.lower().endswith('.bml')]
        xmls = [f for f in os.listdir(d) if f.lower().endswith('.xml')]
        print(f'  [OK] {label} 存在 ({len(bmls)} BML + {len(xmls)} XML)')
        for f in bmls:
            if '50125' in f:
                print(f'    → {f}')
        for f in xmls:
            if '50125' in f:
                print(f'    → {f}')
    else:
        print(f'  [---] {label} 不存在')

# 6. 模拟游戏LoadBinaryXML
print(f'\n=== 6. 模拟游戏XOR解码 ===')
# 游戏读取整个文件，然后每个字节 XOR 0xFF
sim_decoded = bytes(b ^ 0xFF for b in data)  # 应该等于decoded
sim_text = sim_decoded.decode('utf-8', errors='replace')

# 游戏解析XML
# LoadBinaryXML -> LibXMLParse -> process node tree
# 如果XML格式有问题，解析会失败
# 模拟检查：
if sim_text.lstrip().startswith('<?xml'):
    print('  [OK] 以<?xml开头')
elif sim_text.lstrip().startswith('<root>'):
    print('  [OK] 以<root>开头 (无XML声明，但可能仍有效)')
else:
    print(f'  [WARN] 开头不是XML: {sim_text[:50]}')

# 7. 对比原始item768.pak中的原始BML
print(f'\n=== 7. 原始BML vs 部署BML对比 ===')
with open(os.path.join(GAME_DIR, 'item768.pak'), 'rb') as f:
    pak_data = f.read()
pak_dec = bytes(b ^ 0xFF for b in pak_data)

# 找到i50125711的<root>段
idx = pak_dec.find(b'50125711')
if idx >= 0:
    rs = pak_dec.rfind(b'<root>', 0, idx)
    re = pak_dec.find(b'</root>', idx) + len(b'</root>')
    orig = pak_dec[rs:re]
    orig_text = orig.decode('utf-8', errors='replace')
    print(f'原始BML ({len(orig)}B)')
    
    # 比较mesh引用
    import re as re_mod
    orig_meshes = re_mod.findall(r'i50125711_[A-Z.]+\.smd', orig_text)
    new_meshes = re_mod.findall(r'i50125711_[A-Za-z.]+\.smd', text)
    print(f'  原始mesh: {set(orig_meshes)}')
    print(f'  部署mesh: {set(new_meshes)}')
    
    orig_tex = re_mod.findall(r'i50125\d+[A-Za-z_]*\.png', orig_text)
    new_tex = re_mod.findall(r'i50125\d+[A-Za-z_]*\.png', text)
    print(f'  原始texture: {set(orig_tex)}')
    print(f'  部署texture: {set(new_tex)}')
"""check_orig_bml.py — 精确提取原始BML并显示完整内容"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

XOR_KEY = 0xFF

with open(r'C:\Program Files (x86)\T2CN\街头篮球\item768.pak', 'rb') as f:
    pak_data = f.read()

dec = bytes(b ^ XOR_KEY for b in pak_data)

# i50125711的<root>从0xE86开始（XOR解码后）
rs = dec.rfind(b'<root>', 0, dec.find(b'50125711'))
re = dec.find(b'</root>', dec.find(b'50125711')) + len(b'</root>')

print(f'i50125711 <root>段: 0x{rs:X}-0x{re:X} ({re-rs}B)')
print()

orig = dec[rs:re]
orig_text = orig.decode('utf-8', errors='replace')

print('=== 原始BML (精确提取) ===')
for i, line in enumerate(orig_text.split('\n')):
    print(f'{i:3d}: {line}')

print()
print('=== 结构分析 ===')
# 统计每个<character>里的<object>数量
import re
chars = re.findall(r'<character type="\d+">(.*?)</character>', orig_text, re.DOTALL)
for i, c in enumerate(chars):
    objs = re.findall(r'<object[^>]*>', c)
    types = re.findall(r'<type>([^<]+)</type>', c)
    meshes = re.findall(r'<mesh>([^<]+)</mesh>', c)
    print(f'  Character #{i}: {len(objs)} objects, types={types}, meshes={meshes}')

# 检查是否有嵌套问题
print()
print('=== 检查: <object type="2"> 是否在错误位置 ===')
for i, line in enumerate(orig_text.split('\n')):
    if 'object type=' in line or 'character type=' in line:
        print(f'  L{i}: {line.strip()}')
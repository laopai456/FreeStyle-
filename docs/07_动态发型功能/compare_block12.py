from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取文件
files = {}
for code, name in {
    '50125031': '破坏者超赛发型',
    '50124971': '霓虹超赛发型',
    '50124941': '鬼魅白发',
    '50124921': '隐力者发型',
    '50125001': '可爱加倍发型',
    '50124961': '复古怀旧发型',
    '50124981': '冷酷老板发型',
    '50124951': '全息爱心发型',
    '50124931': '黑与白针织帽'
}.items():
    bml_file = pak_dir / f'i{code}.bml'
    with open(bml_file, 'rb') as f:
        files[code] = f.read()

print('=== 所有动态发型第12块完整数据 (offset 318-392, 74 bytes) ===\n')

dynamic = ['50125031', '50124971', '50124941', '50124921']

for code in dynamic:
    block = files[code][318:392]
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'{code}:')
    print(f'  {hex_str}')
    print()

print('\n=== 静态发型第12块完整数据 (offset 320-380, 60 bytes) ===\n')

static = ['50125001', '50124961', '50124981', '50124951', '50124931']

for code in static:
    block = files[code][320:380]
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'{code}:')
    print(f'  {hex_str}')
    print()

print('\n=== 对比：动态与静态第12块头部 (前32字节) ===\n')

print('动态发型:')
for code in dynamic:
    block = files[code][318:350]
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'  {code}: {hex_str}')

print('\n静态发型:')
for code in static:
    block = files[code][320:352]
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'  {code}: {hex_str}')

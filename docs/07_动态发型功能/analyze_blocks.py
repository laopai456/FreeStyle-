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

print('=== 第12块详细分析 (offset 318-392 for dynamic) ===')
print('这是差异最大的块 (+14字节)\n')

# 动态发型第12块
for code in ['50125031', '50124971', '50124941', '50124921']:
    data = files[code]
    block = data[318:392]  # 第12块
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'{code} (动态): {len(block)} bytes')
    print(f'  {hex_str[:100]}...')
    print()

print('--- 静态发型第12块 (offset 320-380) ---')
for code in ['50125001', '50124961', '50124981', '50124951', '50124931']:
    data = files[code]
    block = data[320:380]  # 第12块
    hex_str = ' '.join(f'{b:02X}' for b in block)
    print(f'{code} (静态): {len(block)} bytes')
    print(f'  {hex_str[:100]}...')
    print()

print('\n=== 对比分析 ===')
dyn_block = files['50125031'][318:392]
stat_block = files['50125001'][320:380]

print('动态块额外字节（静态没有）:')
extra_bytes = []
for i in range(len(dyn_block)):
    if i >= len(stat_block) or dyn_block[i] != stat_block[i]:
        extra_bytes.append(f'{dyn_block[i]:02X}')

print(f'  {" ".join(extra_bytes[:50])}...')
print(f'  共 {len(extra_bytes)} 字节差异')

# 查找连续的数值模式（可能是参数）
print('\n=== 查找数值模式（可能的物理参数）===')
# 查找00-0F之间的低值字节（可能是索引）
low_values = []
for i in range(len(dyn_block)):
    if 0 <= dyn_block[i] < 16:
        low_values.append((318+i, dyn_block[i]))

print('动态发型第12块中的低值字节（可能的索引）:')
for offset, value in low_values[:20]:
    print(f'  offset {offset}: 0x{value:02X} ({value})')

# 查找连续的4字节对齐数据
print('\n=== 4字节对齐数据分析 ===')
for i in range(0, len(dyn_block), 4):
    chunk = dyn_block[i:i+4]
    if len(chunk) == 4:
        # 转为float查看
        import struct
        try:
            float_val = struct.unpack('f', bytes(chunk))[0]
            # 只显示合理的数值（排除NaN和极端值）
            if abs(float_val) < 1000 and float_val != 0:
                print(f'  offset {318+i}: {" ".join(f"{b:02X}" for b in chunk)} -> float={float_val:.4f}')
        except:
            pass

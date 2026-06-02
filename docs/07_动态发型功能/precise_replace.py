from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取文件
dyn = open(pak_dir / 'i50125031.bml', 'rb').read()  # 破坏者超赛发型 (动态)
stat = open(pak_dir / 'i50125001.bml', 'rb').read()  # 可爱加倍发型 (静态)

print('=== 完整第12块对比 ===\n')

# 动态第12块: offset 318-392 (74 bytes)
dyn_block = dyn[318:392]
# 静态第12块: offset 320-380 (60 bytes)
stat_block = stat[320:380]

print(f'动态第12块 ({len(dyn_block)} bytes):')
print(f'  {" ".join(f"{b:02X}" for b in dyn_block)}')

print(f'\n静态第12块 ({len(stat_block)} bytes):')
print(f'  {" ".join(f"{b:02X}" for b in stat_block)}')

print('\n=== 差异分析 ===\n')

# 找出差异位置
min_len = min(len(dyn_block), len(stat_block))
diff_positions = []

for i in range(min_len):
    if dyn_block[i] != stat_block[i]:
        diff_positions.append(i)

print(f'前{min_len}字节中差异位置: {len(diff_positions)}个')
print(f'差异位置: {diff_positions[:20]}...' if len(diff_positions) > 20 else f'差异位置: {diff_positions}')

print('\n=== 关键发现 ===\n')

# 对比前26字节
prefix_match = dyn_block[:26] == stat_block[:26]
print(f'前26字节是否一致: {prefix_match}')

if prefix_match:
    print(f'\n前26字节: {" ".join(f"{b:02X}" for b in dyn_block[:26])}')

# 显示offset 26之后的内容
print(f'\n动态 offset 26-30: {" ".join(f"{b:02X}" for b in dyn_block[26:31])}')
print(f'静态 offset 26-30: {" ".join(f"{b:02X}" for b in stat_block[26:31])}')

print('\n=== 测试方案 ===\n')
print('方案1: 完整替换第12块')
print('  - 优点: 保留完整动态参数')
print('  - 风险: 需要调整后续所有数据块位置')
print('')
print('方案2: 只替换offset 26之后的差异部分')
print('  - 优点: 最小化修改')
print('  - 风险: 可能不完整')
print('')
print('方案3: 分析F2F5结构后精确插入')
print('  - 优点: 保持文件结构')
print('  - 风险: 复杂度高')

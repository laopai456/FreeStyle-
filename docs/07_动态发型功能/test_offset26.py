from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取文件
dyn = open(pak_dir / 'i50125031.bml', 'rb').read()  # 破坏者超赛发型 (动态)
stat = open(pak_dir / 'i50125001.bml', 'rb').read()  # 可爱加倍发型 (静态)

print('=== 测试：替换第12块 offset 26之后的部分 ===\n')

# 动态第12块 offset 26之后的数据 (74-26=48 bytes)
dyn_suffix = dyn[318+26:392]
# 静态第12块 offset 26之后的数据 (60-26=34 bytes)
stat_suffix = stat[320+26:380]

print(f'动态第12块后48字节: {len(dyn_suffix)} bytes')
print(f'  {" ".join(f"{b:02X}" for b in dyn_suffix)}\n')

print(f'静态第12块后34字节: {len(stat_suffix)} bytes')
print(f'  {" ".join(f"{b:02X}" for b in stat_suffix)}\n')

# 构建新文件
new_data = bytearray(stat)

# 在静态发型第12块的offset 26位置 (320+26=346) 替换为动态版本
new_data[346:380] = dyn_suffix

print(f'原文件: {len(stat)} bytes')
print(f'新文件: {len(new_data)} bytes')
print(f'增加: {len(new_data) - len(stat)} bytes')

# 保存测试文件
test_file = pak_dir / 'i50125001_test_offset26.bml'
with open(test_file, 'wb') as f:
    f.write(bytes(new_data))

print(f'\n测试文件已保存: {test_file}')
print('\n=== 测试说明 ===')
print('这个测试将动态发型第12块offset 26之后的所有数据（48字节）')
print('替换到静态发型第12块的对应位置（原34字节）。')
print('这样静态发型第12块将从60字节变成74字节，与动态发型一致。')
print('\n由于文件变长了14字节，后续所有数据块位置都会偏移。')
print('测试时需要注意 pak 包是否支持动态调整大小。')

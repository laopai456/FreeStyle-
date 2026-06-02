from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取动态发型和静态发型
dyn_data = open(pak_dir / 'i50125031.bml', 'rb').read()  # 破坏者超赛发型 (动态)
stat_data = open(pak_dir / 'i50125001.bml', 'rb').read()  # 可爱加倍发型 (静态)

print('=== 原始文件信息 ===')
print(f'动态发型 (50125031): {len(dyn_data)} bytes')
print(f'静态发型 (50125001): {len(stat_data)} bytes')

# 提取动态发型的第12块 (offset 318-392)
dyn_block12 = dyn_data[318:392]
print(f'\n动态发型第12块: {len(dyn_block12)} bytes')
print(f'  F2F5数量: {[i for i in range(len(dyn_block12)-1) if dyn_block12[i:i+2] == b"\\xF2\\xF5"]}')

# 替换静态发型的第12块 (offset 320-380) -> 替换为动态的块
# 注意：由于动态块比静态块大14字节，需要调整后续所有数据
new_stat_data = bytearray(stat_data)
new_stat_data[320:380] = dyn_block12  # 替换为74字节，原位置只有60字节

# 现在文件变长了14字节
print(f'\n=== 替换后 ===')
print(f'新文件大小: {len(new_stat_data)} bytes')
print(f'原文件大小: {len(stat_data)} bytes')
print(f'增加: {len(new_stat_data) - len(stat_data)} bytes')

# 保存测试文件
test_file = pak_dir / 'i50125001_test_block12.bml'
with open(test_file, 'wb') as f:
    f.write(bytes(new_stat_data))

print(f'\n测试文件已保存: {test_file}')
print('\n=== 问题说明 ===')
print('由于只替换了第12块，后续所有数据块的F2F5标记位置都会偏移。')
print('这可能导致文件结构错误，需要同步调整后续标记位置。')
print('\n正确的替换方案：')
print('1. 替换第12块为动态版本 (74字节)')
print('2. 调整后续所有F2F5标记位置 (+14)')
print('3. 或者：重新计算整个文件的F2F5标记')

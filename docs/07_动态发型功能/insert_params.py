from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取动态发型和静态发型
dyn_data = open(pak_dir / 'i50125031.bml', 'rb').read()
stat_data = open(pak_dir / 'i50125001.bml', 'rb').read()

print('=== 方案：插入额外参数段 ===\n')

# 动态发型第12块 (offset 318-392)
dyn_block12 = dyn_data[318:392]

# 找到动态发型第12块中的3个F2F5标记
f5_positions = []
for i in range(len(dyn_block12)):
    if dyn_block12[i:i+2] == b'\xF2\xF5':
        f5_positions.append(i)

print(f'动态发型第12块 F2F5位置 (相对): {f5_positions}')
print(f'F2F5数量: {len(f5_positions)}\n')

# 提取每个参数段的内容
params_segments = []
for i, pos in enumerate(f5_positions):
    if i < len(f5_positions) - 1:
        end = f5_positions[i + 1]
    else:
        end = len(dyn_block12)

    segment = dyn_block12[pos:end]
    params_segments.append(segment)
    print(f'参数段{i+1} (offset {318+pos}): {len(segment)} bytes')
    print(f'  {" ".join(f"{b:02X}" for b in segment)}')
    print()

# 静态发型第12块
stat_block12 = stat_data[320:380]
stat_f5_positions = [i for i in range(len(stat_block12)) if stat_block12[i:i+2] == b'\xF2\xF5']

print(f'静态发型第12块 F2F5位置 (相对): {stat_f5_positions}')
print(f'F2F5数量: {len(stat_f5_positions)}\n')

# 分析：静态发型第12块只有1个F2F5，在相对位置49
# 动态发型第12块有3个F2F5，在相对位置47, 58, 72
# 动态发型多了2个参数段

# 构建新文件：在静态发型的第12块末尾插入额外的2个F2F5参数段
print('=== 构建修改方案 ===\n')

# 找到静态发型第12块的结束位置（在offset 380处）
# 我们需要在第1个F2F5之后插入2个额外的参数段

# 方案：找到静态发型第12块中唯一的F2F5位置，在其后插入
if stat_f5_positions:
    insert_pos = 320 + stat_f5_positions[0] + 2  # F2F5之后

    # 提取动态发型的额外2个参数段
    extra_params1 = dyn_block12[f5_positions[1]:f5_positions[2]]  # 第2个参数段
    extra_params2 = dyn_block12[f5_positions[2]:f5_positions[3] if len(f5_positions) > 3 else len(dyn_block12)]  # 第3个参数段

    # 修正：实际需要的是完整参数段（包括F2F5标记）
    extra_segment1 = dyn_block12[f5_positions[1]:f5_positions[2]]  # 从第2个F2F5到第3个F2F5
    extra_segment2 = dyn_block12[f5_positions[2]:]  # 从第3个F2F5到结束

    print(f'插入位置: offset {insert_pos}')
    print(f'额外段1 ({len(extra_segment1)} bytes): {" ".join(f"{b:02X}" for b in extra_segment1)}')
    print(f'额外段2 ({len(extra_segment2)} bytes): {" ".join(f"{b:02X}" for b in extra_segment2)}')
    print()

    # 构建新数据
    new_data = bytearray(stat_data)

    # 插入额外段2（先插入后面的，避免位置偏移）
    new_data[insert_pos:insert_pos] = extra_segment2

    # 插入额外段1
    new_data[insert_pos:insert_pos] = extra_segment1

    print(f'原文件大小: {len(stat_data)} bytes')
    print(f'新文件大小: {len(new_data)} bytes')
    print(f'增加: {len(new_data) - len(stat_data)} bytes')

    # 保存测试文件
    test_file = pak_dir / 'i50125001_test_insert.bml'
    with open(test_file, 'wb') as f:
        f.write(bytes(new_data))

    print(f'\n测试文件已保存: {test_file}')
    print('\n=== 说明 ===')
    print('这个方案在静态发型第12块的F2F5标记后插入了2个额外的参数段。')
    print('这样可以保持原有数据结构，只在末尾添加动态参数。')
else:
    print('错误：静态发型第12块中没有找到F2F5标记')

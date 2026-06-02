from pathlib import Path
import struct

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取动态发型
dyn_block = open(pak_dir / 'i50125031.bml', 'rb').read()[318:392]
stat_block = open(pak_dir / 'i50125001.bml', 'rb').read()[320:380]

print('=== 动态发型第12块参数分析 ===\n')
print(f'完整数据 (74 bytes):')
print(' '.join(f'{b:02X}' for b in dyn_block))
print()

# 提取 F2 F5 之间的数据块
print('=== F2 F5 标记识别 ===')
f5_positions = []
for i in range(len(dyn_block) - 1):
    if dyn_block[i] == 0xF2 and dyn_block[i+1] == 0xF5:
        f5_positions.append(i)
print(f'F2 F5 位置: {f5_positions}')
print()

# 分析每个参数段
print('=== 参数段分析 ===')
for i, pos in enumerate(f5_positions):
    start = pos + 2  # F2 F5 之后
    if i < len(f5_positions) - 1:
        end = f5_positions[i + 1]
    else:
        end = len(dyn_block)

    params = dyn_block[start:end]
    print(f'参数段 {i+1} (offset {318+start}): {len(params)} bytes')
    print(f'  Hex: {" ".join(f"{b:02X}" for b in params)}')

    # 尝试解析为 float
    for j in range(0, len(params), 4):
        if j + 4 <= len(params):
            chunk = params[j:j+4]
            try:
                val = struct.unpack('f', bytes(chunk))[0]
                if abs(val) < 100 and val != 0:
                    print(f'    [{j:2d}] {chunk.hex():8s} = {val:.6f}')
            except:
                pass
    print()

# 对比静态发型
print('=== 静态发型第12块 F2 F5 位置 ===')
f5_positions_stat = []
for i in range(len(stat_block) - 1):
    if stat_block[i] == 0xF2 and stat_block[i+1] == 0xF5:
        f5_positions_stat.append(i)
print(f'F2 F5 位置: {f5_positions_stat}')
print()

# 查找重复模式
print('=== 动态发型中的重复模式 ===')
# 查找 "F2 F5 C3 D0" 后跟8字节的模式
pattern_count = 0
for i in range(len(dyn_block) - 11):
    if dyn_block[i:i+4] == bytes([0xF2, 0xF5, 0xC3, 0xD0]):
        next_8 = dyn_block[i+4:i+12]
        pattern_count += 1
        print(f'模式 {pattern_count} at offset {318+i}:')
        print(f'  标记: F2 F5 C3 D0')
        print(f'  参数: {" ".join(f"{b:02X}" for b in next_8)}')

# 解析参数为可能的数据类型
print('\n  参数解读:')
for j in range(0, 8, 4):
    chunk = next_8[j:j+4]
    try:
        fval = struct.unpack('f', chunk)[0]
        print(f'    [{j:2d}] {chunk.hex():8s} = float {fval:.6f}')
    except:
        pass
    try:
        ival = struct.unpack('i', chunk)[0]
        print(f'    [{j:2d}] {chunk.hex():8s} = int {ival}')
    except:
        pass
print()

# 总结差异
print('=== 差异总结 ===')
print(f'动态发型 F2F5 次数: {len(f5_positions)}')
print(f'静态发型 F2F5 次数: {len(f5_positions_stat)}')
print(f'动态发型第12块: {len(dyn_block)} bytes')
print(f'静态发型第12块: {len(stat_block)} bytes')
print(f'差异: {len(dyn_block) - len(stat_block)} bytes')

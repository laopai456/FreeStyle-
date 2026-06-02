import os
from pathlib import Path

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取所有BML文件
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
    if bml_file.exists():
        with open(bml_file, 'rb') as f:
            files[code] = f.read()

print('=== 动态与静态对比分析 ===\n')

# 对比前500字节的差异
dynamic_codes = ['50125031', '50124971', '50124941', '50124921']
static_codes = ['50125001', '50124961', '50124981', '50124951', '50124931']

# 取第一个动态和第一个静态作为对比样本
dyn_data = files['50125031']
stat_data = files['50125001']

print(f'动态样本: 50125031 ({len(dyn_data)} bytes)')
print(f'静态样本: 50125001 ({len(stat_data)} bytes)\n')

# 查找F2F5DF标记
print('=== F2F5DF标记位置 ===')
def find_markers(data):
    return [i for i in range(len(data) - 2) if data[i] == 0xF2 and data[i+1] == 0xF5 and data[i+2] == 0xDF]

dyn_markers = find_markers(dyn_data)
stat_markers = find_markers(stat_data)

print(f'动态: {dyn_markers}')
print(f'静态: {stat_markers}\n')

# 按标记分段分析
print('=== 数据块分析 ===')
def analyze_blocks(data, markers):
    blocks = []
    prev = 0
    for marker in markers:
        block = data[prev:marker]
        blocks.append({
            'start': prev,
            'end': marker,
            'size': marker - prev,
            'data': block
        })
        prev = marker + 3  # 跳过F2F5DF
    # 最后一个块
    blocks.append({
        'start': prev,
        'end': len(data),
        'size': len(data) - prev,
        'data': data[prev:]
    })
    return blocks

dyn_blocks = analyze_blocks(dyn_data, dyn_markers)
stat_blocks = analyze_blocks(stat_data, stat_markers)

print(f'动态块数: {len(dyn_blocks)}')
print(f'静态块数: {len(stat_blocks)}\n')

# 对比每个块
max_blocks = max(len(dyn_blocks), len(stat_blocks))
for i in range(max_blocks):
    if i < len(dyn_blocks) and i < len(stat_blocks):
        dyn_block = dyn_blocks[i]
        stat_block = stat_blocks[i]

        if dyn_block['data'] != stat_block['data']:
            print(f'--- 第{i+1}块差异 ---')
            print(f'动态: offset {dyn_block["start"]}-{dyn_block["end"]}, size {dyn_block["size"]}')
            print(f'静态: offset {stat_block["start"]}-{stat_block["end"]}, size {stat_block["size"]}')
            print(f'大小差: {dyn_block["size"] - stat_block["size"]}')

            # 显示前32字节
            hex_dyn = ' '.join(f'{b:02X}' for b in dyn_block['data'][:32])
            hex_stat = ' '.join(f'{b:02X}' for b in stat_block['data'][:32])
            print(f'动态头部: {hex_dyn}')
            print(f'静态头部: {hex_stat}')
            print()

# 找出所有动态文件共有的特征
print('=== 动态发型共同特征 ===')
# 对比所有动态文件的前200字节
for i in range(200):
    values = {code: files[code][i] for code in dynamic_codes}
    if len(set(values.values())) == 1:
        continue  # 所有动态文件在此字节一致

    # 检查是否与静态文件有区别
    static_values = {code: files[code][i] for code in static_codes}
    if len(set(values.values())) != len(set(static_values.values())):
        print(f'Offset {i}: 动态={set(values.values())}, 静态={set(static_values.values())}')

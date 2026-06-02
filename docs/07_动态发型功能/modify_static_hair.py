from pathlib import Path
import shutil

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

# 读取文件
dyn = open(pak_dir / 'i50125031.bml', 'rb').read()  # 破坏者超赛发型 (动态)
stat = open(pak_dir / 'i50125001.bml', 'rb').read()  # 可爱加倍发型 (静态)

print('=== 静态发型动态化修改方案 ===\n')
print('目标：将 i50125001.bml (可爱加倍发型) 修改为动态发型\n')

# 备份原文件
backup_file = pak_dir / 'i50125001.bml.backup'
shutil.copy(pak_dir / 'i50125001.bml', backup_file)
print(f'已备份原文件到: {backup_file.name}')

# 动态第12块 offset 26之后的数据 (48 bytes)
dyn_suffix = dyn[318+26:392]
# 静态第12块 offset 26之后的数据 (34 bytes)
stat_suffix = stat[320+26:380]

print(f'\n动态发型第12块后48字节: {len(dyn_suffix)} bytes')
print(f'静态发型第12块后34字节: {len(stat_suffix)} bytes')

# 修改静态文件
new_stat_data = bytearray(stat)

# 在静态发型第12块的offset 26位置 (320+26=346) 替换为动态版本
new_stat_data[346:380] = dyn_suffix

print(f'\n原文件: {len(stat)} bytes')
print(f'新文件: {len(new_stat_data)} bytes')
print(f'增加: {len(new_stat_data) - len(stat)} bytes')

# 直接覆盖原文件
with open(pak_dir / 'i50125001.bml', 'wb') as f:
    f.write(bytes(new_stat_data))

print(f'\n已直接修改: i50125001.bml')
print('\n=== 修改说明 ===')
print('1. 已备份原文件为 i50125001.bml.backup')
print('2. 已修改 i50125001.bml，第12块从60字节变为74字节')
print('3. 文件名保持不变，游戏会按照原名称索引')
print('\n=== 下一步操作 ===')
print('1. 将 item764_pak 文件夹下的所有文件重新压包到 item764.pak')
print('2. 将修改后的 item764.pak 放到游戏目录的 cookies 文件夹')
print('3. 在游戏中查看"可爱加倍发型"是否变成动态效果')
print('\n如果需要恢复原文件:')
print('copy i50125001.bml.backup i50125001.bml')

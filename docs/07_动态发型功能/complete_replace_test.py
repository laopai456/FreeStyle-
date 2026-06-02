from pathlib import Path
import shutil

pak_dir = Path(r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak')

print('=== 完整替换测试 ===\n')

# 读取动态发型和静态发型
dyn = open(pak_dir / 'i50125031.bml', 'rb').read()  # 破坏者超赛发型 (动态)
stat = open(pak_dir / 'i50125001.bml', 'rb').read()  # 可爱加倍发型 (静态)

print(f'动态发型 (50125031): {len(dyn)} bytes')
print(f'静态发型 (50125001): {len(stat)} bytes')
print()

# 备份原文件
backup_file = pak_dir / 'i50125001.bml.backup2'
if not backup_file.exists():
    shutil.copy(pak_dir / 'i50125001.bml', backup_file)
    print(f'已备份: {backup_file.name}')

# 测试1: 完整替换为动态发型（不保留文件大小）
print('\n测试1: 完整替换为动态发型')
with open(pak_dir / 'i50125001.bml', 'wb') as f:
    f.write(dyn)

print(f'  i50125001.bml 已替换为动态发型内容')
print(f'  新大小: {len(dyn)} bytes (原 {len(stat)} bytes)')
print(f'  变化: {len(dyn) - len(stat)} bytes')

print('\n=== 说明 ===')
print('这个测试将整个i50125001.bml文件替换为动态发型i50125031.bml的内容。')
print('如果这样能显示动态效果，说明需要完整的文件结构。')
print('如果仍然不行，说明问题不在文件内容本身。')

print('\n=== 恢复命令 ===')
print(f'测试后如需恢复，运行:')
print(f'copy {backup_file} {pak_dir / "i50125001.bml"}')

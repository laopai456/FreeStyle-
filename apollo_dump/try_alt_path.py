"""try_alt_path.py — 尝试其他BML放置位置"""
import os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'

print('=== 检查可能的目标目录 ===')
check_dirs = [
    'customize', 'customize\\item',
    'Resource\\customize', 'Resource\\customize\\item',
    'item',
    'resource', 'resource\\item',
]
for d in check_dirs:
    full = os.path.join(GAME, d)
    if os.path.exists(full):
        print(f'  [OK] {d}')
    else:
        print(f'  [---] {d}')

# 检查game.ini或相关配置文件
print('\n=== 检查配置文件 ===')
for cfg in ['game.ini', 'config.ini', 'config.inc', 'fname.inc', 'fname.txt']:
    full = os.path.join(GAME, cfg)
    if os.path.exists(full):
        print(f'  [OK] {cfg}')

# 复制BML到多个可能位置
src = os.path.join(GAME, 'Resource', 'item', 'i50125711.bml')
if not os.path.exists(src):
    print(f'\n[ERROR] 源文件不存在: {src}')
    sys.exit(1)

dst_dirs = []
for d in ['item', 'Resource', 'customize', 'customize\\item', 'resource', 'resource\\item']:
    full = os.path.join(GAME, d)
    os.makedirs(full, exist_ok=True)
    dst = os.path.join(full, 'i50125711.bml')
    shutil.copy2(src, dst)
    dst_dirs.append(d)
    print(f'\n[+] 已复制到 {d}\\i50125711.bml')

print(f'\n=== 部署完成 ===')
print(f'已在 {len(dst_dirs)} 个目录放置BML:')
for d in dst_dirs:
    print(f'  {GAME}\\{d}\\i50125711.bml')

print(f'\n=== 建议下一步 ===')
print(f'1. sc.exe stop ApolloProtect')
print(f'2. 启动游戏进入大厅')
print(f'3. py hook_diag_group_read.py')
print(f'4. 进入房间触发加载')
print(f'5. 观察是否出现 res768 AcquireSMD')
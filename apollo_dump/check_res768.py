import sys
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

pak = PGFNPak(r'C:\Program Files (x86)\T2CN\街头篮球\res768.pak')
print(f'res768.pak: {len(pak.entries)} entries')

# 列出所有文件
smds = [e for e in pak.entries if e['name'].endswith('.smd')]
pngs = [e for e in pak.entries if e['name'].endswith('.png')]
print(f'SMD: {len(smds)}, PNG: {len(pngs)}')

# 显示50125开头的SMD
for s in smds:
    if '50125' in s['name']:
        print(f'  {s["name"]} ({s["data_size"]}B)')
        if '50125711' in s['name']:
            print(f'    ^^^ TARGET!')

print(f'\n共 {len([s for s in smds if "50125" in s["name"]])} 个 50125* SMD')

# 也列出前10个SMD看看命名模式
print('\n前10个SMD:')
for s in smds[:10]:
    print(f'  {s["name"]}')
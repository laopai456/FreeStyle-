import sys
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak

# 检查res768.pak中所有文件
pak = PGFNPak(r'C:\Program Files (x86)\T2CN\街头篮球\res768.pak')
print(f'res768.pak: {len(pak.entries)} entries\n')

# 按文件名前缀分组
for e in pak.entries:
    name = e['name']
    # 提取物品前缀
    if name.startswith('i'):
        parts = name.split('_')
        if len(parts) >= 2:
            prefix = parts[0]
            print(f'  {name} ({e["data_size"]}B)')

# 也检查item768.pak中50125701的BML（对比参考）
print('\n=== item768.pak BML列表 ===')
item_pak = PGFNPak(r'C:\Program Files (x86)\T2CN\街头篮球\item768.pak')
for e in item_pak.entries:
    if '50125' in e['name']:
        print(f'  {e["name"]} ({e["data_size"]}B)')

# 现在看看：50125701有2个SMD(mt,mn)，对应的BML可能也是引用这两者
# 50125711只有1个SMD(fn)，但BML引用了8个！
# 这说明BML可能是模板/共享格式，实际加载时游戏会fallback到可用的variant

print('\n=== 结论 ===')
print('50125711只有 fn.smd (女性角色N类型) 的SMD')
print('BML中引用的其他变体(MT/MS/MN/MF/FT/FS/FSC)在res768.pak中不存在')
print('可能需要修改BML，让所有character type都指向 fn.smd')
print('或者游戏会自动fallback到可用的variant')
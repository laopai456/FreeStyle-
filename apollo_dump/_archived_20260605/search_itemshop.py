"""search_itemshop.py — 搜索itemshop JSON数据库"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'

with open(DB_PATH, 'r', encoding='utf-8') as f:
    db = json.load(f)

print(f'数据库总条目: {len(db)}')

# 1. 搜索"超赛"
print('\n=== 搜索"超赛" ===')
results = [(k, v) for k, v in db.items() if '超赛' in v.get('name', '')]
for k, v in results:
    print(f'  {k}: {v["name"]}')
    print(f'    pak={v.get("pak","?")} cat={v.get("category","?")}')

# 2. 搜索50125711
print('\n=== 50125711 详细信息 ===')
item = db.get('50125711', {})
if item:
    for key, val in item.items():
        print(f'  {key}: {val}')
else:
    print('  未找到!')
    # 尝试不带前导0
    item = db.get(50125711, db.get('50125711', {}))

# 3. 查看pak768中的所有发型
print('\n=== pak768中的发型 (itemcode前缀50125) ===')
for k, v in db.items():
    if v.get('pak') == '768' and '发' in v.get('name', ''):
        print(f'  {k}: {v["name"]}')
    elif v.get('pak') == '768' and k.startswith('501'):
        print(f'  {k}: {v["name"]} (pak768)')

# 4. 搜索所有类似的"超赛"系列，找出同一家族的item
print('\n=== "超赛"完整系列 ===')
for k, v in results:
    pak_num = v.get('pak', '?')
    print(f'  {k}: {v["name"]} pak={pak_num}')
    # 检查attributes
    for attr_k in sorted(v.keys()):
        if attr_k == 'name' or attr_k == 'pak' or attr_k == 'category':
            continue
        val = v[attr_k]
        if val and str(val).strip():
            print(f'    {attr_k}: {val}')

# 5. 搜索501257附近的所有item
print('\n=== 50125690-50125730 范围 ===')
for k in sorted(db.keys(), key=lambda x: int(x)):
    ik = int(k)
    if 50125690 <= ik <= 50125730:
        v = db[k]
        print(f'  {k}: {v.get("name","?")} pak={v.get("pak","?")}')
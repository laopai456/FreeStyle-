"""解析 itemshop.txt 并查找发型 code"""
import json, re

path = r'D:\py\反编译\FreeStyle\bin\Debug\net8.0-windows\cookies\item_text_pak\itemshop.txt'
lines = open(path, encoding='gbk').read().splitlines()
header = lines[0].split('\t')
print('Header:', header)

# SMD FILE 输出中的 code
smd_codes = [50125711, 50421161, 50519681, 50623611, 51612121,
             51212851, 50914671, 51313301, 50125701, 50125691, 50119441]

# 建索引
all_items = {}
for ln in lines[1:]:
    if not ln.strip(): continue
    parts = ln.split('\t')
    if not parts or not parts[0].isdigit(): continue
    code = int(parts[0])
    all_items[code] = {
        'code': code,
        'pak': parts[1] if len(parts) > 1 else '',
        'effect': parts[2] if len(parts) > 2 else '',
        'name': parts[3].strip() if len(parts) > 3 else '',
        'comment': parts[4].strip() if len(parts) > 4 else '',
    }

# 分类
hair_items = []
for c, item in all_items.items():
    if 100000 <= c < 102000:
        item['category'] = '男发'
        hair_items.append(item)
    elif 120000 <= c < 130000:
        item['category'] = '女发'
        hair_items.append(item)
    elif 110000 <= c < 120000:
        item['category'] = '男头饰'
        hair_items.append(item)
    elif 130000 <= c < 140000:
        item['category'] = '女头饰'
        hair_items.append(item)

print(f'\n=== All head/hair items: {len(hair_items)} ===')
for h in hair_items[:30]:
    print(f'  {h["code"]} [{h["category"]}] {h["name"]}')

print('\n=== SMD codes lookup in itemshop ===')
for c in smd_codes:
    if c in all_items:
        it = all_items[c]
        print(f'  MATCH! {c}: {it["name"]}')
    else:
        print(f'  NOT FOUND: {c}')

# 如果 SMD code 不在 itemshop，可能是内部模型 ID
# 尝试找 5xxxxxx 格式的 code 在全部数据中出现情况
print('\n=== All 50xxxxx codes in itemshop ===')
for c, it in sorted(all_items.items()):
    if 50000000 <= c < 51000000:
        print(f'  {c}: {it["name"]}')
if not any(50000000 <= c < 51000000 for c in all_items):
    print('  (none)')

# 输出发型 JSON
out_path = r'D:\py\反编译\FreeStyle\apollo_dump\hair_items.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(hair_items, f, ensure_ascii=False, indent=2)
print(f'\nSaved {len(hair_items)} items to {out_path}')
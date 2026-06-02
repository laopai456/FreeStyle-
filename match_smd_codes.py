"""查 FILE 输出中所有 SMD code 对应的 itemshop 名称"""
import json

path = r'D:\py\反编译\FreeStyle\bin\Debug\net8.0-windows\cookies\item_text_pak\itemshop.txt'
lines = open(path, encoding='gbk').read().splitlines()

# FILE 输出中的 code（去掉后缀）
filenames = [
    "c3000.smd", "i50125711_ms.smd", "i50421161_MT.smd", "i50421161_MT_upp01.smd",
    "i50519681_MT.smd", "i50519681_M_low01.smd", "i50623611_M.smd", "i51612121.smd",
    "i51212851.smd", "i50914671_MT.smd", "i51313301_MT.smd", "SMD_2211_halo001.smd",
    "i50125701_ms.smd", "i50125691_MS.smd", "i50119441_M.smd",
]

# 建 itemshop 索引
all_items = {}
for ln in lines:
    if not ln.strip(): continue
    parts = ln.split('\t')
    if len(parts) < 4: continue
    try:
        code = int(parts[0])
        all_items[code] = {'name': parts[3].strip(), 'comment': parts[4].strip() if len(parts) > 4 else ''}
    except:
        pass

print(f"itemshop total: {len(all_items)} items\n")

# 从文件名中提取 code
import re
for f in sorted(filenames):
    m = re.search(r'i(\d+)', f)
    if not m:
        print(f"  SKIP: {f}")
        continue
    code = int(m.group(1))
    if code in all_items:
        it = all_items[code]
        print(f"  {f:35s} → {code} = {it['name']}")
    else:
        print(f"  {f:35s} → {code} = NOT FOUND in itemshop")

# 找出 itemshop 中所有 50xxxxxx 范围的发型（itemcode 5开头且名字含"发"）
print("\n=== 50xxxxx items with '发' in name ===")
hair_50x = []
for code, it in sorted(all_items.items()):
    if 50000000 <= code < 60000000 and '发' in it['name']:
        hair_50x.append((code, it['name']))
        print(f"  {code}: {it['name']}")
print(f"  ({len(hair_50x)} items)")
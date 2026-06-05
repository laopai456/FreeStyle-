# update_itemshop.py — 一键从游戏目录解包 itemshop 最新数据
# 用法: python update_itemshop.py
# 输出: itemshop.json (覆盖写入)
import struct, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

PAK_PATH = r'C:\Program Files (x86)\T2CN\街头篮球\item_text.pak'
JSON_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'

def extract():
    with open(PAK_PATH, 'rb') as f:
        data = f.read()

    # 定位 itemshop.txt 数据头
    marker = b'ItemCode\tPakNum'
    idx = data.find(marker)
    if idx < 0:
        print('ERROR: 未找到 ItemCode 头部')
        return

    text = data[idx:].decode('gbk', errors='replace')
    lines = text.splitlines()

    db = {}
    for ln in lines[1:]:
        if not ln.strip():
            continue
        parts = ln.split('\t')
        code = parts[0].strip()
        if not code.isdigit():
            continue
        entry = {
            'name': parts[3].strip() if len(parts) > 3 else '',
            'pak': parts[1].strip() if len(parts) > 1 else '',
        }
        if len(parts) > 2 and parts[2].strip():
            entry['effect'] = parts[2].strip()
        if len(parts) > 4 and parts[4].strip():
            entry['desc'] = parts[4].strip()[:100]
        db[code] = entry

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)

    print(f'✅ {len(db)} 条 → {JSON_PATH}')

    # 验证
    for code in ['50125461', '50125711', '51415951']:
        item = db.get(code, {})
        print(f'  {code}: {item.get("name", "?")} pak={item.get("pak", "?")}')

if __name__ == '__main__':
    extract()

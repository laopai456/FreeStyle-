"""add_hair.py — 从 itemshop.txt 更新数据库 / 搜索发型并添加到 hair_styles.json

用法:
  python add_hair.py                    # 交互：更新数据库 / 添加发型
  python add_hair.py update             # 直接更新数据库
  python add_hair.py 关键词             # 搜索并交互式添加
  python add_hair.py 50124241           # 直接通过 ItemCode 添加
  python add_hair.py list               # 查看当前 hair_styles.json

示例:
  python add_hair.py update             # 从 itemshop.txt 重建数据库
  python add_hair.py 超赛               # 从数据库搜索"超赛"发型
  python add_hair.py 鬼魅               # 搜索"鬼魅"
"""

import sys
import os
import json
import csv

# ─── 路径配置 ───────────────────────────────────────────────
ITEM_TEXT_PAK = r'C:\Program Files (x86)\T2CN\街头篮球\item_text.pak'
ITESHOP_JSON = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'
HAIR_JSON    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hair_styles.json')
# ────────────────────────────────────────────────────────────


def parse_itemshop_txt(txt_path):
    """将 itemshop.txt (TSV) 解析为 {ItemCode: {...}} 的字典"""
    if not os.path.exists(txt_path):
        print(f'❌ 文件不存在: {txt_path}')
        return None

    db = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for i, row in enumerate(reader):
            if i == 0:
                continue  # 跳过表头
            if len(row) < 4:
                continue
            code = row[0].strip()
            pak  = row[1].strip()
            cat  = row[2].strip() if len(row) > 2 else ''
            name = row[3].strip()
            desc = row[4].strip() if len(row) > 4 else ''

            if not code or not code.isdigit():
                continue

            db[code] = {
                'pak': pak,
                'category': cat,
                'name': name,
                'desc': desc
            }

    return db


def update_database():
    """从游戏目录 item_text.pak 提取最新 itemshop.json"""
    import struct
    print('🔄 正在从 item_text.pak 提取 ...')
    try:
        with open(ITEM_TEXT_PAK, 'rb') as f:
            data = f.read()
        idx = data.find(b'ItemCode\tPakNum')
        if idx < 0:
            print('❌ pak 中未找到 ItemCode 头部')
            return False
        text = data[idx:].decode('gbk', errors='replace')
        lines = text.splitlines()
        db = {}
        for ln in lines[1:]:
            if not ln.strip(): continue
            parts = ln.split('\t')
            code = parts[0].strip()
            if not code.isdigit(): continue
            entry = {'name': parts[3].strip() if len(parts) > 3 else '',
                     'pak': parts[1].strip() if len(parts) > 1 else ''}
            if len(parts) > 2 and parts[2].strip():
                entry['category'] = parts[2].strip()
            if len(parts) > 4 and parts[4].strip():
                entry['desc'] = parts[4].strip()[:100]
            db[code] = entry
    except FileNotFoundError:
        print(f'❌ 文件不存在: {ITEM_TEXT_PAK}')
        return False

    os.makedirs(os.path.dirname(ITESHOP_JSON), exist_ok=True)
    with open(ITESHOP_JSON, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f'✅ 数据库已更新: {len(db)} 条')
    print(f'   来源: {ITEM_TEXT_PAK}')
    print(f'   输出: {ITESHOP_JSON}')
    return True


def load_json(path):
    """安全加载 JSON"""
    if not os.path.exists(path):
        print(f'❌ 文件不存在: {path}')
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f'❌ JSON 解析错误: {e}')
        return None


def save_json(path, data):
    """写回 JSON"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✅ 已保存 ({len(data)} 条) → {path}')


def search_itemshop(db, keyword):
    """在数据库中搜索匹配项"""
    results = []
    for code, item in db.items():
        name = str(item.get('name', ''))
        pak = item.get('pak', '?')
        if keyword.lower() in name.lower():
            results.append((code, name, pak))
    return results


def list_current(hair_data):
    """显示当前发型列表"""
    if not hair_data:
        print('当前 hair_styles.json 为空')
        return
    print(f'\n📋 当前发型列表 ({len(hair_data)} 条)：')
    print(f'{"ItemCode":<12} {"名称":<20} {"pak":<6}')
    print('-' * 42)
    for item in sorted(hair_data, key=lambda x: x['itemCode']):
        print(f'{item["itemCode"]:<12} {item["name"]:<20} {item["pak"]:<6}')


def show_all_hairs(db):
    """显示数据库中所有含"发"的物品"""
    results = []
    for code, item in db.items():
        name = str(item.get('name', ''))
        pak = item.get('pak', '?')
        if '发' in name:
            results.append((code, name, pak))
    return results


def add_to_hair_list(hair_data, new_code, new_name, new_pak):
    """添加条目到发型列表（去重）"""
    existing_codes = {item['itemCode'] for item in hair_data}
    if new_code in existing_codes:
        return hair_data, False
    hair_data.append({
        'itemCode': new_code,
        'name': new_name,
        'pak': new_pak
    })
    hair_data.sort(key=lambda x: x['itemCode'])
    return hair_data, True


def interactive_add(hair_data, db, results):
    """交互式选择添加"""
    if not results:
        return hair_data

    print(f'\n🔍 找到 {len(results)} 个匹配项：')
    print(f'{"#":<4} {"ItemCode":<12} {"名称":<24} {"pak":<6}')
    print('-' * 50)
    for i, (code, name, pak) in enumerate(results, 1):
        existing = any(item['itemCode'] == int(code) for item in hair_data)
        flag = ' ✅ 已有' if existing else ''
        print(f'{i:<4} {code:<12} {name:<24} {pak:<6}{flag}')

    print()
    print('输入编号添加，多个用空格分隔（如: 1 3 5）')
    print('输入 a 添加全部，q 取消')
    choice = input('> ').strip()

    if choice.lower() == 'q':
        return hair_data

    if choice.lower() == 'a':
        for code, name, pak in results:
            pak_int = int(pak) if str(pak).isdigit() else pak
            hair_data, _ = add_to_hair_list(hair_data, int(code), name, pak_int)
        hair_data.sort(key=lambda x: x['itemCode'])
        return hair_data

    indices = []
    for part in choice.split():
        try:
            idx = int(part)
            if 1 <= idx <= len(results):
                indices.append(idx)
            else:
                print(f'⚠️ 编号越界: {idx}')
        except ValueError:
            print(f'⚠️ 无效输入: {part}')

    for idx in indices:
        code, name, pak = results[idx - 1]
        pak_int = int(pak) if str(pak).isdigit() else pak
        hair_data, _ = add_to_hair_list(hair_data, int(code), name, pak_int)

    return hair_data


def add_hair_flow(itemshop_db, hair_data, keyword):
    """搜索发型并添加的完整流程"""
    results = search_itemshop(itemshop_db, keyword)

    if not results:
        print(f'❌ 数据库中未找到含 "{keyword}" 的物品')
        return hair_data

    # 发型优先在前
    hair_results = [(c, n, p) for c, n, p in results if '发' in n]
    other_results = [(c, n, p) for c, n, p in results if '发' not in n]

    if hair_results:
        hair_data = interactive_add(hair_data, itemshop_db, hair_results)

    if other_results:
        print(f'\n📦 其他匹配 ({len(other_results)} 条)：')
        show_others = input('显示其他匹配？(y/n): ').strip().lower()
        if show_others == 'y':
            hair_data = interactive_add(hair_data, itemshop_db, other_results)

    return hair_data


def main():
    # ── 无参数 → 选择操作 ──
    if len(sys.argv) < 2:
        print('请选择操作：')
        print('  1. 更新数据库  (从 itemshop.txt 重建 itemshop.json)')
        print('  2. 添加发型    (搜索数据库并添加到 hair_styles.json)')
        print('  3. 查看列表    (显示当前 hair_styles.json)')
        choice = input('输入 1/2/3: ').strip()

        if choice == '1':
            update_database()
        elif choice == '2' or choice == '':
            # 先确保数据库存在
            if not os.path.exists(ITESHOP_JSON):
                print('⚠️ 数据库不存在，先更新...')
                update_database()
            itemshop_db = load_json(ITESHOP_JSON)
            if itemshop_db is None:
                return
            hair_data = load_json(HAIR_JSON) or []
            kw = input('输入搜索关键词: ').strip()
            if kw:
                hair_data = add_hair_flow(itemshop_db, hair_data, kw)
                save_json(HAIR_JSON, hair_data)
        elif choice == '3':
            hair_data = load_json(HAIR_JSON) or []
            list_current(hair_data)
        return

    arg = sys.argv[1]

    # ── update: 更新数据库 ──
    if arg.lower() == 'update':
        update_database()
        return

    # ── 确保数据库存在 ──
    if not os.path.exists(ITESHOP_JSON):
        print('⚠️ 数据库不存在，先自动更新...')
        if not update_database():
            return

    itemshop_db = load_json(ITESHOP_JSON)
    if itemshop_db is None:
        return

    hair_data = load_json(HAIR_JSON) or []
    # 标准化 itemCode 为 int
    for item in hair_data:
        if isinstance(item.get('itemCode'), str):
            item['itemCode'] = int(item['itemCode'])

    # ── list: 查看当前列表 ──
    if arg.lower() == 'list':
        list_current(hair_data)
        return

    # ── search-all: 浏览所有发型 ──
    if arg.lower() == 'all':
        all_hairs = show_all_hairs(itemshop_db)
        print(f'\n📦 数据库中所有含"发"的物品 ({len(all_hairs)} 条)：')
        print(f'{"ItemCode":<12} {"名称":<24} {"pak":<6}')
        print('-' * 45)
        for code, name, pak in sorted(all_hairs, key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
            print(f'{code:<12} {name:<24} {pak:<6}')
        return

    # ── 直接通过 ItemCode 添加 ──
    try:
        code_int = int(arg)
        code_str = str(code_int)
        item = itemshop_db.get(code_str)
        if not item:
            print(f'❌ 数据库中未找到 ItemCode: {code_int}')
            return
        name = item.get('name', '?')
        pak = item.get('pak', '?')
        pak_int = int(pak) if str(pak).isdigit() else pak
        hair_data, changed = add_to_hair_list(hair_data, code_int, name, pak_int)
        if changed:
            save_json(HAIR_JSON, hair_data)
        else:
            print(f'⚠️ {code_int} ({name}) 已存在')
        return
    except ValueError:
        pass

    # ── 关键词搜索 → 添加 ──
    hair_data = add_hair_flow(itemshop_db, hair_data, arg)
    save_json(HAIR_JSON, hair_data)


if __name__ == '__main__':
    main()

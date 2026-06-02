# build_hair_table.py
# 从 itemshop.json 提取动态发型信息，生成发型表

import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'

# 要查询的发型名称关键词
HAIR_KEYWORDS = [
    '鬼魅',
    '少年漫',
    '霓虹超赛',
    '金色超赛',
    '火焰超赛',
    '淡粉超赛',
    '超赛之神',
    '极限超赛',
    '紫色超赛',
    '超赛',
]

def main():
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    print(f'数据库总条目: {len(db)}')
    print('')

    # 收集所有发型
    hair_items = {}

    for k, v in db.items():
        name = v.get('name', '')
        if not name:
            continue

        # 检查是否是发型（通常以 501 开头）
        if not k.startswith('501'):
            continue

        # 检查是否匹配关键词
        for kw in HAIR_KEYWORDS:
            if kw in name:
                pak = v.get('pak', '?')
                cat = v.get('category', '?')

                # 判断是否动态（pak >= 768 通常是动态）
                is_dynamic = '动态' if pak != '?' and int(pak) >= 768 else '静态'

                hair_items[k] = {
                    'name': name,
                    'pak': pak,
                    'category': cat,
                    'type': is_dynamic,
                    'keyword': kw,
                }
                break

    # 按关键词分组显示
    print('=' * 60)
    print('动态发型表')
    print('=' * 60)

    for kw in HAIR_KEYWORDS:
        items = [(k, v) for k, v in hair_items.items() if v.get('keyword') == kw]
        if items:
            print(f'\n【{kw}】')
            for k, v in sorted(items, key=lambda x: int(x[0])):
                print(f'  {k}: {v["name"]}')
                print(f'       pak={v["pak"]} 类型={v["type"]}')

    # 生成 Python 字典格式
    print('\n' + '=' * 60)
    print('Python 字典格式（可直接复制到脚本）')
    print('=' * 60)
    print('\nHAIR_TABLE = {')

    # 按名称排序
    for k, v in sorted(hair_items.items(), key=lambda x: x[1]['name']):
        print(f'    "{v["name"]}": {{')
        print(f'        "itemcode": {k},')
        print(f'        "pak": {v["pak"]},')
        print(f'        "type": "{v["type"]}",')
        print(f'    }},')
    print('}')

    # 生成简洁版
    print('\n' + '=' * 60)
    print('简洁版（itemcode: name）')
    print('=' * 60)
    print('\nHAIR_CODES = {')
    for k, v in sorted(hair_items.items(), key=lambda x: x[1]['name']):
        print(f'    {k}: "{v["name"]}",  # pak={v["pak"]} {v["type"]}')
    print('}')

if __name__ == '__main__':
    main()
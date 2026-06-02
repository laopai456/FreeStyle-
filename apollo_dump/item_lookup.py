# item_lookup.py - ItemCode快速查名称/pak号，用于脚本注释
# 用法: from item_lookup import name, pak, info
#       print(name('50125461'))  # 美丽梦想发型
#       print(pak('50125461'))   # 767
#       print(info('50125461'))  # 美丽梦想发型(pak767)
import json, os, sys

_DB = None
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json')

def _load():
    global _DB
    if _DB is None:
        with open(_PATH, 'r', encoding='utf-8') as f:
            _DB = json.load(f)
    return _DB

def name(code):
    """item_name('50125461') → '美丽梦想发型'"""
    d = _load().get(str(code), {})
    return d.get('name', f'未知({code})')

def pak(code):
    """item_pak('50125461') → '767'"""
    d = _load().get(str(code), {})
    return d.get('pak', '?')

def info(code):
    """item_info('50125461') → '美丽梦想发型(pak767)'"""
    return f"{name(code)}(pak{pak(code)})"

def search(keyword):
    """按关键字搜索: item_search('超赛') → [('50125711', ...), ...]"""
    db = _load()
    return [(k, v) for k, v in db.items() if keyword in v.get('name', '')]

if __name__ == '__main__':
    # 测试
    for code in ['50125461', '50125711', '50125331']:
        print(f'{code}: {info(code)}')
    print()
    print("搜索'超赛':")
    for k, v in search('超赛'):
        print(f'  {k}: {v["name"]} (pak{v["pak"]})')

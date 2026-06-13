# itemshop_db.py — itemshop 数据查询服务
# 供 server.py 调用，提供道具名称/PAK/搜索功能
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'data', 'itemshop.json')
_db = None

def _load():
    global _db
    if _db is None:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            _db = json.load(f)
    return _db

def get_name(code):
    """get_name(50125461) -> '美丽梦想发型'"""
    return _load().get(str(code), {}).get('name', f'未知({code})')

def get_pak(code):
    """get_pak(50125461) -> '767'"""
    return _load().get(str(code), {}).get('pak', '?')

def get_info(code):
    """get_info(50125461) -> {'name':'...', 'pak':'...'}"""
    return _load().get(str(code), {})

def search(keyword, limit=50):
    """search('超赛') -> [{'code':'50125711','name':'紫色超赛发型','pak':'768'},...]"""
    db = _load()
    kw = keyword.lower()
    results = []
    for code, item in db.items():
        name = item.get('name', '')
        if kw in name.lower() or kw in code:
            results.append({
                'code': code,
                'name': name,
                'pak': item.get('pak', '?')
            })
            if len(results) >= limit:
                break
    return results

def search_by_code_range(prefix, limit=50):
    """search_by_code_range('501') -> 所有501开头的道具"""
    db = _load()
    results = []
    for code, item in db.items():
        if code.startswith(prefix):
            results.append({
                'code': code,
                'name': item.get('name', ''),
                'pak': item.get('pak', '?')
            })
            if len(results) >= limit:
                break
    return results

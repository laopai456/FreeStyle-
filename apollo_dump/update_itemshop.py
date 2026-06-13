"""update_itemshop.py — 从 item_text.pak 更新 itemshop.json 的道具名称"""
import json, os

ITEMSHOP_PATH = r'C:\Users\w\.claude\projects\C--Users-w-Documents-GitHub-cc\memory\itemshop.json'
PAK_PATH = r'C:\Program Files (x86)\T2CN\街头篮球\item_text.pak'

def main():
    # Load current itemshop.json
    with open(ITEMSHOP_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # Parse item_text.pak
    with open(PAK_PATH, 'rb') as f:
        data = f.read()

    marker = b'ItemCode\tPakNum'
    idx = data.find(marker)
    if idx < 0:
        print('ERROR: ItemCode marker not found in pak')
        return
    end = data.find(b'\n', idx)
    text_data = data[end+1:].decode('gbk', errors='replace')

    # Build name/effect/pak map from pak
    pak_names = {}
    for line in text_data.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 4 and parts[0].strip().isdigit():
            code = parts[0].strip()
            pak_num = parts[1].strip() if len(parts) > 1 else ''
            name = parts[3].strip()
            effect = parts[2].strip() if len(parts) > 2 else ''
            if name:
                pak_names[code] = {'name': name, 'effect': effect, 'pak': pak_num}

    # Update db
    updated = 0
    pak_updated = 0
    new_items = 0
    for code, info in pak_names.items():
        if code in db:
            if not db[code].get('name'):
                db[code]['name'] = info['name']
                updated += 1
            if info['effect'] and not db[code].get('effect'):
                db[code]['effect'] = info['effect']
            # Always update pak from item_text.pak (source of truth)
            if info['pak'] and db[code].get('pak') != info['pak']:
                db[code]['pak'] = info['pak']
                pak_updated += 1
        else:
            db[code] = {'name': info['name'], 'pak': info['pak'], 'effect': info['effect']}
            new_items += 1

    print(f'Updated names: {updated}')
    print(f'Updated pak: {pak_updated}')
    print(f'New items: {new_items}')
    print(f'Total items in db: {len(db)}')

    # Verify
    code = '51612121'
    print(f'{code} name: {db.get(code, {}).get("name", "NOT FOUND")}')

    # Save
    with open(ITEMSHOP_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print('Saved!')

if __name__ == '__main__':
    main()

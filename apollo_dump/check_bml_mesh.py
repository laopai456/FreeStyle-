# check_bml_mesh.py - 读取item767和item768的BML，找出mesh路径
import sys, struct, os
sys.stdout.reconfigure(encoding='utf-8')

def xor_decode(data):
    return bytes(b ^ 0xFF for b in data)

def parse_pgfn(data):
    """解析PGFN pak链表"""
    entries = {}
    pos = 0
    while pos < len(data) - 16:
        dwNameSize = struct.unpack_from('<I', data, pos)[0]
        dwElementPos = struct.unpack_from('<I', data, pos+4)[0]
        dwElementSize = struct.unpack_from('<I', data, pos+8)[0]
        dwNextElement = struct.unpack_from('<I', data, pos+12)[0]
        
        if dwNameSize == 0 or dwNameSize > 256:
            break
        
        try:
            name = data[pos+16:pos+16+dwNameSize].rstrip(b'\x00').decode('ascii', errors='replace')
        except:
            break
        
        element_data = data[dwElementPos:dwElementPos+dwElementSize]
        entries[name] = element_data
        
        if dwNextElement == 0:
            break
        pos = dwNextElement
    
    return entries

def find_bml_for_item(entries, item_code):
    """找包含指定ItemCode的BML"""
    for name, data in entries.items():
        decoded = xor_decode(data)
        try:
            text = decoded.decode('utf-8', errors='replace')
            if item_code in text:
                return name, text
        except:
            continue
    return None, None

# 读取item767.pak
pak_dir = r"C:\Program Files (x86)\T2CN\街头篮球"
item767 = os.path.join(pak_dir, "item767.pak")
item768 = os.path.join(pak_dir, "item768.pak")

for pak_path, pak_num, items_to_find in [
    (item767, 767, ['50125461']),
    (item768, 768, ['50125711']),
]:
    print(f'\n=== item{pak_num}.pak ===')
    if not os.path.exists(pak_path):
        print(f'  文件不存在: {pak_path}')
        continue
    
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    entries = parse_pgfn(data)
    print(f'  共 {len(entries)} 个条目')
    
    for ic in items_to_find:
        name, text = find_bml_for_item(entries, ic)
        if text:
            print(f'\n  --- {ic} BML ({name}) ---')
            # 显示mesh和texture标签
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if '<mesh>' in line.lower() or '<texture>' in line.lower() or '<file>' in line.lower():
                    print(f'  {line}')
        else:
            print(f'  {ic}: 未找到BML')


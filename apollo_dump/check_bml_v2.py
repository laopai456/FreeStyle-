# check_bml_v2.py - 正确解析PGFN pak并提取BML
import sys, struct, os
sys.stdout.reconfigure(encoding='utf-8')

def xor_decode(data):
    return bytes(b ^ 0xFF for b in data)

def parse_pgfn(data):
    """解析PGFN pak - 5个DWORD头部"""
    if data[:4] != b'PGFN':
        return {}
    
    entries = {}
    # 跳过PGFN头部(0x18字节)
    pos = 0x18
    
    while pos < len(data) - 20:
        dwField1 = struct.unpack_from('<I', data, pos)[0]      # 元素大小
        dwNameSize = struct.unpack_from('<I', data, pos+4)[0]   # 名字长度
        dwElementPos = struct.unpack_from('<I', data, pos+8)[0] # 数据位置
        dwNextElement = struct.unpack_from('<I', data, pos+12)[0]  # 下一元素
        dwField5 = struct.unpack_from('<I', data, pos+16)[0]    # 未知
        
        if dwNameSize == 0 or dwNameSize > 256 or dwField1 > 0x100000:
            break
        
        name_start = pos + 20
        name = data[name_start:name_start+dwNameSize].rstrip(b'\x00').decode('ascii', errors='replace')
        
        element_data = data[dwElementPos:dwElementPos+dwField1]
        entries[name] = element_data
        
        if dwNextElement == 0:
            break
        pos = dwNextElement
    
    return entries

pak_dir = r"C:\Program Files (x86)\T2CN\街头篮球"

for pak_num in [767, 768]:
    pak_path = os.path.join(pak_dir, f"item{pak_num}.pak")
    print(f'\n=== item{pak_num}.pak ===')
    
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    entries = parse_pgfn(data)
    print(f'共 {len(entries)} 个条目')
    
    # 列出所有BML文件名
    bml_names = [n for n in entries if n.endswith('.bml')]
    print(f'BML文件: {bml_names[:10]}...')
    
    # 找目标物品的BML
    targets = ['50125461', '50125711']
    for name, edata in entries.items():
        decoded = xor_decode(edata)
        try:
            text = decoded.decode('utf-8', errors='replace')
        except:
            continue
        
        for t in targets:
            if t in text:
                print(f'\n--- {name} (包含{t}) ---')
                # 提取mesh和texture行
                for line in text.split('\n'):
                    line = line.strip()
                    if any(tag in line.lower() for tag in ['<mesh>', '<texture>', '<file>', '<itemcode', '<animation>']):
                        print(f'  {line}')


"""
extract_single_bml.py — 从multi-item BML中提取单个物品的独立BML
用法:
  py extract_single_bml.py <pak_path> <itemcode>
  py extract_single_bml.py <multi_bml_file> <itemcode> --file

例:
  py extract_single_bml.py "C:\Program Files (x86)\T2CN\街头篮球\item768.pak" 50125711
"""
import sys, os, struct

XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def parse_pgfn(data):
    if data[:4] != b'PGFN':
        return {}
    entries = {}
    pos = 0x18
    while pos < len(data) - 20:
        dwField1 = struct.unpack_from('<I', data, pos)[0]
        dwNameSize = struct.unpack_from('<I', data, pos+4)[0]
        dwElementPos = struct.unpack_from('<I', data, pos+8)[0]
        dwNextElement = struct.unpack_from('<I', data, pos+12)[0]
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

def extract_single_bml(multi_bml_data, target_ic):
    """从multi-item BML中提取单个物品的独立BML"""
    decoded = xor_crypt(multi_bml_data)

    # 找到目标<root>段
    # 在解码后的数据中搜索包含目标IC的<root>...</root>块
    search_str = target_ic.encode('utf-8')
    search_str2 = target_ic.encode('ascii')

    # 找到目标IC所在位置
    idx = decoded.find(search_str)
    if idx < 0:
        idx = decoded.find(search_str2)
    if idx < 0:
        print(f'[!] 未找到 {target_ic}')
        return None

    print(f'[*] 找到 {target_ic} 在偏移 {idx}')

    # 向前找最近的 <root>
    root_start = decoded.rfind(b'<root>', 0, idx)
    if root_start < 0:
        print('[!] 未找到 <root>')
        return None

    # 向后找对应的 </root>
    root_end = decoded.find(b'</root>', idx)
    if root_end < 0:
        print('[!] 未找到 </root>')
        return None
    root_end += len(b'</root>')

    # 提取完整的XML段
    xml_section = decoded[root_start:root_end]
    print(f'[*] XML段: offset={root_start} size={len(xml_section)}B')

    try:
        xml_text = xml_section.decode('utf-8', errors='replace')
    except:
        xml_text = xml_section.decode('ascii', errors='replace')

    print(f'\n[*] 提取的XML:')
    print(xml_text)

    return xml_section

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    target_ic = sys.argv[2] if len(sys.argv) > 2 else '50125711'

    if '--file' in sys.argv:
        # 直接从multi-item BML文件读取
        bml_path = sys.argv[1]
        with open(bml_path, 'rb') as f:
            multi_data = f.read()
    else:
        # 从PAK提取
        pak_path = sys.argv[1]
        with open(pak_path, 'rb') as f:
            pak_data = f.read()
        entries = parse_pgfn(pak_data)
        bmls = [n for n in entries if n.endswith('.bml')]
        if not bmls:
            print(f'[!] PAK中没有BML文件')
            return
        multi_data = entries[bmls[0]]
        print(f'[*] PAK中BML: {bmls[0]}, size={len(multi_data)}B')

    xml_section = extract_single_bml(multi_data, target_ic)
    if xml_section is None:
        return

    # 创建带XML声明的完整BML
    full_xml = b'<?xml version="1.0"?>\n' + xml_section

    # XOR编码为BML
    encoded = xor_crypt(full_xml)

    # 输出
    out_name = f'i{target_ic}_standalone.bml'
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    with open(out_path, 'wb') as f:
        f.write(encoded)
    print(f'\n[+] 独立BML已保存: {out_path} ({len(encoded)}B)')

    # 也保存解码版本方便查看
    xml_out = out_path.replace('.bml', '.xml')
    with open(xml_out, 'w', encoding='utf-8') as f:
        f.write(full_xml.decode('utf-8'))
    print(f'[+] XML版本: {xml_out}')

    print(f'\n[*] 部署命令:')
    game_dir = r'C:\Program Files (x86)\T2CN\街头篮球'
    print(f'    copy "{out_path}" "{game_dir}\\Resource\\item\\i{target_ic}.bml"')

if __name__ == '__main__':
    main()
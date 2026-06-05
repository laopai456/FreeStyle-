# patch_res767.py - 替换res767.pak中i50125461的SMD数据为i50125711
# 用法: py patch_res767.py
# 备份: C:\Users\w\Desktop\res767.pak
import struct, sys, os, shutil

sys.stdout.reconfigure(encoding='utf-8')

GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
BACKUP_DIR = r'C:\Users\w\Desktop'

# 映射: res767里的文件名 → res768里对应的文件名
REPLACE_MAP = {
    'i50125461_mt.smd':  'i50125711_mt.smd',
    'i50125461_ms.smd':  'i50125711_ms.smd',
    'i50125461_mn.smd':  'i50125711_mn.smd',
    'i50125461_mf.smd':  'i50125711_mf.smd',
    'i50125461_ft.smd':  'i50125711_ft.smd',
    'i50125461_fs.smd':  'i50125711_fs.smd',
    'i50125461_fn.smd':  'i50125711_fn.smd',
    'i50125461_fsc.smd': 'i50125711_fsc.smd',
}

def parse_pak(path):
    with open(path, 'rb') as f:
        data = f.read()

    hdr = data[:24]
    numShares = struct.unpack_from('<I', hdr, 20)[0]
    assert numShares == 0

    numEl = struct.unpack_from('<I', data, 24)[0]
    suc = data[-16:]

    entries = []
    pos = 28
    for i in range(numEl):
        ns, ep, es, ne = struct.unpack_from('<IIII', data, pos)
        name_raw = data[pos+16 : pos+16+ns]
        name = name_raw.decode('ascii', errors='replace').rstrip('\x00')
        entry_data = data[ep : ep+es]
        entries.append({
            'name_raw': name_raw,
            'name': name,
            'old_elPos': ep,
            'old_elSize': es,
            'data': entry_data,
        })
        if ne == 0:
            break
        pos = ne

    return hdr, numEl, entries, suc, data

def get_replacement_data(res768_path):
    """从res768.pak提取i50125711的SMD数据"""
    replacements = {}
    with open(res768_path, 'rb') as f:
        data = f.read()

    numEl = struct.unpack_from('<I', data, 24)[0]
    pos = 28
    for i in range(numEl):
        ns, ep, es, ne = struct.unpack_from('<IIII', data, pos)
        name = data[pos+16 : pos+16+ns].decode('ascii', errors='replace').rstrip('\x00')
        if name in REPLACE_MAP.values():
            replacements[name] = data[ep : ep+es]
        if ne == 0: break
        pos = ne

    return replacements

def rebuild_pak(hdr, numEl, entries, suc):
    out = bytearray()
    out.extend(hdr)
    out.extend(struct.pack('<I', numEl))

    # 计算新布局: 先写所有entry headers，再写所有data
    # Phase 1: 计算entry headers区域大小
    entry_header_size = 0
    for e in entries:
        entry_header_size += 16 + len(e['name_raw'])

    # Phase 2: 数据起始位置
    data_start = 28 + entry_header_size  # 24(header) + 4(numEl) + headers

    # Phase 3: 计算每个entry的data偏移
    current_data_pos = data_start
    for e in entries:
        e['new_elPos'] = current_data_pos
        e['new_elSize'] = len(e['data'])
        current_data_pos += e['new_elSize']

    # Phase 4: 写entry headers
    for i, e in enumerate(entries):
        if i < len(entries) - 1:
            next_header_pos = 28 + sum(16 + len(entries[j]['name_raw']) for j in range(i+1))
            # Actually, let's compute differently
            pass

    # 重新计算: 先算每个entry header的位置
    header_positions = []
    current = 28  # after hdr(24) + numEl(4)
    for e in entries:
        header_positions.append(current)
        current += 16 + len(e['name_raw'])

    # 数据位置
    data_area_start = current
    current_data = data_area_start
    for e in entries:
        e['new_elPos'] = current_data
        e['new_elSize'] = len(e['data'])
        current_data += len(e['data'])

    # 写entry headers
    for i, e in enumerate(entries):
        ns = len(e['name_raw'])
        ep = e['new_elPos']
        es = e['new_elSize']
        if i < len(entries) - 1:
            ne = header_positions[i + 1]
        else:
            ne = 0
        out.extend(struct.pack('<IIII', ns, ep, es, ne))
        out.extend(e['name_raw'])

    # 写data
    for e in entries:
        out.extend(e['data'])

    # SUC
    out.extend(suc)

    return bytes(out)

def main():
    res767_path = os.path.join(GAME_DIR, 'res767.pak')
    res768_path = os.path.join(GAME_DIR, 'res768.pak')
    backup_path = os.path.join(BACKUP_DIR, 'res767.pak')

    # 解析原pak
    print('解析 res767.pak ...')
    hdr, numEl, entries, suc, orig_data = parse_pak(res767_path)
    print(f'  {len(entries)} 个条目, {len(orig_data)} bytes')

    # 提取替换数据
    print('从 res768.pak 提取替换SMD ...')
    replacements = get_replacement_data(res768_path)
    for name, data in replacements.items():
        print(f'  {name}: {len(data)} bytes')
    assert len(replacements) == 8, f'只找到 {len(replacements)} 个替换文件，需要8个'

    # 替换
    replaced = 0
    for e in entries:
        if e['name'] in REPLACE_MAP:
            new_name = REPLACE_MAP[e['name']]
            if new_name in replacements:
                old_size = len(e['data'])
                e['data'] = replacements[new_name]
                print(f'  替换 {e["name"]}: {old_size} → {len(e["data"])} bytes')
                replaced += 1

    print(f'共替换 {replaced} 个条目')

    if replaced != 8:
        print(f'错误: 期望替换8个，实际替换{replaced}个')
        sys.exit(1)

    # 重建pak
    print('重建 pak ...')
    new_data = rebuild_pak(hdr, numEl, entries, suc)
    print(f'  新pak大小: {len(new_data)} bytes (原: {len(orig_data)}, 增加: {len(new_data)-len(orig_data)})')

    # 先写到桌面
    out_path = os.path.join(BACKUP_DIR, 'res767_patched.pak')
    with open(out_path, 'wb') as f:
        f.write(new_data)
    print(f'已写入: {out_path}')

    # 验证
    print('验证新pak ...')
    hdr2, numEl2, entries2, suc2, _ = parse_pak(out_path)
    print(f'  条目数: {len(entries2)}')
    for e in entries2:
        if '50125461' in e['name'] and e['name'].endswith('.smd'):
            print(f'  {e["name"]}: {e["old_elSize"]} bytes')

    print()
    print(f'验证通过! 请手动复制到游戏目录:')
    print(f'  copy "{out_path}" "{res767_path}"')
    print(f'然后重启游戏测试')

if __name__ == '__main__':
    main()

# patch_res767_add.py — 组合攻击: 往res767.pak新增50125711的SMD/PNG文件
# 用法: py patch_res767_add.py
# 效果: res767.pak中既有原50125461文件，也有新增的50125711文件
# 配合BML hook使用: BML路径改为res767\i50125711_XX.smd → 游戏从res767.pak加载
import struct, sys, os, shutil

sys.stdout.reconfigure(encoding='utf-8')

GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
DESKTOP = r'C:\Users\w\Desktop'

# 从res768.pak提取的文件名列表
ADD_FILES = [
    'i50125711_mt.smd', 'i50125711_ms.smd', 'i50125711_mn.smd', 'i50125711_mf.smd',
    'i50125711_ft.smd', 'i50125711_fs.smd', 'i50125711_fn.smd', 'i50125711_fsc.smd',
    'i50125711.png',
]


def parse_pak(path):
    with open(path, 'rb') as f:
        data = f.read()
    hdr = data[:24]
    numShares = struct.unpack_from('<I', hdr, 20)[0]
    numEl = struct.unpack_from('<I', data, 24)[0]
    suc = data[-16:]

    entries = []
    pos = 28
    for i in range(numEl):
        ns, ep, es, ne = struct.unpack_from('<IIII', data, pos)
        name_raw = data[pos + 16: pos + 16 + ns]
        name = name_raw.decode('ascii', errors='replace').rstrip('\x00')
        entry_data = data[ep: ep + es]
        entries.append({
            'name_raw': name_raw,
            'name': name,
            'data': entry_data,
        })
        if ne == 0:
            break
        pos = ne
    return hdr, entries, suc


def extract_from_pak(pak_path, filenames):
    with open(pak_path, 'rb') as f:
        data = f.read()
    numEl = struct.unpack_from('<I', data, 24)[0]
    pos = 28
    result = {}
    for i in range(numEl):
        ns, ep, es, ne = struct.unpack_from('<IIII', data, pos)
        name = data[pos + 16: pos + 16 + ns].decode('ascii', errors='replace').rstrip('\x00')
        if name in filenames:
            result[name] = data[ep: ep + es]
        if ne == 0:
            break
        pos = ne
    return result


def build_pak(hdr, entries, suc):
    out = bytearray()
    out.extend(hdr)

    numEl = len(entries)
    out.extend(struct.pack('<I', numEl))

    # 计算entry headers区域
    header_sizes = []
    for e in entries:
        header_sizes.append(16 + len(e['name_raw']))

    header_area = sum(header_sizes)
    data_start = 28 + header_area

    # 计算每个entry的data偏移
    current_data = data_start
    for e in entries:
        e['data_offset'] = current_data
        e['data_size'] = len(e['data'])
        current_data += e['data_size']

    # 写entry headers (linked list)
    header_pos = 28
    for i, e in enumerate(entries):
        ns = len(e['name_raw'])
        ep = e['data_offset']
        es = e['data_size']
        ne = (header_pos + 16 + ns) if i < len(entries) - 1 else 0
        out.extend(struct.pack('<IIII', ns, ep, es, ne))
        out.extend(e['name_raw'])
        header_pos += 16 + ns

    # 写data
    for e in entries:
        out.extend(e['data'])

    # SUC
    out.extend(suc)
    return bytes(out)


def main():
    res767_path = os.path.join(GAME_DIR, 'res767.pak')
    res768_path = os.path.join(GAME_DIR, 'res768.pak')
    out_path = os.path.join(DESKTOP, 'res767_combined.pak')

    # 解析原res767
    print('解析 res767.pak ...')
    hdr, entries, suc = parse_pak(res767_path)
    print(f'  {len(entries)} 个条目')

    # 检查是否已有50125711文件
    existing = [e['name'] for e in entries if '50125711' in e['name']]
    if existing:
        print(f'  警告: 已有50125711文件: {existing}')
        print('  先恢复原始res767.pak再运行')
        sys.exit(1)

    # 从res768提取50125711文件
    print(f'从 res768.pak 提取 {len(ADD_FILES)} 个文件 ...')
    add_data = extract_from_pak(res768_path, set(ADD_FILES))
    for name in ADD_FILES:
        if name not in add_data:
            print(f'  错误: 未找到 {name}')
            sys.exit(1)
        print(f'  {name}: {len(add_data[name])} bytes')

    # 新增条目
    for name in ADD_FILES:
        name_bytes = name.encode('ascii') + b'\x00'
        entries.append({
            'name_raw': name_bytes,
            'name': name,
            'data': add_data[name],
        })

    print(f'总条目数: {len(entries)} (新增 {len(ADD_FILES)})')

    # 重建pak
    print('重建 pak ...')
    new_data = build_pak(hdr, entries, suc)
    orig_size = os.path.getsize(res767_path)
    print(f'  原始: {orig_size} bytes')
    print(f'  新文件: {len(new_data)} bytes (+{len(new_data) - orig_size})')

    with open(out_path, 'wb') as f:
        f.write(new_data)
    print(f'已写入: {out_path}')

    # 验证
    print('验证 ...')
    hdr2, entries2, suc2 = parse_pak(out_path)
    print(f'  条目数: {len(entries2)}')
    for e in entries2:
        if '50125711' in e['name']:
            print(f'  [新增] {e["name"]}: {len(e["data"])} bytes')

    print()
    print('验证通过! 部署命令:')
    print(f'  copy "{res767_path}" "{os.path.join(DESKTOP, "res767_backup.pak")}"')
    print(f'  copy "{out_path}" "{res767_path}"')


if __name__ == '__main__':
    main()

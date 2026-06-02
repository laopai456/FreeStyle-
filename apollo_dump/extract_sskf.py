"""
extract_sskf.py — 从pak文件中提取SSKF数据
暴力搜索: 扫描pak文件中的"SSKF"魔数+目标文件名, 提取完整SSKF数据
"""
import sys, os, struct

def find_sskf_in_pak(pak_path, target_name):
    """在pak文件中搜索包含target_name的SSKF数据"""
    with open(pak_path, 'rb') as f:
        data = f.read()

    results = []
    magic = b'SSKF'
    pos = 0

    while True:
        idx = data.find(magic, pos)
        if idx == -1:
            break

        # 检查SSKF头部的文件名
        # +0x00: SSKF (4B)
        # +0x04: version/count (4B)
        # +0x08: filename (null-terminated)
        name_start = idx + 8
        name_end = data.find(b'\x00', name_start, name_start + 64)
        if name_end == -1:
            name_end = name_start + 64

        sskf_name = data[name_start:name_end].decode('ascii', errors='replace')

        # 读SSKF mesh size
        if idx + 4 <= len(data):
            mesh_count = struct.unpack_from('<I', data, idx + 4)[0]
        else:
            mesh_count = 0

        is_target = target_name in sskf_name

        info = {
            'offset': idx,
            'name': sskf_name,
            'mesh_count': mesh_count,
            'is_target': is_target
        }

        if is_target or len(results) < 5:  # 记录前5个+所有匹配
            results.append(info)
            print(f"  offset=0x{idx:08X} name=\"{sskf_name}\" mesh_count={mesh_count}"
                  f"{' ★ TARGET' if is_target else ''}")

        pos = idx + 4

    return results, data


def extract_sskf_data(data, offset, total_size=None):
    """提取从offset开始的SSKF数据"""
    # SSKF header固定512字节, 后面是mesh数据
    header_size = 512

    if total_size:
        sskf_data = data[offset:offset + total_size]
    else:
        # 如果不知道总大小, 取header(512) + 尝试读更多
        # 实际大小需要从pak index获取, 这里用启发式
        sskf_data = data[offset:offset + 512]

    return sskf_data


def main():
    # 目标文件名
    TARGET = 'i50125711_FN.smd'  # 紫色超赛发型 (pak768)

    # 找游戏目录
    import psutil
    game_dir = None
    for p in psutil.process_iter(['name', 'exe']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            game_dir = os.path.dirname(p.info['exe'])
            break

    if not game_dir:
        print('FreeStyle.exe 未运行, 请指定pak文件路径')
        print('用法: python extract_sskf.py <pak_path> [target_name]')
        return

    print(f'游戏目录: {game_dir}')

    # 搜索pak文件
    import glob
    pak_files = glob.glob(os.path.join(game_dir, '**', 'res768.pak'), recursive=True)
    pak_files += glob.glob(os.path.join(game_dir, '..', '**', 'res768.pak'), recursive=True)

    # 也搜索更广泛的路径
    if not pak_files:
        pak_files = glob.glob(os.path.join(game_dir, '**', '*.pak'), recursive=True)
        pak_files = [f for f in pak_files if '768' in f]

    if not pak_files:
        print(f'未找到 res768.pak, 搜索所有pak:')
        all_paks = glob.glob(os.path.join(game_dir, '**', '*.pak'), recursive=True)
        for f in all_paks[:20]:
            print(f'  {f} ({os.path.getsize(f)} bytes)')
        return

    pak_path = pak_files[0]
    print(f'pak文件: {pak_path} ({os.path.getsize(pak_path)} bytes)')
    print(f'搜索: {TARGET}')
    print()

    results, data = find_sskf_in_pak(pak_path, TARGET)

    if not any(r['is_target'] for r in results):
        print(f'\n未找到 {TARGET}')
        print(f'pak中共找到 {len(results)} 个SSKF文件:')
        for r in results:
            print(f'  {r["name"]}')
        return

    # 提取目标SSKF数据
    target = [r for r in results if r['is_target']][0]
    print(f'\n目标找到: offset=0x{target["offset"]:08X} name="{target["name"]}"')

    # 提取header (512字节)
    header_data = extract_sskf_data(data, target['offset'], 512)

    # 保存header
    out_dir = os.path.dirname(os.path.abspath(__file__))
    header_file = os.path.join(out_dir, 'sskf_50125711_header.bin')
    with open(header_file, 'wb') as f:
        f.write(header_data)
    print(f'Header已保存: {header_file} ({len(header_data)} bytes)')

    # 尝试提取mesh数据 (header后面的数据)
    # 需要知道mesh大小。从之前的日志看, 发型的mesh是100864字节
    # 但不同发型大小不同, 我们尝试几种常见大小
    mesh_offset = target['offset'] + 512

    # 搜索下一个SSKF标记来确定mesh结束位置
    next_sskf = data.find(b'SSKF', target['offset'] + 4)
    if next_sskf > mesh_offset:
        mesh_size = next_sskf - mesh_offset
        print(f'Mesh大小 (到下一个SSKF): {mesh_size} bytes')
    else:
        mesh_size = 100864  # 默认发型mesh大小
        print(f'使用默认mesh大小: {mesh_size} bytes')

    mesh_data = data[mesh_offset:mesh_offset + mesh_size]

    mesh_file = os.path.join(out_dir, 'sskf_50125711_mesh.bin')
    with open(mesh_file, 'wb') as f:
        f.write(mesh_data)
    print(f'Mesh已保存: {mesh_file} ({len(mesh_data)} bytes)')

    # 合并保存完整SSKF
    full_file = os.path.join(out_dir, 'sskf_50125711_full.bin')
    with open(full_file, 'wb') as f:
        f.write(header_data)
        f.write(mesh_data)
    print(f'完整SSKF: {full_file} ({512 + len(mesh_data)} bytes)')


if __name__ == '__main__':
    main()

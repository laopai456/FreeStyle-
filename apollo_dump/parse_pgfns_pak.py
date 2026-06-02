"""
parse_pgfns_pak.py — 解析NFGP/PGFN格式pak文件，提取i50125711相关资源

PAK格式 (DFileGPack):
  Header: magic(4)="NFGP" + ver(4) + crypt(4) + res1(4) + res2(4) + numShares(4) = 24 bytes
  + share names array (numShares * [strlen(4) + chars])
  Element array header: numElements(4)
  Elements (linked list):
    nameLen(4) + nextElement(4) + dataPos(4) + dataSize(4) + name(nameLen)

松散文件回退路径: GameDir\Resource\{Group}\{Name}
"""
import struct, os, sys

sys.stdout.reconfigure(encoding='utf-8')

PAK_PATH = r"C:\Program Files (x86)\T2CN\街头篮球\res768.pak"
OUT_DIR = r"C:\tmp\res768_extract"
TARGET = "50125711"


def main():
    with open(PAK_PATH, 'rb') as f:
        data = f.read()

    print(f'pak大小: {len(data)} bytes ({len(data)/1024/1024:.1f} MB)')

    magic = data[:4]
    print(f'magic: {magic} ({magic.hex()}) [LE读取为0x{struct.unpack_from("<I", data, 0)[0]:08X} = "NFGP"]')

    version = struct.unpack_from('<I', data, 4)[0]
    crypt = struct.unpack_from('<I', data, 8)[0]
    print(f'version: {version}, cryptMethod: {crypt}')

    # 头部24字节
    print(f'\n头部:')
    labels = ['magic', 'version', 'cryptMethod', 'res1', 'res2', 'numShares']
    for i in range(6):
        val = struct.unpack_from('<I', data, i*4)[0]
        print(f'  [{i}] {labels[i]:12s} = {val} (0x{val:08X})')

    numShares = struct.unpack_from('<I', data, 20)[0]

    # 跳过share names
    offset = 24
    for _ in range(numShares):
        strSize = struct.unpack_from('<I', data, offset)[0]
        offset += 4 + strSize

    # 读取numElements
    numElements = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    print(f'\nnumElements: {numElements} (at offset {offset-4})')
    print(f'元素起始offset: {offset}')

    # 解析元素 (linked list: 每个entry = nameLen + nextElement + dataPos + dataSize + name)
    entries = []
    for i in range(min(numElements, 2000)):
        if offset + 16 > len(data):
            break

        nameLen = struct.unpack_from('<I', data, offset)[0]
        if nameLen == 0 or nameLen > 256:
            print(f'  [!] 条目#{i}: 异常nameLen={nameLen} at 0x{offset:X}')
            break

        nextElement = struct.unpack_from('<I', data, offset + 4)[0]
        dataPos = struct.unpack_from('<I', data, offset + 8)[0]
        dataSize = struct.unpack_from('<I', data, offset + 12)[0]

        nameStart = offset + 16
        if nameStart + nameLen > len(data):
            print(f'  [!] 条目#{i}: name超出pak范围')
            break

        nameBytes = data[nameStart:nameStart + nameLen]
        try:
            name = nameBytes.decode('ascii')
        except:
            name = nameBytes.decode('ascii', errors='replace')

        entries.append({
            'idx': i,
            'name': name,
            'nameLen': nameLen,
            'nextElement': nextElement,
            'dataPos': dataPos,
            'dataSize': dataSize,
            'rawOffset': offset,
        })

        # 用nextElement跳转（如果是0说明是最后一个）
        if nextElement == 0 and i < numElements - 1:
            # nextElement=0可能是终止标记，尝试顺序读取
            offset = nameStart + nameLen
        else:
            offset = nameStart + nameLen

    print(f'成功解析 {len(entries)} 个条目')

    # 显示前20个条目
    print(f'\n前20个条目:')
    for e in entries[:20]:
        print(f'  #{e["idx"]:3d}: next=0x{e["nextElement"]:06X} pos=0x{e["dataPos"]:06X} '
              f'size={e["dataSize"]:>8d} name="{e["name"]}"')

    # 搜索目标
    targets = [e for e in entries if TARGET in e['name']]
    print(f'\n包含"{TARGET}"的条目: {len(targets)}')
    for e in targets:
        print(f'  #{e["idx"]:3d}: pos=0x{e["dataPos"]:06X} size={e["dataSize"]:>8d} '
              f'name="{e["name"]}"')

    # 提取所有目标
    os.makedirs(OUT_DIR, exist_ok=True)

    for e in targets:
        pos, sz = e['dataPos'], e['dataSize']
        if pos + sz <= len(data) and sz > 0:
            entry_data = data[pos:pos + sz]
            safe_name = e['name'].replace('\\', '_').replace('/', '_')
            out_path = os.path.join(OUT_DIR, safe_name)
            with open(out_path, 'wb') as f:
                f.write(entry_data)
            print(f'\n  提取: {out_path} ({sz} bytes)')

            # 显示头部
            head = entry_data[:min(64, sz)]
            print(f'    hex: {head[:32].hex()}')
            ascii_head = ''.join(chr(b) if 32 <= b < 127 else '.' for b in head[:64])
            print(f'    asc: {ascii_head}')

            # XOR 0xFF解码测试
            decoded = bytes(b ^ 0xFF for b in head)
            dec_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in decoded[:64])
            if any(c.isalpha() for c in dec_ascii[:20]):
                print(f'    xor: {dec_ascii}')

            # 如果是PNG
            if entry_data[:4] == b'\x89PNG':
                print(f'    [PNG图片, 不需要解码]')
            # 如果看起来像XML
            if b'<?xml' in entry_data[:100] or b'<item' in entry_data[:100]:
                print(f'    [明文XML]')
        else:
            print(f'  [!] {e["name"]}: pos+size超出范围 (0x{pos:X}+{sz} > {len(data)})')

    # 扩展名统计
    from collections import Counter
    exts = Counter()
    for e in entries:
        parts = e['name'].rsplit('.', 1)
        if len(parts) == 2:
            exts[parts[1]] += 1
        else:
            exts['(no ext)'] += 1
    print(f'\n扩展名统计:')
    for ext, cnt in exts.most_common(20):
        print(f'  .{ext}: {cnt}')

    # dataPos范围分析
    if entries:
        positions = [e['dataPos'] for e in entries if e['dataPos'] > 0]
        sizes = [e['dataSize'] for e in entries if e['dataSize'] > 0]
        print(f'\ndataPos范围: {min(positions)} - {max(positions)} (pak={len(data)})')
        print(f'dataSize范围: {min(sizes)} - {max(sizes)}')
        total_data = sum(sizes)
        print(f'数据总量: {total_data} bytes ({total_data/1024/1024:.1f} MB)')


if __name__ == '__main__':
    main()

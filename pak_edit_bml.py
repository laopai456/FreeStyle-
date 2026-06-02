"""
pak_edit_bml.py — 修改 item767.pak BML 的 mesh/texture 路径
格式: [NFGP24B][count4B][entries 16B链表]
用法:
  py pak_edit_bml.py <itemcode> <src_pak> <dst_pak> [dst_itemcode]
示例:
  py pak_edit_bml.py 50125461 767 768 50125711
  # 美丽梦想→res768\i50125711_*.smd (紫色超赛发型)
"""
import struct, re, sys, os, shutil

PAK_PATH = r'C:\Program Files (x86)\T2CN\街头篮球\item767.pak'
BACKUP_DIR = r'D:\py\反编译\FreeStyle\cookies'

def read_entries(data):
    count = struct.unpack_from('<I', data, 24)[0]
    entries, pos = [], 28
    for _ in range(count):
        nl = struct.unpack_from('<I', data, pos)[0]
        if nl > 100: break
        doff = struct.unpack_from('<I', data, pos+4)[0]
        ds = struct.unpack_from('<I', data, pos+8)[0]
        ne = struct.unpack_from('<I', data, pos+12)[0]
        nm = data[pos+16:pos+16+nl-1].decode('ascii')
        entries.append((pos, nl, doff, ds, ne, nm))
        if ne == 0 or ne >= len(data): break
        pos = ne
    return entries

def main():
    ic = sys.argv[1] if len(sys.argv) > 1 else '50125461'
    src = sys.argv[2] if len(sys.argv) > 2 else '767'
    dst = sys.argv[3] if len(sys.argv) > 3 else '768'
    dst_ic = sys.argv[4] if len(sys.argv) > 4 else ic

    data = open(PAK_PATH, 'rb').read()
    ents = read_entries(data)
    print(f'PAK: {len(data)}B, {len(ents)} entries')

    shutil.copy2(PAK_PATH, os.path.join(BACKUP_DIR, 'item767_bak_before_edit.pak'))
    print('Backup saved')

    found = False
    for pos, nl, doff, ds, ne, nm in ents:
        if ic not in nm: continue
        found = True
        print(f'\n{nm} @{pos:X} doff={doff:X} sz={ds}')
        raw = data[doff:doff+ds]
        dec = bytes(b^0xFF for b in raw).decode('gbk', errors='replace')

        meshes = re.findall(r'<mesh>([^<]+)</mesh>', dec)
        print('  meshes:')
        new_dec = dec
        for m in meshes:
            new_m = re.sub(r'res\d+', f'res{dst}', m)
            if ic != dst_ic:
                new_m = new_m.replace(ic, dst_ic)
            new_dec = new_dec.replace(m, new_m)
            print(f'    {m} → {new_m}')

        texs = re.findall(r'<texture>([^<]+)</texture>', dec)
        for t in texs:
            new_t = re.sub(r'res\d+', f'res{dst}', t)
            if ic != dst_ic:
                new_t = new_t.replace(ic, dst_ic)
            new_dec = new_dec.replace(t, new_t)
            print(f'    tex: {t} → {new_t}')

        encoded = bytes(b ^ 0xFF for b in new_dec.encode('gbk'))
        if len(encoded) == ds:
            new_data = bytearray(data)
            new_data[doff:doff+ds] = encoded
            with open(PAK_PATH, 'wb') as f:
                f.write(new_data)
            print(f'\nWritten ({ds}B inline replace)')
        else:
            print(f'\nSIZE MISMATCH: {len(encoded)} vs {ds} — abort')
        break

    if not found:
        print(f'Item {ic} not found')

if __name__ == '__main__':
    main()

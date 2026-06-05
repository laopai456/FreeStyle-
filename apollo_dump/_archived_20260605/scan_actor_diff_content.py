# scan_actor_diff_content.py — 对比 Actor 对象内容变化
#
# 用法:
#   1. py scan_actor_v3_deep.py               # 先跑基线，生成 actor_dumps/
#   2. 换装动态发型
#   3. py scan_actor_diff_content.py           # 对比内容变化
#
# 也可以对比两次 dump 目录:
#   py scan_actor_diff_content.py --dir1 actor_dumps --dir2 actor_dumps2

import pymem
import struct
import sys
import os
import json

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'actor_dumps')
BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'actor_baseline_v3.json')


def find_pid():
    import subprocess
    try:
        r = subprocess.run(
            ['tasklist.exe', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle' in line:
                return int(line.split(',')[1].strip('"'))
    except:
        pass
    return None


def diff_bytes(old, new, base=0):
    """逐 dword 对比，返回变化的列表"""
    changes = []
    length = min(len(old), len(new))
    for i in range(0, length - 3, 4):
        ov = struct.unpack_from('<I', old, i)[0]
        nv = struct.unpack_from('<I', new, i)[0]
        if ov != nv:
            changes.append((base + i, ov, nv))
    return changes


def diff_dirs(dir1, dir2):
    """对比两个 dump 目录中的同名文件"""
    files1 = {f: os.path.join(dir1, f) for f in os.listdir(dir1) if f.endswith('.bin')}
    files2 = {f: os.path.join(dir2, f) for f in os.listdir(dir2) if f.endswith('.bin')}

    all_files = sorted(set(files1) | set(files2)

)
    for fname in all_files:
        if fname not in files1:
            print(f'  [NEW in dir2] {fname}')
            continue
        if fname not in files2:
            print(f'  [GONE from dir2] {fname}')
            continue

        with open(files1[fname], 'rb') as f:
            old = f.read()
        with open(files2[fname], 'rb') as f:
            new = f.read()

        changes = diff_bytes(old, new)
        if changes:
            print(f'\n  === {fname}: {len(changes)} changed dwords ===')
            for off, ov, nv in changes[:30]:
                # 尝试解读为 float
                of = struct.pack('<I', ov)
                nf = struct.pack('<I', nv)
                try:
                    ofv = struct.unpack('<f', of)[0]
                    nfv = struct.unpack('<f', nf)[0]
                    float_str = f'  (f: {ofv:.4f} -> {nfv:.4f})'
                except:
                    float_str = ''
                print(f'    +0x{off:03X}: 0x{ov:08X} -> 0x{nv:08X}{float_str}')
            if len(changes) > 30:
                print(f'    ... ({len(changes)-30} more)')
        else:
            print(f'  {fname}: identical')


def main():
    # Mode 1: compare two directories
    if '--dir1' in sys.argv:
        idx1 = sys.argv.index('--dir1')
        idx2 = sys.argv.index('--dir2')
        dir1 = sys.argv[idx1 + 1]
        dir2 = sys.argv[idx2 + 1]
        diff_dirs(dir1, dir2)
        return

    # Mode 2: re-read live objects and compare with saved dumps
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    if not os.path.exists(BASE_FILE):
        print('[!] No baseline. Run scan_actor_v3_deep.py first.')
        sys.exit(1)

    with open(BASE_FILE) as f:
        baseline = json.load(f)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    all_addrs = [(a, 'DS') for a in baseline['ds']] + [(a, 'DD') for a in baseline['dd']]

    total_changes = 0
    changed_objects = 0

    for addr, kind in all_addrs:
        fname = f'{kind.lower()}_{addr:08X}.bin'
        fpath = os.path.join(DUMP_DIR, fname)

        if not os.path.exists(fpath):
            print(f'  [no baseline dump for {fname}]')
            continue

        with open(fpath, 'rb') as f:
            old_data = f.read()

        # Re-read from live process
        try:
            new_data = pm.read_bytes(addr, len(old_data))
        except:
            print(f'  {fname}: UNREADABLE (object freed?)')
            continue

        if not new_data:
            print(f'  {fname}: NULL read')
            continue

        changes = diff_bytes(old_data, new_data)
        if changes:
            changed_objects += 1
            total_changes += len(changes)
            print(f'\n  === {fname}: {len(changes)} changed dwords ===')
            for off, ov, nv in changes[:40]:
                try:
                    ofv = struct.unpack('<f', struct.pack('<I', ov))[0]
                    nfv = struct.unpack('<f', struct.pack('<I', nv))[0]
                    float_str = f'  (f: {ofv:.4f} -> {nfv:.4f})'
                except:
                    float_str = ''
                print(f'    +0x{off:03X}: 0x{ov:08X} -> 0x{nv:08X}{float_str}')
            if len(changes) > 40:
                print(f'    ... ({len(changes)-40} more)')
        else:
            print(f'  {fname}: no change')

    print(f'\n[*] Summary: {changed_objects} objects changed, {total_changes} total dword diffs')

    # Also scan for new DD objects (in case vtable changed)
    DD_VTABLE = 0x0284A9EC
    DS_VTABLE = 0x0284E00C
    TEXT_CEILING = 0x02B00000

    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    MEM_COMMIT = 0x1000
    RW_PROTECT = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ('BaseAddress', ctypes.c_void_p),
            ('AllocationBase', ctypes.c_void_p),
            ('AllocationProtect', wintypes.DWORD),
            ('RegionSize', ctypes.c_size_t),
            ('State', wintypes.DWORD),
            ('Protect', wintypes.DWORD),
            ('Type', wintypes.DWORD),
        ]

    def quick_scan(pm, vtable_val, expected_type8):
        target = struct.pack('<I', vtable_val)
        h = pm.process_handle
        found = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)
        while True:
            ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
            if ret == 0:
                break
            base = mbi.BaseAddress or 0
            size = mbi.RegionSize or 0
            if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0:
                try:
                    data = pm.read_bytes(base, size)
                    if data:
                        off = 0
                        while True:
                            idx = data.find(target, off)
                            if idx < 0:
                                break
                            obj_addr = base + idx
                            if obj_addr >= TEXT_CEILING and idx + 12 <= len(data):
                                type8 = struct.unpack_from('<I', data, idx + 8)[0]
                                if type8 == expected_type8:
                                    found.append(obj_addr)
                            off = idx + 4
                except:
                    pass
            next_addr = base + size
            if next_addr <= addr or next_addr > 0x7FFF0000:
                break
            addr = next_addr
        return found

    dd_now = quick_scan(pm, DD_VTABLE, 1)
    ds_now = quick_scan(pm, DS_VTABLE, 3)

    old_dd_set = set(baseline['dd'])
    old_ds_set = set(baseline['ds'])

    new_dd = sorted(set(dd_now) - old_dd_set)
    new_ds = sorted(set(ds_now) - old_ds_set)
    gone_dd = sorted(old_dd_set - set(dd_now))
    gone_ds = sorted(old_ds_set - set(ds_now))

    print(f'\n[*] Address-level changes:')
    print(f'    DD: {len(baseline["dd"])} -> {len(dd_now)}  (+{len(new_dd)} new, -{len(gone_dd)} gone)')
    print(f'    DS: {len(baseline["ds"])} -> {len(ds_now)}  (+{len(new_ds)} new, -{len(gone_ds)} gone)')

    if new_dd:
        print(f'    New DD: {[hex(a) for a in new_dd]}')
    if new_ds:
        print(f'    New DS: {[hex(a) for a in new_ds]}')

    pm.close_process()


if __name__ == '__main__':
    main()

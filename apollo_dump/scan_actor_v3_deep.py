# scan_actor_v3_deep.py — 深度扫描 + 过滤 + dump
#
# 改进:
#   1. 过滤 .text 段地址 (< 0x02B00000)
#   2. 验证 type8 (DD=1, DS=3)
#   3. 深度 dump 对象字段到 0x600
#   4. 搜索对象内部是否含 ItemCode (50xxxxxx)
#
# 用法:
#   py scan_actor_v3_deep.py           # 扫描 + 深度 dump
#   py scan_actor_v3_deep.py --raw     # 额外输出 hex dump

import pymem
import struct
import sys
import os
import json
import time
import ctypes
from ctypes import wintypes

DD_VTABLE = 0x0284A9EC
DS_VTABLE = 0x0284E00C
TEXT_CEILING = 0x02B00000  # .text + .rdata 大致上限

BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'actor_baseline_v3.json')
DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'actor_dumps')

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


def scan_vtable(pm, vtable_val, expected_type8):
    """扫描堆内存，过滤代码段 + 验证 type8"""
    found = []
    target = struct.pack('<I', vtable_val)
    h = pm.process_handle
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

                        # 过滤 1: 跳过代码段
                        if obj_addr < TEXT_CEILING:
                            off = idx + 4
                            continue

                        # 过滤 2: 读 type8 验证
                        if idx + 12 <= len(data):
                            type8 = struct.unpack_from('<I', data, idx + 8)[0]
                            if type8 != expected_type8:
                                off = idx + 4
                                continue

                        # 过滤 3: 读 vtable[0] 确认是代码指针
                        vfunc0_val = struct.unpack_from('<I', data, idx)[0]
                        # vtable 值本身就是 vtable_val，直接检查 vtable[0]
                        try:
                            vf0 = pm.read_bytes(vtable_val, 4)
                            if not vf0:
                                off = idx + 4
                                continue
                        except:
                            off = idx + 4
                            continue

                        found.append(obj_addr)
                        off = idx + 4
            except:
                pass

        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    return found


def dump_obj(pm, addr, size=0x600):
    """深度 dump 对象"""
    try:
        data = pm.read_bytes(addr, size)
        return data
    except:
        return None


def scan_for_itemcode(data, base_offset=0):
    """在对象数据中搜索 ItemCode 模式 (50xxxxxx)"""
    hits = []
    for i in range(0, len(data) - 3, 4):
        val = struct.unpack_from('<I', data, i)[0]
        if 0x50000000 <= val <= 0x50FFFFFF:
            hits.append((base_offset + i, val))
    return hits


def scan_for_pointers(data, base_offset=0, min_val=0x00400000, max_val=0x7FFFFFFF):
    """搜索合理范围内的指针"""
    ptrs = []
    for i in range(0, len(data) - 3, 4):
        val = struct.unpack_from('<I', data, i)[0]
        if min_val <= val <= max_val:
            ptrs.append((base_offset + i, val))
    return ptrs


def format_hex_line(data, offset, width=16):
    hex_part = ' '.join(f'{b:02X}' for b in data[:width])
    ascii_part = ''.join(chr(b) if 0x20 <= b < 0x7F else '.' for b in data[:width])
    return f'  +0x{offset:03X}: {hex_part:<{width*3}} {ascii_part}'


def print_field(label, data, offset, fmt='<I'):
    val = struct.unpack_from(fmt, data, offset)[0]
    if fmt == '<I':
        print(f'  {label:16s} = 0x{val:08X} ({val})')
    elif fmt == '<f':
        print(f'  {label:16s} = {val:.6f}')
    return val


def analyze_obj(pm, addr, data, label, do_raw=False):
    """分析单个对象"""
    print(f'\n{"="*60}')
    print(f'  {label} @ 0x{addr:08X} (size: {len(data)} bytes)')
    print(f'{"="*60}')

    # 核心字段
    print_field('+0x000 vtable',   data, 0x000)
    print_field('+0x004 f004',     data, 0x004)
    print_field('+0x008 type8',    data, 0x008)
    print_field('+0x00C f00C',     data, 0x00C)
    print_field('+0x010 f010',     data, 0x010)
    print_field('+0x014 f014',     data, 0x014)
    print_field('+0x018 f018',     data, 0x018)
    print_field('+0x020 f020',     data, 0x020)
    print_field('+0x030 f030',     data, 0x030)
    print_field('+0x040 f040',     data, 0x040)
    print_field('+0x050 f050',     data, 0x050)
    print_field('+0x060 f060',     data, 0x060)
    print_field('+0x070 f070',     data, 0x070)
    print_field('+0x074 flags',    data, 0x074)
    print_field('+0x080 f080',     data, 0x080)
    print_field('+0x090 f090',     data, 0x090)
    print_field('+0x0A0 f0A0',     data, 0x0A0)
    print_field('+0x0B0 f0B0',     data, 0x0B0)
    print_field('+0x0C0 f0C0',     data, 0x0C0)

    # 物理区域
    print(f'\n  --- physics block (+0x460 ~ +0x490) ---')
    print_field('+0x460 phys_ptr',  data, 0x460)
    print_field('+0x464 sub_vtable', data, 0x464)
    print_field('+0x468 f468',      data, 0x468)
    print_field('+0x46C index',     data, 0x46C)
    print_field('+0x470 f470',      data, 0x470)
    print_field('+0x474 f474',      data, 0x474)
    print_field('+0x478 f478',      data, 0x478)
    print_field('+0x47C f47C',      data, 0x47C)
    print_field('+0x480 f480',      data, 0x480)
    print_field('+0x484 f484',      data, 0x484)
    print_field('+0x488 f488',      data, 0x488)
    print_field('+0x48C f48C',      data, 0x48C)

    # 搜索 ItemCode
    ic_hits = scan_for_itemcode(data)
    if ic_hits:
        print(f'\n  --- ItemCode candidates ---')
        for off, val in ic_hits:
            print(f'  +0x{off:03X}: {val} (0x{val:08X})')
    else:
        print(f'\n  (no ItemCode pattern found in object body)')

    # 搜索子指针（指向堆的其他对象）
    ptrs = scan_for_pointers(data, min_val=0x00400000, max_val=0x7FFF0000)
    if ptrs:
        # 只显示前 20 个
        print(f'\n  --- pointers ({len(ptrs)} total, showing first 20) ---')
        for off, val in ptrs[:20]:
            # 尝试读指针目标的前 4 字节
            try:
                target_data = pm.read_bytes(val, 4)
                if target_data:
                    tv = struct.unpack_from('<I', target_data, 0)[0]
                    print(f'  +0x{off:03X}: -> 0x{val:08X}  (target[0]=0x{tv:08X})')
                else:
                    print(f'  +0x{off:03X}: -> 0x{val:08X}  (unreadable)')
            except:
                print(f'  +0x{off:03X}: -> 0x{val:08X}')

    # raw hex dump
    if do_raw:
        print(f'\n  --- raw hex (first 0x200) ---')
        for i in range(0, min(0x200, len(data)), 16):
            print(format_hex_line(data[i:i+16], i))


def main():
    do_raw = '--raw' in sys.argv
    do_diff = '--diff' in sys.argv

    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # Scan
    print(f'\n[*] Scanning DDynamicActor (vtable=0x{DD_VTABLE:08X}, type8=1)...')
    dd_objects = scan_vtable(pm, DD_VTABLE, expected_type8=1)
    print(f'    Found: {len(dd_objects)} genuine objects')

    print(f'[*] Scanning DStaticActor (vtable=0x{DS_VTABLE:08X}, type8=3)...')
    ds_objects = scan_vtable(pm, DS_VTABLE, expected_type8=3)
    print(f'    Found: {len(ds_objects)} genuine objects')

    if not do_diff:
        # Deep dump all objects
        for i, addr in enumerate(dd_objects):
            data = dump_obj(pm, addr)
            if data:
                analyze_obj(pm, addr, data, f'DDynamicActor #{i}', do_raw)

        for i, addr in enumerate(ds_objects):
            data = dump_obj(pm, addr)
            if data:
                analyze_obj(pm, addr, data, f'DStaticActor #{i}', do_raw)

        # Save baseline
        baseline = {
            'time': time.strftime('%H:%M:%S'),
            'dd': sorted(dd_objects),
            'ds': sorted(ds_objects),
        }
        with open(BASE_FILE, 'w') as f:
            json.dump(baseline, f)
        print(f'\n[*] Baseline saved ({len(dd_objects)} DD, {len(ds_objects)} DS)')

        # Save raw dumps to files
        os.makedirs(DUMP_DIR, exist_ok=True)
        for i, addr in enumerate(dd_objects):
            data = dump_obj(pm, addr, size=0x800)
            if data:
                path = os.path.join(DUMP_DIR, f'dd_{addr:08X}.bin')
                with open(path, 'wb') as f:
                    f.write(data)

        for i, addr in enumerate(ds_objects):
            data = dump_obj(pm, addr, size=0x800)
            if data:
                path = os.path.join(DUMP_DIR, f'ds_{addr:08X}.bin')
                with open(path, 'wb') as f:
                    f.write(data)

        print(f'[*] Raw dumps saved to {DUMP_DIR}/')

    else:
        # Diff mode
        if not os.path.exists(BASE_FILE):
            print('[!] No baseline. Run without --diff first.')
            sys.exit(1)
        with open(BASE_FILE) as f:
            baseline = json.load(f)

        old_dd = set(baseline['dd'])
        old_ds = set(baseline['ds'])
        new_dd = sorted(set(dd_objects) - old_dd)
        new_ds = sorted(set(ds_objects) - old_ds)
        gone_dd = sorted(old_dd - set(dd_objects))
        gone_ds = sorted(old_ds - set(ds_objects))

        print(f'\n=== DIFF (baseline @ {baseline["time"]}) ===')
        print(f'  DD: {len(baseline["dd"])} -> {len(dd_objects)}')
        print(f'      +{len(new_dd)} new, -{len(gone_dd)} gone')
        print(f'  DS: {len(baseline["ds"])} -> {len(ds_objects)}')
        print(f'      +{len(new_ds)} new, -{len(gone_ds)} gone')

        for addr in new_dd:
            data = dump_obj(pm, addr)
            if data:
                analyze_obj(pm, addr, data, 'NEW DD', do_raw)

        for addr in new_ds:
            data = dump_obj(pm, addr)
            if data:
                analyze_obj(pm, addr, data, 'NEW DS', do_raw)

    pm.close_process()


if __name__ == '__main__':
    main()

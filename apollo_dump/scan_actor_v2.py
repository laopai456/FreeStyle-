# scan_actor_v2.py — 修正版 Actor 对象堆扫描
#
# 修正:
#   1. DS vtable 用工厂函数覆盖后的运行时值 0x0284E00C (非 ctor 的 0x0284E0B4)
#   2. 复用 pymem 的 process handle 做 VirtualQueryEx
#   3. read_bytes 覆盖到 0x490+ 以读物理块字段
#   4. 额外扫描更多保护类型 (PAGE_READONLY 等)
#
# 用法:
#   py scan_actor_v2.py              # baseline 扫描
#   py scan_actor_v2.py --diff       # 对比新对象

import pymem
import struct
import sys
import os
import json
import time
import ctypes
from ctypes import wintypes

# 运行时 vtable (工厂函数最终写入的值)
DD_VTABLE = 0x0284A9EC   # DDynamicActor (ctor 值 = 运行时值)
DS_VTABLE = 0x0284E00C   # DStaticActor (ctor=0x0284E0B4, 工厂覆盖为 0x0284E00C)

BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'actor_baseline_v2.json')

kernel32 = ctypes.windll.kernel32

MEM_COMMIT = 0x1000

RW_PROTECT = {
    0x02,  # PAGE_READONLY
    0x04,  # PAGE_READWRITE
    0x08,  # PAGE_WRITECOPY
    0x20,  # PAGE_EXECUTE_READ
    0x40,  # PAGE_EXECUTE_READWRITE
    0x80,  # PAGE_EXECUTE_WRITECOPY
}

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


def scan_vtable(pm, vtable_val):
    """用 pymem 的 handle 扫描所有 committed 可读内存"""
    found = []
    target = struct.pack('<I', vtable_val)
    h = pm.process_handle

    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)
    regions_scanned = 0

    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0:
            break

        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0

        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0:
            regions_scanned += 1
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(target, off)
                        if idx < 0:
                            break
                        # 验证: 对象大小应 >= 0x600, 读 vtable[0] 确认是有效代码地址
                        obj_addr = base + idx
                        found.append(obj_addr)
                        off = idx + 4
            except:
                pass

        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    print(f'    (scanned {regions_scanned} regions)')
    return found


def read_obj_fields(pm, addr):
    """读对象关键字段, 覆盖到 0x490"""
    try:
        data = pm.read_bytes(addr, 0x490)
        if not data or len(data) < 0x490:
            return None

        fields = {}
        fields['vtable']   = struct.unpack_from('<I', data, 0x000)[0]
        fields['f4']       = struct.unpack_from('<I', data, 0x004)[0]
        fields['type8']    = struct.unpack_from('<I', data, 0x008)[0]
        fields['f0C']      = struct.unpack_from('<I', data, 0x00C)[0]
        fields['f74']      = struct.unpack_from('<I', data, 0x074)[0]
        fields['f460']     = struct.unpack_from('<I', data, 0x460)[0]
        fields['f464']     = struct.unpack_from('<I', data, 0x464)[0]
        fields['f468']     = struct.unpack_from('<I', data, 0x468)[0]
        fields['f46C']     = struct.unpack_from('<I', data, 0x46C)[0]
        fields['f470']     = struct.unpack_from('<I', data, 0x470)[0]
        fields['f474']     = struct.unpack_from('<I', data, 0x474)[0]
        fields['f478']     = struct.unpack_from('<I', data, 0x478)[0]
        fields['f47C']     = struct.unpack_from('<I', data, 0x47C)[0]
        fields['f48C']     = struct.unpack_from('<I', data, 0x48C)[0]

        # 验证 vtable[0] 是合理的代码地址 (应在 .text 范围内)
        vfunc0 = struct.unpack_from('<I', data, 0x000)[0]
        # 这里实际读的是 vtable 本身的值, 需要间接读
        return fields
    except:
        return None


def validate_obj(pm, addr, expected_vtable):
    """验证对象: vtable match + vtable[0] 是合理代码指针"""
    try:
        vtable = struct.unpack_from('<I', pm.read_bytes(addr, 4), 0)[0]
        if vtable != expected_vtable:
            return False
        # 读 vtable[0] (虚函数第一项)
        vfunc0_data = pm.read_bytes(vtable, 4)
        if not vfunc0_data:
            return False
        vfunc0 = struct.unpack_from('<I', vfunc0_data, 0)[0]
        # .text 范围大约 0x00401000 - 0x02A00000
        if not (0x00401000 <= vfunc0 <= 0x02B00000):
            return False
        # 读 vfunc0 处的前几个字节, 确认是代码序言
        prologue = pm.read_bytes(vfunc0, 4)
        if not prologue:
            return False
        # push ebp = 0x55, mov ebp esp = 0x8B 0xEC, sub esp = 0x83
        b0 = prologue[0]
        return b0 in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xE9, 0xCC)
    except:
        return False


def main():
    do_diff = '--diff' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)
    print(f'[+] Process handle: 0x{pm.process_handle:X}')

    # --- Scan DDynamicActor ---
    print(f'\n[*] Scanning DDynamicActor (vtable=0x{DD_VTABLE:08X})...')
    dd_raw = scan_vtable(pm, DD_VTABLE)
    dd_objects = [a for a in dd_raw if validate_obj(pm, a, DD_VTABLE)]
    print(f'    Raw hits: {len(dd_raw)}, Validated: {len(dd_objects)}')

    # --- Scan DStaticActor ---
    print(f'\n[*] Scanning DStaticActor (vtable=0x{DS_VTABLE:08X})...')
    ds_raw = scan_vtable(pm, DS_VTABLE)
    ds_objects = [a for a in ds_raw if validate_obj(pm, a, DS_VTABLE)]
    print(f'    Raw hits: {len(ds_raw)}, Validated: {len(ds_objects)}')

    # --- 旧 vtable 也扫一次做对比 ---
    print(f'\n[*] Bonus: DStaticActor ctor vtable (0x0284E0B4)...')
    ds_ctor_raw = scan_vtable(pm, 0x0284E0B4)
    ds_ctor = [a for a in ds_ctor_raw if validate_obj(pm, a, 0x0284E0B4)]
    print(f'    Raw hits: {len(ds_ctor_raw)}, Validated: {len(ds_ctor)}')

    if not do_diff:
        baseline = {
            'time': time.strftime('%H:%M:%S'),
            'dd': sorted(dd_objects),
            'ds': sorted(ds_objects),
            'ds_ctor': sorted(ds_ctor),
        }
        with open(BASE_FILE, 'w') as f:
            json.dump(baseline, f)
        print(f'\n[*] Baseline saved to {BASE_FILE}')

        def show_objs(label, objs, vtable):
            print(f'\n  === {label} ({len(objs)} objects) ===')
            for addr in objs[:20]:
                fields = read_obj_fields(pm, addr)
                if fields:
                    print(f'  @ 0x{addr:08X}: type8={fields["type8"]} '
                          f'f74=0x{fields["f74"]:08X} '
                          f'f460=0x{fields["f460"]:08X} '
                          f'f464=0x{fields["f464"]:08X} '
                          f'f46C=0x{fields["f46C"]:08X}')
            if len(objs) > 20:
                print(f'  ... (+{len(objs)-20} more)')

        show_objs('DDynamicActor', dd_objects, DD_VTABLE)
        show_objs('DStaticActor (runtime)', ds_objects, DS_VTABLE)
        show_objs('DStaticActor (ctor)', ds_ctor, 0x0284E0B4)

    else:
        if not os.path.exists(BASE_FILE):
            print('[!] No baseline. Run without --diff first.')
            sys.exit(1)
        with open(BASE_FILE) as f:
            baseline = json.load(f)

        old_dd = set(baseline['dd'])
        old_ds = set(baseline['ds'])
        new_dd = sorted(set(dd_objects) - old_dd)
        new_ds = sorted(set(ds_objects) - old_ds)

        print(f'\n=== DIFF (baseline @ {baseline["time"]}) ===')
        print(f'  DD: {len(baseline["dd"])} -> {len(dd_objects)} ({len(new_dd)} new)')
        print(f'  DS: {len(baseline["ds"])} -> {len(ds_objects)} ({len(new_ds)} new)')

        for addr in new_dd[:10]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  NEW DD @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')

        for addr in new_ds[:10]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  NEW DS @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')

    pm.close_process()


if __name__ == '__main__':
    main()

# scan_actor_objects.py — Pymem 扫描堆中的 DDynamicActor/DStaticActor 对象
#
# 原理:
#   对象的第一个 dword 是 vtable 指针
#   DDynamicActor vtable = 0x0284A9EC
#   DStaticActor vtable = 0x0284E0B4
#   扫描整个进程内存找到这些对象
#
# 用法:
#   1. 进入游戏大厅
#   2. py scan_actor_objects.py          # 记录 baseline
#   3. 装备一个发型
#   4. py scan_actor_objects.py --diff   # 显示新增对象

import pymem
import pymem.process
import struct
import sys
import os
import json
import time
import subprocess

DD_VTABLE = 0x0284A9EC
DS_VTABLE = 0x0284E0B4
BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'actor_baseline.json')


def find_pid():
    try:
        r = subprocess.run(['tasklist.exe','/fi','IMAGENAME eq FreeStyle.exe','/fo','csv','/nh'],
                          capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle' in line:
                return int(line.split(',')[1].strip('"'))
    except: pass
    return None


def scan_vtable(pm, vtable_val):
    """扫描进程内存找到 vtable 开头的对象"""
    found = []
    target = struct.pack('<I', vtable_val)

    # 枚举内存区域
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    pid = pm.process_id
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    # 用 VirtualQueryEx 枚举
    MEM_COMMIT = 0x1000
    PAGE_READWRITE = 0x04
    PAGE_WRITECOPY = 0x08
    PAGE_EXECUTE_READWRITE = 0x40
    PAGE_EXECUTE_WRITECOPY = 0x80

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

    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return found

    try:
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while True:
            ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
            if ret == 0 or mbi.BaseAddress is None:
                break

            if (mbi.State == MEM_COMMIT and
                mbi.Protect in (PAGE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY)):

                base = mbi.BaseAddress or 0
                size = mbi.RegionSize or 0
                if base == 0 or size == 0:
                    pass
                else:
                    try:
                        data = pm.read_bytes(base, size)
                        if data:
                            off = 0
                            while True:
                                idx = data.find(target, off)
                                if idx < 0: break
                                obj_addr = base + idx
                                found.append(obj_addr)
                                off = idx + 4
                    except:
                        pass

            next_addr = (mbi.BaseAddress or 0) + (mbi.RegionSize or 0)
            if next_addr <= addr or next_addr > 0x7FFF0000:
                break
            addr = next_addr
    finally:
        kernel32.CloseHandle(h)

    return found


def read_obj_fields(pm, addr):
    """读对象关键字段"""
    try:
        # offset 0: vtable (4)
        # offset 4: ??
        # offset 8: type field (from DStaticActor ctor: mov [edx+8], 3)
        data = pm.read_bytes(addr, 0x100)
        if not data: return None

        fields = {}
        fields['vtable'] = struct.unpack_from('<I', data, 0)[0]
        fields['f4'] = struct.unpack_from('<I', data, 4)[0]
        fields['type8'] = struct.unpack_from('<I', data, 8)[0]
        fields['f0C'] = struct.unpack_from('<I', data, 0xC)[0]
        fields['f10'] = struct.unpack_from('<I', data, 0x10)[0]
        fields['f74'] = struct.unpack_from('<I', data, 0x74)[0]
        # DStaticActor: [ecx+0x460]=0, DDynamicActor: DynamicInit sets [ecx+0x460]
        fields['f460'] = struct.unpack_from('<I', data, 0x460)[0] if len(data) > 0x464 else 0
        return fields
    except:
        return None


def main():
    do_diff = '--diff' in sys.argv

    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    print(f'[*] Scanning DDynamicActor objects (vtable=0x{DD_VTABLE:08X})...')
    dd_objects = scan_vtable(pm, DD_VTABLE)
    print(f'    Found: {len(dd_objects)}')

    print(f'[*] Scanning DStaticActor objects (vtable=0x{DS_VTABLE:08X})...')
    ds_objects = scan_vtable(pm, DS_VTABLE)
    print(f'    Found: {len(ds_objects)}')

    if not do_diff:
        # 保存 baseline
        baseline = {
            'time': time.strftime('%H:%M:%S'),
            'dd': sorted(dd_objects),
            'ds': sorted(ds_objects),
        }
        with open(BASE_FILE, 'w') as f:
            json.dump(baseline, f)
        print(f'[*] Baseline saved ({len(dd_objects)} DD, {len(ds_objects)} DS)')

        # 显示找到的对象
        for addr in dd_objects[:5]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  DD @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')
        if len(dd_objects) > 5:
            print(f'  ... (+{len(dd_objects)-5} more)')

        for addr in ds_objects[:5]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  DS @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')
        if len(ds_objects) > 5:
            print(f'  ... (+{len(ds_objects)-5} more)')
    else:
        # diff mode
        if not os.path.exists(BASE_FILE):
            print('[!] No baseline found. Run without --diff first.')
            sys.exit(1)

        with open(BASE_FILE) as f:
            baseline = json.load(f)

        old_dd = set(baseline['dd'])
        old_ds = set(baseline['ds'])
        new_dd = set(dd_objects) - old_dd
        new_ds = set(ds_objects) - old_ds

        print(f'\n=== DIFF (baseline @ {baseline["time"]}) ===')
        print(f'  DD: {len(baseline["dd"])} -> {len(dd_objects)} ({len(new_dd)} new)')
        print(f'  DS: {len(baseline["ds"])} -> {len(ds_objects)} ({len(new_ds)} new)')

        for addr in sorted(new_dd)[:10]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  NEW DD @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')

        for addr in sorted(new_ds)[:10]:
            fields = read_obj_fields(pm, addr)
            if fields:
                print(f'  NEW DS @ 0x{addr:08X}: type8={fields["type8"]} f460=0x{fields["f460"]:08X}')

    pm.close_process()


if __name__ == '__main__':
    main()

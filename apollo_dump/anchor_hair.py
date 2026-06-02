# anchor_hair.py — 以 美丽梦想发型(50125461) 为锚点定位 DS 对象
#
# 扫描 50125461 在堆中的位置, 对每个命中:
#   1. 读前后 0x400 字节
#   2. 检查是否包含 8 个 DS 对象地址之一
#   3. 向前搜索 vtable 定位父对象起始
#   4. 如果是描述符(+0x000=0x027FCEA0), 记录

import pymem
import struct
import sys
import ctypes
from ctypes import wintypes

TARGET_IC = 50125461
DESC_VTABLE = 0x027FCEA0
DS_VTABLE = 0x0284E00C
TEXT_CEILING = 0x02B00000

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

def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)
    h = pm.process_handle

    # Step 1: 扫 DS 对象
    print('[*] Scanning DS objects...')
    ds_target = struct.pack('<I', DS_VTABLE)
    ds_objects = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)
    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0: break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(ds_target, off)
                        if idx < 0: break
                        obj_addr = base + idx
                        if idx + 12 <= len(data):
                            type8 = struct.unpack_from('<I', data, idx + 8)[0]
                            if type8 == 3:
                                ds_objects.append(obj_addr)
                        off = idx + 4
            except: pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000: break
        addr = next_addr
    ds_set = set(ds_objects)
    ds_bytes = {a: struct.pack('<I', a) for a in ds_objects}
    print(f'    DS objects: {[hex(a) for a in sorted(ds_objects)]}')

    # Step 2: 扫 ItemCode 50125461
    ic_pattern = struct.pack('<i', TARGET_IC)
    print(f'\n[*] Scanning ItemCode={TARGET_IC} (0x{TARGET_IC:X})...')
    ic_hits = []
    addr = 0
    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0: break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(ic_pattern, off)
                        if idx < 0: break
                        ic_hits.append(base + idx)
                        off = idx + 4
            except: pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000: break
        addr = next_addr
    print(f'    Found {len(ic_hits)} hits')

    # Step 3: 对每个 ItemCode hit, 检查周围
    print(f'\n[*] Checking vicinity of each ItemCode hit...')
    for ic_addr in sorted(ic_hits):
        # 读前后 0x400
        read_start = max(ic_addr - 0x400, TEXT_CEILING)
        read_size = 0x800
        try:
            region = pm.read_bytes(read_start, read_size)
        except:
            continue
        if not region:
            continue

        ic_off = ic_addr - read_start  # offset within region

        # 检查是否有 DS 对象指针在附近
        ds_found = []
        for ds_a, ds_pat in ds_bytes.items():
            idx = region.find(ds_pat)
            if idx >= 0:
                ds_found.append((idx, ds_a))

        # 向前找 vtable
        vtable_found = []
        for backtrack in range(0, min(ic_off, 0x400), 4):
            val = struct.unpack_from('<I', region, ic_off - backtrack)[0]
            if 0x00400000 <= val <= 0x02B00000 and (val & 3) == 0:
                # 检查 vtable[0] 是否像代码
                try:
                    vf0 = pm.read_bytes(val, 1)
                    if vf0 and vf0[0] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xE9):
                        vtable_found.append((ic_off - backtrack, val))
                except:
                    pass

        is_desc = False
        parent_vt = None
        for vt_off, vt_val in vtable_found:
            if vt_val == DESC_VTABLE:
                is_desc = True
                parent_vt = vt_val
                parent_start = read_start + vt_off
                break

        if ds_found or is_desc:
            print(f'\n  IC @ 0x{ic_addr:08X}:')
            if is_desc:
                print(f'    descriptor @ 0x{parent_start:08X}')
                # 读描述符完整字段
                for off in [0x000, 0x004, 0x040, 0x04C, 0x058, 0x060, 0x064, 0x080, 0x0F0, 0x0F4, 0x0F8, 0x100, 0x104]:
                    val = struct.unpack_from('<I', region, vt_off + off)[0] if vt_off + off + 4 <= len(region) else 0
                    print(f'    +0x{off:03X} = 0x{val:08X}')
                    # 检查这个值是否是 DS 对象地址
                    if val in ds_set:
                        print(f'           ^^^ THIS IS A DS OBJECT!')

            if ds_found:
                for ds_off, ds_a in ds_found:
                    off_from_ic = ds_off - ic_off
                    print(f'    DS @ 0x{ds_a:08X} (offset from IC: {off_from_ic:+d})')

    # Step 4: 更宽范围 — 在 ItemCode 附近 0x1000 内搜 DS 指针
    print(f'\n[*] Extended search (0x1000 range)...')
    for ic_addr in sorted(ic_hits):
        read_start = max(ic_addr - 0x800, TEXT_CEILING)
        read_size = 0x1000
        try:
            region = pm.read_bytes(read_start, read_size)
        except:
            continue
        ic_off = ic_addr - read_start

        for ds_a, ds_pat in ds_bytes.items():
            idx = region.find(ds_pat)
            if idx >= 0:
                off_from_ic = idx - ic_off
                print(f'  IC @ 0x{ic_addr:08X} +{off_from_ic:+d} -> DS @ 0x{ds_a:08X}')
                # 显示这个区域的关键数据
                context_start = max(0, idx - 0x20)
                context_end = min(len(region), idx + 0x30)
                for i in range(context_start, context_end, 4):
                    val = struct.unpack_from('<I', region, i)[0]
                    marker = ' <--- DS ptr' if i == idx else ''
                    abs_a = read_start + i
                    off_label = i - ic_off
                    print(f'    [{off_label:+5d}] 0x{abs_a:08X}: 0x{val:08X}{marker}')

    # Step 5: 从 DS 对象出发, 在更大范围(0x2000)搜 ItemCode
    print(f'\n[*] Reverse: DS object surroundings -> ItemCode...')
    for ds_addr in sorted(ds_objects):
        # DS 对象是独立分配, 读前后 0x1000 看是否有相关结构
        # 先看 DS 对象所在整个内存区域
        alloc_base = None
        alloc_size = None
        a = 0
        while True:
            ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(a), ctypes.byref(mbi), mbi_size)
            if ret == 0: break
            b = mbi.BaseAddress or 0
            s = mbi.RegionSize or 0
            if b <= ds_addr < b + s:
                alloc_base = b
                alloc_size = s
                break
            next_a = b + s
            if next_a <= a or next_a > 0x7FFF0000: break
            a = next_a

        if alloc_base is None:
            continue

        ds_off_in_region = ds_addr - alloc_base
        f46c = struct.unpack_from('<I', pm.read_bytes(ds_addr + 0x46C, 4), 0)[0]

        # 在同一区域内搜 ItemCode
        try:
            region_data = pm.read_bytes(alloc_base, min(alloc_size, 0x10000))
        except:
            continue

        ic_in_region = []
        for i in range(0, len(region_data) - 3, 4):
            v = struct.unpack_from('<I', region_data, i)[0]
            if v == TARGET_IC:
                off_from_ds = i - ds_off_in_region
                ic_in_region.append((i, off_from_ds))

        if ic_in_region:
            print(f'  DS @ 0x{ds_addr:08X} (idx={f46c}) in region 0x{alloc_base:08X}+0x{alloc_size:X}:')
            for i, off in ic_in_region:
                abs_a = alloc_base + i
                print(f'    IC={TARGET_IC} @ 0x{abs_a:08X} (offset from DS: {off:+d})')

    pm.close_process()

if __name__ == '__main__':
    main()

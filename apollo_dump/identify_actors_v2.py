# identify_actors_v2.py — 反向追踪: 从 DS 对象找到 ItemCode
#
# 策略:
#   1. 扫描所有描述符 (vtable=0x027FCEA0), 读 ItemCode(+0x060)
#   2. 对每个描述符, 搜索其内部是否有指针指向我们的 8 个 DS 对象
#   3. 如果没直接关联, 就反向搜: 在整个堆中搜 DS 对象地址, 找父结构
#
# 用法:
#   py identify_actors_v2.py

import pymem
import struct
import sys
import os
import ctypes
from ctypes import wintypes

DS_VTABLE = 0x0284E00C
DESC_VTABLE = 0x027FCEA0   # 描述符 vtable
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


def read_mem(pm, addr, size):
    try:
        return pm.read_bytes(addr, size)
    except:
        return None


def read_dword(pm, addr):
    d = read_mem(pm, addr, 4)
    return struct.unpack_from('<I', d, 0)[0] if d else None


def scan_heap(pm, target_bytes):
    """扫描堆内存找目标字节序列"""
    hits = []
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
            if base >= TEXT_CEILING and size <= 0x1000000:
                try:
                    data = pm.read_bytes(base, size)
                    if data:
                        off = 0
                        while True:
                            idx = data.find(target_bytes, off)
                            if idx < 0:
                                break
                            hits.append(base + idx)
                            off = idx + 4
                except:
                    pass

        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr
    return hits


def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # Step 1: 扫描 DS 对象
    print('[*] Step 1: Scanning DStaticActor objects...')
    ds_target = struct.pack('<I', DS_VTABLE)
    ds_hits = scan_heap(pm, ds_target)
    # Filter by type8=3
    ds_objects = []
    for addr in ds_hits:
        type8 = read_dword(pm, addr + 8)
        if type8 == 3:
            ds_objects.append(addr)
    print(f'    Found {len(ds_objects)} DS objects: {[hex(a) for a in sorted(ds_objects)]}')

    # Step 2: 扫描描述符
    print('\n[*] Step 2: Scanning descriptors (vtable=0x027FCEA0)...')
    desc_target = struct.pack('<I', DESC_VTABLE)
    desc_hits = scan_heap(pm, desc_target)
    # Filter: check if +0x060 has a reasonable ItemCode
    descriptors = []
    for addr in desc_hits:
        ic = read_dword(pm, addr + 0x060)
        if ic and ic > 0:
            descriptors.append((addr, ic))
    print(f'    Found {len(descriptors)} descriptors')

    # Group descriptors by ItemCode
    by_ic = {}
    for addr, ic in descriptors:
        by_ic.setdefault(ic, []).append(addr)

    print(f'    Unique ItemCodes: {len(by_ic)}')
    # Show hair-related items (category 3)
    hair_ics = []
    for ic, addrs in sorted(by_ic.items()):
        # Check subtype at +0x058
        for a in addrs:
            sub = read_dword(pm, a + 0x058)
            cat = read_dword(pm, a + 0x04C)
            if cat == 3:  # hair category
                hair_ics.append((ic, a, sub))
    if hair_ics:
        print(f'\n    Hair descriptors (category=3):')
        for ic, a, sub in hair_ics:
            print(f'      ItemCode={ic} desc@0x{a:08X} subtype={sub}')

    # Step 3: 反向搜索 — 对每个 DS 对象, 在堆中搜索指向它的指针
    print(f'\n[*] Step 3: Reverse pointer scan (who points to DS objects?)')
    ds_set = set(ds_objects)

    for ds_addr in sorted(ds_objects):
        f46c = read_dword(pm, ds_addr + 0x46C) or '?'
        print(f'\n  --- DS @ 0x{ds_addr:08X} (idx={f46c}) ---')

        ptr_bytes = struct.pack('<I', ds_addr)
        ptr_hits = scan_heap(pm, ptr_bytes)

        # 过滤掉代码段和自身
        ptr_hits = [h for h in ptr_hits if h >= TEXT_CEILING and h != ds_addr]

        print(f'    {len(ptr_hits)} pointers to this object')

        for hit_addr in ptr_hits[:30]:
            # 检查这个位置附近是否有描述符 vtable
            # 向前搜索最多 0x100 字节
            found_desc = False
            for backtrack in range(0, 0x200, 4):
                check_addr = hit_addr - backtrack
                if check_addr < TEXT_CEILING:
                    break
                val = read_dword(pm, check_addr)
                if val == DESC_VTABLE:
                    # 找到描述符!
                    ic = read_dword(pm, check_addr + 0x060)
                    sub = read_dword(pm, check_addr + 0x058)
                    cat = read_dword(pm, check_addr + 0x04C)
                    print(f'    -> DESC @ 0x{check_addr:08X} (back +0x{backtrack:02X}) '
                          f'ItemCode={ic} cat={cat} subtype={sub}')
                    found_desc = True
                    break

            if not found_desc:
                # 读一下 hit 位置前后的 dword 来判断结构
                context_before = read_mem(pm, max(hit_addr - 0x20, TEXT_CEILING), 0x40)
                if context_before:
                    # 检查前后的值
                    ptr_off_in_ctx = min(0x20, hit_addr - max(hit_addr - 0x20, TEXT_CEILING))
                    dwords_before = []
                    for i in range(0, len(context_before), 4):
                        dwords_before.append(struct.unpack_from('<I', context_before, i)[0])

                    # 检查是否有 ItemCode (50xxxxxx) 在附近
                    nearby_ic = None
                    for i, v in enumerate(dwords_before):
                        if 0x50000000 <= v <= 0x50FFFFFF:
                            nearby_ic = v

                    tag = ''
                    if nearby_ic:
                        tag = f'  *** nearby ItemCode={nearby_ic} ***'

                    # 简洁输出
                    idx_in_ds = hit_addr - ds_addr
                    if -0x200 < idx_in_ds < 0:
                        continue  # 自引用, 跳过

                    print(f'    -> ptr @ 0x{hit_addr:08X}{tag}')
                    # 显示前后 4 个 dword
                    ctx_str = ' '.join(f'{v:08X}' for v in dwords_before[:8])
                    print(f'       context: {ctx_str}')

    # Step 4: 也试正向 — 从描述符找 DS 对象
    print(f'\n[*] Step 4: Forward scan (descriptor -> DS object)')
    for ds_addr in sorted(ds_objects):
        # 在描述符数据中搜索 DS 对象地址
        ds_ptr_bytes = struct.pack('<I', ds_addr)

        for desc_addr, ic in descriptors:
            desc_data = read_mem(pm, desc_addr, 0x200)
            if desc_data and ds_ptr_bytes in desc_data:
                sub = read_dword(pm, desc_addr + 0x058)
                cat = read_dword(pm, desc_addr + 0x04C)
                f46c = read_dword(pm, ds_addr + 0x46C)
                print(f'  DS @ 0x{ds_addr:08X} (idx={f46c}) <-> Desc @ 0x{desc_addr:08X} '
                      f'ItemCode={ic} cat={cat} subtype={sub}')

    pm.close_process()


if __name__ == '__main__':
    main()

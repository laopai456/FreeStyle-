# link_ds_to_item.py — 反向关联 DS 对象到 ItemCode
#
# 策略:
#   对每个 DS 对象地址, 在堆中搜索该地址(作为指针值),
#   找到持有者结构后, 在持有者内搜索 ItemCode (50xxxxxx/25xxx 等)
#   用 batch scan 加速: 一次读一大块内存, 同时搜多个 DS 地址

import pymem
import struct
import sys
import os
import ctypes
from ctypes import wintypes

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

    # Step 1: 扫 DS 对象
    print('[*] Scanning DS objects...')
    ds_target = struct.pack('<I', DS_VTABLE)
    ds_objects = []
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
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(ds_target, off)
                        if idx < 0:
                            break
                        obj_addr = base + idx
                        if idx + 12 <= len(data):
                            type8 = struct.unpack_from('<I', data, idx + 8)[0]
                            if type8 == 3:
                                ds_objects.append(obj_addr)
                        off = idx + 4
            except:
                pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    ds_set = set(ds_objects)
    ds_bytes = {a: struct.pack('<I', a) for a in ds_objects}
    print(f'    Found {len(ds_objects)}: {[hex(a) for a in sorted(ds_objects)]}')

    # Step 2: 全堆搜索, 同时搜所有 DS 对象地址
    print(f'\n[*] Scanning heap for DS object pointers (batch mode)...')

    # results: ds_addr -> list of (hit_addr, context_dwords)
    ds_refs = {a: [] for a in ds_objects}
    regions = 0
    addr = 0
    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING and size <= 0x1000000:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    regions += 1
                    for ds_addr, ds_pat in ds_bytes.items():
                        off = 0
                        while True:
                            idx = data.find(ds_pat, off)
                            if idx < 0:
                                break
                            hit = base + idx
                            # 排除自引用 (DS 对象内部指向自己的)
                            if hit not in ds_set:
                                # 检查前后 0x20 的内容
                                ctx_start = max(0, idx - 0x20)
                                ctx_end = min(len(data), idx + 0x24)
                                ctx = data[ctx_start:ctx_end]
                                ds_refs[ds_addr].append((hit, ctx, base, size))
                            off = idx + 4
            except:
                pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr
    print(f'    Scanned {regions} regions')

    # Step 3: 分析每个 DS 对象的引用
    print(f'\n[*] Analyzing references...')
    for ds_addr in sorted(ds_objects):
        f46c_data = pm.read_bytes(ds_addr + 0x46C, 4)
        f46c = struct.unpack_from('<I', f46c_data, 0)[0] if f46c_data else 0
        refs = ds_refs[ds_addr]
        print(f'\n  DS @ 0x{ds_addr:08X} (idx={f46c}): {len(refs)} external refs')

        for hit, ctx, region_base, region_size in refs:
            # 在 hit 附近大范围搜索 ItemCode
            # 读 hit 前后 0x200
            read_start = max(hit - 0x200, region_base)
            read_size = min(0x400, region_base + region_size - read_start)
            try:
                region_data = pm.read_bytes(read_start, read_size)
            except:
                continue

            hit_off = hit - read_start  # offset of our DS pointer within region_data

            # 搜索 ItemCode 模式
            item_codes = []
            for i in range(0, len(region_data) - 3, 4):
                v = struct.unpack_from('<I', region_data, i)[0]
                # 常见 ItemCode 范围: 25xxx, 501xxxxx, 504xxxxx, 505xxxxx, 511xxxxx 等
                if (25000 <= v <= 99999) or (50000000 <= v <= 59999999):
                    abs_addr = read_start + i
                    item_codes.append((abs_addr, v))

            # 也搜索 vtable 特征来识别父对象
            parent_vtables = []
            for i in range(0, len(region_data) - 3, 4):
                v = struct.unpack_from('<I', region_data, i)[0]
                if 0x00400000 <= v <= 0x02B00000 and (v & 3) == 0:
                    # 可能是 vtable, 检查 vtable[0] 是否像代码
                    try:
                        vf0 = pm.read_bytes(v, 1)
                        if vf0 and vf0[0] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0xE9):
                            abs_addr = read_start + i
                            parent_vtables.append((abs_addr, v))
                    except:
                        pass

            if item_codes or parent_vtables:
                print(f'    ref @ 0x{hit:08X}:')
                if item_codes:
                    for ic_addr, ic in item_codes[:10]:
                        off_from_ptr = ic_addr - hit
                        print(f'      ItemCode={ic} @ 0x{ic_addr:08X} (offset from ptr: {off_from_ptr:+d})')
                if parent_vtables:
                    for pv_addr, pv in parent_vtables[:5]:
                        off_from_ptr = pv_addr - hit
                        print(f'      vtable=0x{pv:08X} @ 0x{pv_addr:08X} (offset from ptr: {off_from_ptr:+d})')
            else:
                # 没找到 ItemCode, 但仍显示基本信息
                pass

    # Step 4: 如果上面没找到, 尝试从 DS 对象自身的字段跟踪
    print(f'\n[*] Chasing DS object internal pointers (depth 2)...')
    for ds_addr in sorted(ds_objects):
        ds_data = pm.read_bytes(ds_addr, 0x600)
        if not ds_data:
            continue
        f46c = struct.unpack_from('<I', ds_data, 0x46C)[0]

        # 对 DS 对象内的每个指针, 读目标并搜 ItemCode
        for i in range(0, len(ds_data) - 3, 4):
            ptr = struct.unpack_from('<I', ds_data, i)[0]
            if not (0x01000000 <= ptr <= 0x7FFF0000):
                continue

            try:
                target_data = pm.read_bytes(ptr, 0x200)
            except:
                continue
            if not target_data:
                continue

            # 搜 ItemCode
            for j in range(0, len(target_data) - 3, 4):
                v = struct.unpack_from('<I', target_data, j)[0]
                if (25000 <= v <= 99999) or (50000000 <= v <= 59999999):
                    print(f'  DS @ 0x{ds_addr:08X} (idx={f46c}): '
                          f'+0x{i:03X} -> 0x{ptr:08X} +0x{j:03X}: ItemCode={v}')

            # 二级: target 内的指针再跟一层
            for j in range(0, min(len(target_data), 0x80), 4):
                ptr2 = struct.unpack_from('<I', target_data, j)[0]
                if not (0x01000000 <= ptr2 <= 0x7FFF0000):
                    continue
                try:
                    target2_data = pm.read_bytes(ptr2, 0x100)
                except:
                    continue
                if not target2_data:
                    continue
                for k in range(0, len(target2_data) - 3, 4):
                    v = struct.unpack_from('<I', target2_data, k)[0]
                    if (25000 <= v <= 99999) or (50000000 <= v <= 59999999):
                        print(f'  DS @ 0x{ds_addr:08X} (idx={f46c}): '
                              f'+0x{i:03X} -> 0x{ptr:08X} +0x{j:03X} -> 0x{ptr2:08X} +0x{k:03X}: ItemCode={v}')

    pm.close_process()


if __name__ == '__main__':
    main()

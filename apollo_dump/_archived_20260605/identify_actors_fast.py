# identify_actors_fast.py — 快速从描述符正向关联 DS 对象
#
# 已知 6 个发型描述符地址, 读描述符内所有指针,
# 检查是否指向 8 个 DS 对象之一

import pymem
import struct
import sys

DS_VTABLE = 0x0284E00C
DESC_VTABLE = 0x027FCEA0
TEXT_CEILING = 0x02B00000


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

    # Step 1: 扫 DS 对象 (和之前一样)
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
    print(f'[+] DS objects ({len(ds_objects)}): {[hex(a) for a in sorted(ds_objects)]}')

    # Step 2: 已知描述符地址, 读完整内容
    hair_descs = [
        (50125691, 0x0A161C98, 0, '黑金热血青春发型'),
        (50125701, 0x0A162070, 1, '?'),
        (50125711, 0x0A162448, 2, '动态发型'),
        (50125721, 0x0A162820, 3, '粉色超赛3'),
        (50421151, 0x0A162BF8, 4, '?'),
        (50421161, 0x0A162FD0, 5, '?'),
    ]

    print(f'\n[*] Checking hair descriptors for DS object pointers...')

    for ic, desc_addr, sub, name in hair_descs:
        desc_data = pm.read_bytes(desc_addr, 0x200)
        if not desc_data:
            print(f'  IC={ic}: unreadable')
            continue

        # 在描述符内搜索 DS 对象地址
        found_ds = []
        for i in range(0, len(desc_data) - 3, 4):
            val = struct.unpack_from('<I', desc_data, i)[0]
            if val in ds_set:
                found_ds.append((i, val))

        # 也搜索所有堆指针并跟踪一级
        all_ptrs = []
        for i in range(0, len(desc_data) - 3, 4):
            val = struct.unpack_from('<I', desc_data, i)[0]
            if 0x01000000 <= val <= 0x7FFF0000:
                all_ptrs.append((i, val))

        tag = f' *** -> {found_ds}' if found_ds else ''
        print(f'\n  IC={ic} ({name}) desc@0x{desc_addr:08X} subtype={sub}{tag}')
        print(f'    Pointers in descriptor:')
        for off, val in all_ptrs:
            # 检查指针目标是否是 DS 对象
            is_ds = val in ds_set
            marker = ' <=== DS OBJECT!' if is_ds else ''

            # 读指针目标的前几个 dword
            try:
                target_data = pm.read_bytes(val, 0x10)
                if target_data:
                    tv0 = struct.unpack_from('<I', target_data, 0)[0]
                    # 检查目标是否也是 vtable 开头的对象
                    if tv0 == DESC_VTABLE:
                        marker += ' [desc]'
                    elif tv0 == DS_VTABLE:
                        marker += ' [DS Actor]'
                    elif tv0 == 0x0284A9EC:
                        marker += ' [DD Actor]'
                print(f'    +0x{off:03X}: 0x{val:08X}{marker}')
            except:
                print(f'    +0x{off:03X}: 0x{val:08X} (unreadable){marker}')

        # 如果描述符里没直接指向 DS, 跟踪一层: 读每个指针目标, 搜索 DS 地址
        if not found_ds:
            for off, val in all_ptrs:
                try:
                    target_data = pm.read_bytes(val, 0x200)
                    if not target_data:
                        continue
                    for j in range(0, len(target_data) - 3, 4):
                        tv = struct.unpack_from('<I', target_data, j)[0]
                        if tv in ds_set:
                            print(f'    +0x{off:03X} -> 0x{val:08X} -> +0x{j:03X}: DS @ 0x{tv:08X} ***')
                except:
                    pass

    # Step 3: 也对每个 DS 对象, 读其全部指针字段, 看有没有指向描述符的
    print(f'\n[*] Reverse: DS object -> descriptor?')
    desc_addrs = {a for _, a, _, _ in hair_descs}
    for ds_addr in sorted(ds_objects):
        ds_data = pm.read_bytes(ds_addr, 0x600)
        if not ds_data:
            continue
        f46c = struct.unpack_from('<I', ds_data, 0x46C)[0]

        for i in range(0, len(ds_data) - 3, 4):
            val = struct.unpack_from('<I', ds_data, i)[0]
            if val in desc_addrs:
                print(f'  DS @ 0x{ds_addr:08X} (idx={f46c}) +0x{i:03X} -> desc 0x{val:08X} ***')

    # Step 4: 也扫描所有描述符 (不止发型), 看有没有指向 DS 的
    print(f'\n[*] All 1023 descriptors -> DS objects?')
    desc_target = struct.pack('<I', DESC_VTABLE)
    all_descs = []
    addr = 0
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
                        idx = data.find(desc_target, off)
                        if idx < 0:
                            break
                        desc_a = base + idx
                        ic_val = struct.unpack_from('<I', data, idx + 0x60)[0] if idx + 0x64 <= len(data) else 0
                        if ic_val > 0:
                            # 检查描述符内是否有 DS 指针
                            desc_d = data[idx:idx+0x200]
                            for j in range(0, min(len(desc_d), 0x200), 4):
                                dv = struct.unpack_from('<I', desc_d, j)[0]
                                if dv in ds_set:
                                    print(f'  Desc IC={ic_val} @ 0x{desc_a:08X} +0x{j:03X} -> DS 0x{dv:08X}')
                        off = idx + 4
            except:
                pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    pm.close_process()


if __name__ == '__main__':
    main()

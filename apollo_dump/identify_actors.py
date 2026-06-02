# identify_actors.py — 追踪 DS 对象指针，识别每个部件
#
# 对每个对象:
#   1. 读 0x800 字节
#   2. 跟踪所有指针 -> 读目标前 0x100 字节
#   3. 搜索 GBK 字符串、文件路径 (.smd/.sskf/.bml)、ItemCode

import pymem
import struct
import sys
import os
import ctypes
from ctypes import wintypes

DS_VTABLE = 0x0284E00C
TEXT_CEILING = 0x02B0000


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


def try_read(pm, addr, size):
    try:
        return pm.read_bytes(addr, size)
    except:
        return None


def try_read_dword(pm, addr):
    d = try_read(pm, addr, 4)
    if d and len(d) == 4:
        return struct.unpack_from('<I', d, 0)[0]
    return None


def scan_for_strings(data, min_len=4):
    """搜索 ASCII/GBK 可读字符串"""
    results = []
    current = b''
    start = 0
    for i in range(len(data)):
        b = data[i]
        if 0x20 <= b < 0x7F or b >= 0x80:  # ASCII printable or GBK high byte
            if not current:
                start = i
            current += bytes([b])
        else:
            if len(current) >= min_len:
                try:
                    s = current.decode('ascii')
                    results.append((start, s, 'ascii'))
                except:
                    try:
                        s = current.decode('gbk')
                        results.append((start, s, 'gbk'))
                    except:
                        pass
            current = b''
    if len(current) >= min_len:
        try:
            s = current.decode('ascii')
            results.append((start, s, 'ascii'))
        except:
            try:
                s = current.decode('gbk')
                results.append((start, s, 'gbk'))
            except:
                pass
    return results


def find_interesting_strings(strings):
    """过滤出有意义的字符串"""
    keywords = ['hair', 'head', 'body', 'face', 'shoe', 'pant', 'shirt', 'arm', 'leg',
                'hand', 'neck', 'glass', 'cap', 'wing', 'tail', 'back', 'item',
                '.smd', '.sskf', '.bml', '.pak', '501', 'data', 'mesh', 'skin',
                'char', 'model', 'anim', 'motion', 'equip', 'slot', 'part']
    interesting = []
    for off, s, enc in strings:
        s_lower = s.lower()
        if any(kw in s_lower for kw in keywords):
            interesting.append((off, s, enc))
    return interesting


def follow_pointer_chain(pm, addr, depth=2, max_chain=5):
    """跟踪指针链，记录每一步读到的内容"""
    chains = []
    visited = set()

    def _follow(addr, chain, remaining):
        if remaining <= 0 or addr in visited or addr < 0x10000:
            return
        visited.add(addr)
        data = try_read(pm, addr, 0x100)
        if not data:
            return

        # 检查这个地址的内容
        strings = scan_for_strings(data, min_len=3)
        interesting = find_interesting_strings(strings)

        entry = {
            'addr': addr,
            'dwords': [struct.unpack_from('<I', data, i)[0] for i in range(0, min(32, len(data)), 4)],
            'strings': strings[:10],
            'interesting': interesting,
        }
        chain.append(entry)

        if interesting:
            chains.append(list(chain))

        # 跟踪前几个 dword 作为指针
        if remaining > 1:
            for i in range(min(8, len(entry['dwords']))):
                ptr = entry['dwords'][i]
                if 0x00400000 <= ptr <= 0x7FFF0000 and ptr not in visited:
                    _follow(ptr, chain, remaining - 1)
                    if len(chains) >= max_chain:
                        return

    _follow(addr, [], depth)
    return chains


def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 直接用已知地址 (从 scan_actor_v3_deep 结果)
    # 也重新扫一次
    print('[*] Scanning DStaticActor objects...')
    target = struct.pack('<I', DS_VTABLE)
    h = pm.process_handle
    import ctypes
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

    ds_objects = []
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
                            if type8 == 3:
                                ds_objects.append(obj_addr)
                        off = idx + 4
            except:
                pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    print(f'[*] Found {len(ds_objects)} DS objects\n')

    for i, addr in enumerate(ds_objects):
        data = try_read(pm, addr, 0x800)
        if not data:
            continue

        f004 = struct.unpack_from('<I', data, 0x04)[0]
        f074 = struct.unpack_from('<I', data, 0x74)[0]
        f460 = struct.unpack_from('<I', data, 0x460)[0]
        f464 = struct.unpack_from('<I', data, 0x464)[0]
        f468 = struct.unpack_from('<I', data, 0x468)[0]
        f46c = struct.unpack_from('<I', data, 0x46C)[0]

        print(f'{"="*70}')
        print(f'  #{i} DS @ 0x{addr:08X}  idx={f46c}')
        print(f'{"="*70}')

        # 1. 搜索对象自身内的字符串
        obj_strings = scan_for_strings(data, min_len=3)
        obj_interesting = find_interesting_strings(obj_strings)
        if obj_interesting:
            print(f'  [obj strings]')
            for off, s, enc in obj_interesting:
                print(f'    +0x{off:03X} ({enc}): {s[:80]}')

        # 2. 跟踪关键指针
        key_offsets = [
            (0x04, 'f004'),
            (0x10, 'f010'),
            (0x14, 'f014'),
            (0x18, 'f018'),
            (0x40, 'f040'),
            (0x44, 'f044'),
            (0x48, 'f048'),
            (0x50, 'f050'),
            (0x54, 'f054'),
            (0x58, 'f058'),
            (0x60, 'f060'),
            (0x80, 'f080'),
            (0x84, 'f084'),
            (0x88, 'f088'),
            (0x90, 'f090'),
            (0xA0, 'f0A0'),
            (0xA4, 'f0A4'),
            (0xB0, 'f0B0'),
            (0xC0, 'f0C0'),
        ]

        print(f'  [pointer chase]')
        for off, name in key_offsets:
            ptr = struct.unpack_from('<I', data, off)[0]
            if ptr < 0x10000 or ptr > 0x7FFF0000:
                continue
            ptr_data = try_read(pm, ptr, 0x100)
            if not ptr_data:
                continue

            # 检查指针目标是否有字符串
            ptr_strings = scan_for_strings(ptr_data, min_len=3)
            ptr_interesting = find_interesting_strings(ptr_strings)

            # 也检查是否有 ItemCode
            item_codes = []
            for j in range(0, len(ptr_data) - 3, 4):
                v = struct.unpack_from('<I', ptr_data, j)[0]
                if 0x50000000 <= v <= 0x50FFFFFF:
                    item_codes.append((j, v))

            if ptr_interesting or item_codes:
                print(f'    {name}(+0x{off:02X}) -> 0x{ptr:08X}:')
                for soff, s, enc in ptr_interesting[:5]:
                    print(f'      [{enc}] +0x{soff:02X}: {s[:80]}')
                for coff, cv in item_codes:
                    print(f'      ItemCode: {cv} (0x{cv:08X}) @ +0x{coff:02X}')

            # 二级指针 (ptr 的 dword 再解引用)
            if ptr_interesting or item_codes:
                for j in range(0, min(16, len(ptr_data)), 4):
                    ptr2 = struct.unpack_from('<I', ptr_data, j)[0]
                    if 0x00400000 <= ptr2 <= 0x7FFF0000:
                        ptr2_data = try_read(pm, ptr2, 0x100)
                        if ptr2_data:
                            ptr2_strings = scan_for_strings(ptr2_data, min_len=3)
                            ptr2_interesting = find_interesting_strings(ptr2_strings)
                            if ptr2_interesting:
                                print(f'      ->[{j//4}] -> 0x{ptr2:08X}:')
                                for soff, s, enc in ptr2_interesting[:3]:
                                    print(f'         [{enc}] +0x{soff:02X}: {s[:80]}')

        # 3. 跟踪 f460 (phys/mesh data ptr)
        print(f'  [f460 chain]')
        if 0x00400000 <= f460 <= 0x7FFF0000:
            chains = follow_pointer_chain(pm, f460, depth=2, max_chain=3)
            for chain in chains:
                has_interesting = any(step['interesting'] for step in chain)
                if has_interesting:
                    for step in chain:
                        if step['interesting']:
                            print(f'    -> 0x{step["addr"]:08X}:')
                            for soff, s, enc in step['interesting'][:5]:
                                print(f'       [{enc}] +0x{soff:02X}: {s[:80]}')

        # 4. 跟踪 f468 (addr+0x100 自引用)
        print(f'  [f468 self-ref at +0x100]')
        sub_data = data[0x100:0x300]
        if sub_data:
            sub_strings = scan_for_strings(sub_data, min_len=3)
            sub_interesting = find_interesting_strings(sub_strings)
            for off, s, enc in sub_interesting[:5]:
                print(f'    +0x{0x100+off:03X} ({enc}): {s[:80]}')

            # sub region 里的指针也跟
            for j in range(0, min(len(sub_data), 0x60), 4):
                sp = struct.unpack_from('<I', sub_data, j)[0]
                if 0x00400000 <= sp <= 0x7FFF0000:
                    sp_data = try_read(pm, sp, 0x100)
                    if sp_data:
                        sp_strings = scan_for_strings(sp_data, min_len=3)
                        sp_interesting = find_interesting_strings(sp_strings)
                        if sp_interesting:
                            print(f'    +0x{0x100+j:03X} -> 0x{sp:08X}:')
                            for soff, s, enc in sp_interesting[:3]:
                                print(f'      [{enc}] +0x{soff:02X}: {s[:80]}')

        print()

    pm.close_process()


if __name__ == '__main__':
    main()

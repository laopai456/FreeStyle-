"""
find_acquiresmd_v3.py — 搜索 SSKF 附近所有可能的函数入口（含 thiscall）

思路:
  AcquireSMD 很可能是 thiscall (C++ 成员函数)
  从 SSKF 引用点往前搜索 ALL 可能的函数序言类型
"""

import sys, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000
TEXT_SIZE = 0x280A000

# SSKF 引用点 (已知)
SSKF_REFS = [0x022EC941, 0x022ED7D5, 0x02366958, 0x02367513, 0x024C4183]

# 所有 MSVC 函数序言模式
PROLOGUES = {
    'stdcall': b'\x55\x8B\xEC',                    # push ebp; mov ebp,esp (标准)
    'stdcall_sub': b'\x55\x8B\xEC\x83\xEC',        # 带局部变量
    'hotpatch': b'\x8B\xFF\x55\x8B\xEC',           # mov edi,edi; push ebp; mov ebp,esp
    'hotpatch_sub': b'\x8B\xFF\x55\x8B\xEC\x83\xEC', # mov edi,edi + stdcall + sub
    'seh_prolog': b'\x64\xA1\x00\x00\x00\x00\x55\x8B\xEC',  # mov eax,fs:[0]; push ebp; mov ebp,esp
    'thiscall': b'\x56\x8B\xF1',                   # push esi; mov esi, ecx (thiscall 常用)
    'thiscall_ebp': b'\x55\x8B\xEC\x56\x8B\xF1',  # push ebp; mov ebp,esp; push esi; mov esi,ecx
    'thiscall_edi': b'\x57\x8B\xF9',               # push edi; mov edi, ecx (变体)
    'thiscall_std': b'\x55\x8B\xEC\x51\x56\x8B\xF1', # stdcall 帧 + thiscall
    'fastcall_ecx': b'\x8B\xC8',                   # not really prologue
    'fpo_8': b'\x83\xEC\x08',                      # sub esp,8 (FPO, var=8)
    'fpo_10': b'\x83\xEC\x10',                     # sub esp,0x10
    'fpo_20': b'\x83\xEC\x20',                     # sub esp,0x20
    'fpo_30': b'\x83\xEC\x30',                     # sub esp,0x30
    'fpo_40': b'\x83\xEC\x40',                     # sub esp,0x40
    'fpo_50': b'\x83\xEC\x50',                     # sub esp,0x50
    'fpo_60': b'\x83\xEC\x60',                     # sub esp,0x60
    'fpo_80': b'\x83\xEC\x80',                     # sub esp,0x80
    'fpo_A0': b'\x83\xEC\xA0',                     # sub esp,0xA0
    'fpo_C0': b'\x83\xEC\xC0',                     # sub esp,0xC0
    'fpo_100': b'\x81\xEC\x00\x01\x00\x00',        # sub esp,0x100
    'fpo_200': b'\x81\xEC\x00\x02\x00\x00',        # sub esp,0x200
    'fpo_400': b'\x81\xEC\x00\x04\x00\x00',        # sub esp,0x400
    'fpo_800': b'\x81\xEC\x00\x08\x00\x00',        # sub esp,0x800
    'fpo_1000': b'\x81\xEC\x00\x10\x00\x00',       # sub esp,0x1000
    'cdecl_pure': b'\x55\x8B\xEC\x83\xEC\x50',     # 带50字节局部变量的 cdecl
    'push_regs': b'\x55\x8B\xEC\x56\x57',          # push ebp; mov ebp,esp; push esi; push edi
    'push_ebx': b'\x55\x8B\xEC\x53',               # push ebp; mov ebp,esp; push ebx
    'push_all': b'\x55\x8B\xEC\x56\x57\x53',       # push 3 regs
}

kernel32 = ctypes.windll.kernel32

def rpm(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok else None

def find_all_prologues(data, search_range_start, search_range_end):
    """在范围内搜索所有函数序言"""
    chunk = data[search_range_start:search_range_end]
    found = {}

    for name, pattern in PROLOGUES.items():
        pos = 0
        while True:
            idx = chunk.find(pattern, pos)
            if idx < 0:
                break
            abs_addr = search_range_start + idx
            rva = abs_addr
            if name not in found:
                found[name] = []
            found[name].append(abs_addr)
            pos = idx + 1

    return found

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    handle = pm.process_handle
    pid = pm.process_id
    print(f"[+] PID = {pid}")

    text_start = BASE + 0x1000
    print(f"[*] 加载 .text...")

    # 加载全部
    full_data = bytearray()
    offset = 0
    CHUNK_SIZE = 4 * 1024 * 1024
    while offset < TEXT_SIZE:
        read_size = min(CHUNK_SIZE, TEXT_SIZE - offset)
        data = rpm(handle, text_start + offset, read_size)
        if data:
            full_data.extend(data)
        offset += read_size
    data = bytes(full_data)
    print(f"[*] 已加载 {len(data)} 字节")
    print()

    # 对每个 SSKF 引用点，在其前 0x800 字节搜索函数序言
    for ref_addr in SSKF_REFS:
        rva = ref_addr - BASE
        ref_offset_in_data = ref_addr - text_start
        search_start = max(0, ref_offset_in_data - 0x800)
        search_end = ref_offset_in_data

        print(f"--- SSKF 引用 @ 0x{ref_addr:08X} (RVA 0x{rva:06X}) 前 0x800 字节 ---")

        results = find_all_prologues(data, search_start, search_end)

        # 按地址排序输出
        all_entries = set()
        for name, addrs in results.items():
            for a in addrs:
                all_entries.add(a)

        if not all_entries:
            print(f"  ❌ 0x800 内无任何函数序言")
        else:
            for a in sorted(all_entries):
                types = [n for n, addrs in results.items() if a in addrs]
                dist = ref_addr - a
                print(f"  0x{a:08X} (RVA 0x{a-BASE:06X}) [-0x{dist:X}] {' / '.join(types)}")

        print()

    print(f"\n--- 综合性搜索: 已知地址周围的序言 ---")
    known = [0x0229B0B0, 0x0229B4D0, 0x0229C2D0, 0x02297810, 0x022ECCD0]
    for addr in known:
        rva = addr - BASE
        offset_in_data = addr - text_start
        search_start = max(0, offset_in_data - 0x200)
        results = find_all_prologues(data, search_start, offset_in_data + 0x10)
        all_entries = set()
        for name, addrs in results.items():
            for a in addrs:
                all_entries.add(a)
        print(f"  0x{addr:08X} (RVA 0x{rva:06X}): ", end="")
        if all_entries:
            best = min(all_entries, key=lambda x: abs(x - addr))
            best_types = [n for n, addrs in results.items() if best in addrs]
            print(f"最近的序言 @ 0x{best:08X} (-0x{addr-best:X}): {'/'.join(best_types)}")
        else:
            print("0x200内无任何序言")

    pm.close_process()

if __name__ == "__main__":
    main()
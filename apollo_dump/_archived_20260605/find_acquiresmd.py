"""
find_acquiresmd.py — 搜索引用 SSKF 数据地址的所有函数入口

思路:
  AcquireSMD 把 "SSKF" 字符串地址 (0x284B9C4) 加载到寄存器
  在 x86 代码中，地址 0x284B9C4 的小端编码 = C4 B9 84 02
  所有引用这个地址的代码，都在引用的函数附近
  找到这些引用点后往回搜索函数序言 → 得到入口

综合搜索所有已知锚点:
  SSKF 地址   = C4 B9 84 02  (0x0284B9C4)
  .smd 字符串 = 2E 73 6D 64  (".smd")
  "SMD" 字符串= 53 4D 44     ("SMD")
"""

import sys, struct, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000
TEXT_RVA = 0x1000
TEXT_SIZE = 0x280A000

# 搜索锚点
ANCHORS = {
    'SSKF地址引用 (小端 0x0284B9C4)': b'\xC4\xB9\x84\x02',
    'SSKF RVA引用 (小端 0x0244B9C4)': b'\xC4\xB9\x44\x02',
    '.smd 字符串': b'\x2E\x73\x6D\x64',
    'SMD 字符串': b'\x53\x4D\x44',
    'AcquireSMD 函数名': b'AcquireSMD',
    'i50111851': b'i50111851',  # 目标发型SMD
}

PROLOGUE_STD = b'\x55\x8B\xEC'        # push ebp; mov ebp, esp (stdcall/cdecl)
PROLOGUE_HOT = b'\x8B\xFF\x55\x8B\xEC' # mov edi,edi; push ebp; mov ebp, esp (hotpatch)

kernel32 = ctypes.windll.kernel32

def rpm(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok else None

def find_all(data, needle):
    """查找所有匹配位置"""
    results = []
    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx < 0:
            break
        results.append(idx)
        pos = idx + 1
    return results

def find_prologue(data, offset_in_chunk, chunk_base, search_back=0x200):
    """从当前位置往回搜索函数序言"""
    search_start = max(0, offset_in_chunk - search_back)
    chunk = data[search_start:offset_in_chunk]
    # 搜索标准序言 55 8B EC
    idx = chunk.find(PROLOGUE_STD)
    if idx >= 0:
        return chunk_base + search_start + idx
    # 搜索hotpatch序言 8B FF 55 8B EC
    idx = chunk.find(PROLOGUE_HOT)
    if idx >= 0:
        return chunk_base + search_start + idx
    return None

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    handle = pm.process_handle
    pid = pm.process_id
    print(f"[+] PID = {pid}")
    print()

    text_start = BASE + TEXT_RVA
    CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks
    print(f"[*] 加载 .text ({TEXT_SIZE/1024/1024:.0f}MB) 到内存...")

    full_data = bytearray()
    offset = 0
    while offset < TEXT_SIZE:
        read_size = min(CHUNK_SIZE, TEXT_SIZE - offset)
        data = rpm(handle, text_start + offset, read_size)
        if data:
            full_data.extend(data)
        else:
            print(f"[!] 读取失败 @ 0x{text_start + offset:08X}")
            full_data.extend(b'\x00' * read_size)
        offset += read_size
        if offset % (8 * 1024 * 1024) == 0:
            print(f"    [{offset * 100 // TEXT_SIZE}%]")

    print(f"[*] 已加载 {len(full_data)} 字节")
    print()

    for name, needle in ANCHORS.items():
        hits = find_all(bytes(full_data), needle)
        print(f"--- {name} ({len(hits)} 处命中) ---")
        for h in hits[:20]:
            abs_addr = text_start + h
            rva = abs_addr - BASE
            # 返回搜索函数入口
            entry = find_prologue(bytes(full_data), h, text_start)

            extra = ''
            # 显示周围 16 字节上下文
            ctx_start = max(0, h - 4)
            ctx = full_data[ctx_start:ctx_start + 20]
            ctx_hex = ' '.join(f'{b:02x}' for b in ctx)
            extra = f'  ctx: [{ctx_hex}]'

            if entry:
                entry_rva = entry - BASE
                print(f"  命中 @ 0x{abs_addr:08X} (RVA 0x{rva:06X}) → 函数入口 @ 0x{entry:08X} (RVA 0x{entry_rva:06X}){extra}")
            else:
                print(f"  命中 @ 0x{abs_addr:08X} (RVA 0x{rva:06X}) → ❌ 0x200 内无函数序言{extra}")
        if len(hits) > 20:
            print(f"  ... 还有 {len(hits) - 20} 处")

    # 保存全量结果
    out_path = r"D:\py\反编译\FreeStyle\apollo_dump\runtime\function_entries.txt"
    with open(out_path, 'w') as f:
        f.write("所有函数入口 (RVA):\n")
        for off in range(len(full_data) - 2):
            if full_data[off:off+3] == PROLOGUE_STD:
                abs_addr = text_start + off
                f.write(f"  0x{abs_addr:08X}  (RVA 0x{abs_addr - BASE:06X})\n")
    print(f"\n[+] 函数入口列表已保存: {out_path}")

    pm.close_process()
    print("[*] 完成")

if __name__ == "__main__":
    main()
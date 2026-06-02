"""
scan_prologues.py — 用 Pymem 读取加密 .text，搜索所有函数入口

原理:
  .text (40MB) 在内存中已解密，ReadProcessMemory 可安全读取
  搜索 55 8B EC (push ebp; mov ebp, esp) = x86 标准函数序言
  输出的地址就是所有函数入口 — Frida Memory.scan 坏了，绕过它
"""

import sys, struct, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000
TEXT_RVA = 0x1000
TEXT_SIZE = 0x280A000  # 40MB

PROLOGUE = b'\x55\x8B\xEC'  # push ebp; mov ebp, esp

kernel32 = ctypes.windll.kernel32

def rpm(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    if not ok:
        return None
    return buf.raw[:n.value]

def scan_chunk(data, offset_base):
    """在 data 中搜索所有序言"""
    results = []
    pos = 0
    while True:
        idx = data.find(PROLOGUE, pos)
        if idx < 0:
            break
        results.append(offset_base + idx)
        pos = idx + 1  # 允许重叠搜索
    return results

def group_by_page(addrs):
    """按 0x1000 页分组"""
    pages = {}
    for a in addrs:
        p = a & ~0xFFF
        if p not in pages:
            pages[p] = []
        pages[p].append(a)
    return pages

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    handle = pm.process_handle
    pid = pm.process_id
    print(f"[+] PID = {pid}")

    text_start = BASE + TEXT_RVA
    CHUNK_SIZE = 1024 * 1024  # 1MB per read

    total_hits = []
    chunk_num = 0

    print(f"[*] 扫描 .text ({TEXT_SIZE/1024/1024:.0f}MB)...")
    start = time.time()

    offset = 0
    while offset < TEXT_SIZE:
        read_size = min(CHUNK_SIZE, TEXT_SIZE - offset)
        addr = text_start + offset
        data = rpm(handle, addr, read_size)
        if data is None:
            print(f"[!] 读取失败 @ 0x{addr:08X} (offset 0x{offset:X})")
            offset += read_size
            continue

        hits = scan_chunk(data, offset)
        total_hits.extend(hits)
        chunk_num += 1

        if chunk_num % 10 == 0:
            pct = (offset + read_size) * 100 // TEXT_SIZE
            print(f"    [{pct}%] {len(total_hits)} 个入口已找到...")

        offset += read_size

    elapsed = time.time() - start
    print(f"\n[+] 扫描完成: {elapsed:.1f}s, 共 {len(total_hits)} 个函数入口")

    # 按页分组
    pages = group_by_page([text_start + o for o in total_hits])
    page_addrs = sorted(pages.keys())

    # 密度最高的页
    print(f"\n--- 函数密度最高的 20 页 ---")
    sorted_pages = sorted(pages.items(), key=lambda x: -len(x[1]))
    for addr, funcs in sorted_pages[:20]:
        rva = addr - BASE
        print(f"  RVA 0x{rva:06X} (0x{addr:08X}): {len(funcs)} 个入口")

    # SSKF 附近的入口
    SSKF_RUNTIME = 0x284B9C4
    print(f"\n--- SSKF 附近 (±{0x100000:#x}) 的入口 ---")
    nearby = [a for a in [text_start + o for o in total_hits]
              if abs(a - SSKF_RUNTIME) < 0x100000]
    print(f"  找到 {len(nearby)} 个")
    for addr in sorted(nearby)[:50]:
        rva = addr - BASE
        print(f"  0x{addr:08X} (RVA 0x{rva:06X})")

    # 已知地址验证
    known = {
        'DDynamicActor ctor': 0x229B0B0,
        'DStaticActor ctor': 0x236B8A0,
        'DynamicInit': 0x229B4D0,
        'DynamicPhysicsInit': 0x229C2D0,
        'SetMotionType': 0x2297810,
        'CharacterMotion解析': 0x21B46E0,
        '对象工厂': 0x21C1F00,
        'SSKF加载器': 0x22ECCD0,
    }
    print(f"\n--- 已知地址验证 ---")
    for name, addr in known.items():
        data = rpm(handle, addr, 3)
        if data and data[:3] == PROLOGUE:
            print(f"  {name} @ 0x{addr:08X}: ✅ 55 8B EC 确认")
        elif data:
            print(f"  {name} @ 0x{addr:08X}: ⚠️ 字节 {data.hex()} (非标准序言)")
        else:
            print(f"  {name} @ 0x{addr:08X}: ❌ 读取失败")

    # 保存到文件
    out_path = r"D:\py\反编译\FreeStyle\apollo_dump\runtime\prologues.txt"
    with open(out_path, 'w') as f:
        f.write(f"总入口数: {len(total_hits)}\n\n")
        f.write("全部入口 (RVA):\n")
        for o in sorted(total_hits):
            f.write(f"  0x{(text_start + o):08X}  (RVA 0x{(text_start + o - BASE):06X})\n")
    print(f"\n[+] 完整列表已保存: {out_path}")

    pm.close_process()
    print("[*] 完成")

if __name__ == "__main__":
    main()
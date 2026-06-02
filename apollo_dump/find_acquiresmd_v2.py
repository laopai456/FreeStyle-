"""
find_acquiresmd_v2.py — 搜索引用 AcquireSMD/SSKF 字符串地址的代码

思路:
  AcquireSMD 调试字符串 @ 0x0284B9DE ("in AcquireSMD(SFullName) = [%s]")
  SSKF 数据 @ 0x0284B9C4
  这些字符串被函数体内的 push/lea/mov 指令引用
  搜索其地址的小端编码 → 找到引用点 → 回溯函数入口
"""

import sys, struct, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000
TEXT_SIZE = 0x280A000

# AcquireSMD 相关字符串的运行时地址 (小端编码)
STR_ADDRS = {
    'AcquireSMD调试字符串': struct.pack('<I', 0x0284B9DE),
    'strSMD字符串':        struct.pack('<I', 0x0284B9CF),
    'SSKF数据':            struct.pack('<I', 0x0284B9C4),
    'AcquireSMD2':         struct.pack('<I', 0x0284BA0F),  # 第二个 strSMD
    'AcquireSMD2格式':     struct.pack('<I', 0x0284BA1E),  # 第二个 SFullName
    'strSMD3':             struct.pack('<I', 0x0284BA0F),
}

PROLOGUE_STD = b'\x55\x8B\xEC'           # push ebp; mov ebp, esp
PROLOGUE_HOT = b'\x8B\xFF\x55\x8B\xEC'   # mov edi,edi; push ebp...
PROLOGUE_SEH = b'\x64\xA1\x00\x00\x00\x00'  # mov eax, fs:[0]
PROLOGUE_MOV = b'\x8B\xFF'               # mov edi, edi (hotpatch entry without push)

kernel32 = ctypes.windll.kernel32

def rpm(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok else None

def find_prologue(data, pos_in_data, text_base, search_back=0x400):
    """从 pos 往回搜索函数序言，支持多种序言类型"""
    start = max(0, pos_in_data - search_back)
    chunk = data[start:pos_in_data + 3]  # +3 to allow matching at boundary

    # 按优先级搜索
    for name, pattern in [
        ('stdcall', PROLOGUE_STD),
        ('hotpatch', PROLOGUE_HOT),
        ('hotpatch_entry', PROLOGUE_MOV),
        ('seh', PROLOGUE_SEH),
    ]:
        idx = chunk.find(pattern)
        if idx >= 0 and idx < (pos_in_data - start):  # 必须在 pos 之前
            # 如果是 MOV EDI,EDI (hotpatch entry), 检查后面是否是 55 8B EC
            if pattern == PROLOGUE_MOV:
                # 检查是否构成 hotpatch 序言: 8B FF 55 8B EC
                after_mov = chunk[idx + 2:idx + 5]
                if after_mov == PROLOGUE_STD:
                    return text_base + start + idx  # 返回 8B FF 的位置
            else:
                return text_base + start + idx

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

    text_start = BASE + 0x1000
    CHUNK_SIZE = 4 * 1024 * 1024

    # 加载 .text 到内存
    print(f"[*] 加载 .text...")
    full_data = bytearray()
    offset = 0
    while offset < TEXT_SIZE:
        read_size = min(CHUNK_SIZE, TEXT_SIZE - offset)
        data = rpm(handle, text_start + offset, read_size)
        if data:
            full_data.extend(data)
        offset += read_size
        if offset % (8 * 1024 * 1024) == 0:
            print(f"    [{offset * 100 // TEXT_SIZE}%]")
    print(f"[*] 已加载 {len(full_data)} 字节")
    print()

    data = bytes(full_data)
    results = []

    for name, needle in STR_ADDRS.items():
        pos = 0
        while True:
            idx = data.find(needle, pos)
            if idx < 0:
                break
            abs_addr = text_start + idx
            entry = find_prologue(data, idx, text_start, 0x400)

            # 显示上下文
            ctx_start = max(0, idx - 8)
            ctx_len = min(28, len(data) - ctx_start)
            ctx = data[ctx_start:ctx_start + ctx_len]

            results.append({
                'name': name,
                'abs_addr': abs_addr,
                'rva': abs_addr - BASE,
                'entry': entry,
                'entry_rva': entry - BASE if entry else 0,
                'ctx': ctx,
            })
            pos = idx + 1

    # 按地址排序
    results.sort(key=lambda r: r['abs_addr'])

    # 分组输出
    last_name = ''
    for r in results:
        if r['name'] != last_name:
            print(f"\n--- {r['name']} ---")
            last_name = r['name']

        ctx_hex = ' '.join(f'{b:02x}' for b in r['ctx'])
        if r['entry']:
            print(f"  引用 @ 0x{r['abs_addr']:08X} (RVA 0x{r['rva']:06X}) "
                  f"→ {r['entry_rva']:#06X} ctx: [{ctx_hex}]")
        else:
            print(f"  引用 @ 0x{r['abs_addr']:08X} (RVA 0x{r['rva']:06X}) "
                  f"→ ❌ 0x400内无函数序言 ctx: [{ctx_hex}]")

    # 汇总
    with_entry = [r for r in results if r['entry']]
    print(f"\n\n===== 汇总 =====")
    print(f"总引用数: {len(results)}")
    print(f"有函数入口的: {len(with_entry)}")
    print()

    if with_entry:
        print("所有找到的候选函数入口 (按地址排序):")
        unique_entries = sorted(set(r['entry'] for r in with_entry))
        for e in unique_entries:
            refs = [r for r in with_entry if r['entry'] == e]
            ref_types = ', '.join(set(r['name'] for r in refs))
            print(f"  0x{e:08X} (RVA 0x{e - BASE:06X}) — {ref_types} [{len(refs)}处引用]")

    # 保存到文件
    out_path = r"D:\py\反编译\FreeStyle\apollo_dump\runtime\acquiresmd_candidates.txt"
    with open(out_path, 'w') as f:
        f.write(f"总引用: {len(results)}, 有函数入口: {len(with_entry)}\n\n")
        for r in sorted(results, key=lambda x: x['abs_addr']):
            f.write(f"0x{r['abs_addr']:08X} | {r['name']} | "
                    f"entry=0x{r['entry']:08X}" + ("\n" if r['entry'] else " NONE\n"))
        f.write("\n\n候选函数入口:\n")
        for e in sorted(set(r['entry'] for r in with_entry if r['entry'])):
            refs = [(r['name'], r['abs_addr']) for r in with_entry if r['entry'] == e]
            f.write(f"0x{e:08X} (RVA 0x{e-BASE:06X}): {refs}\n")
    print(f"\n[+] 已保存: {out_path}")

    pm.close_process()

if __name__ == "__main__":
    main()
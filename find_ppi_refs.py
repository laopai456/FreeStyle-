"""
find_ppi_code_refs.py — 在游戏代码段搜索 .ppi 和 item_ 字符串引用
找到构造资源路径的代码位置

结果写文件
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.process, pymem.memory

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("FreeStyle.exe not found"); return

    outpath = r"D:\py\反编译\FreeStyle\find_ppi_refs.txt"
    outf = open(outpath, 'w', encoding='utf-8')

    mod = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
    base = mod.lpBaseOfDll
    size = mod.SizeOfImage
    code_end = base + size

    print(f"PID={pm.process_id}  base=0x{base:08X}  size=0x{size:08X}")
    outf.write(f"Module: 0x{base:08X} - 0x{code_end:08X}\n\n")

    # 读取整个模块
    data = pm.read_bytes(base, size)

    # 搜索关键字符串
    needles = [b'.ppi', b'item_24', b'item_26', b'%s.ppi', b'%d.ppi', b'.pak']

    for needle in needles:
        hits = []
        pos = 0
        while True:
            idx = data.find(needle, pos)
            if idx < 0: break
            hits.append(base + idx)
            pos = idx + 1

        line = f"'{needle.decode()}' in module: {len(hits)} hits"
        print(f"  {line}")
        outf.write(f"\n{'='*60}\n{line}\n{'='*60}\n")

        for addr in hits[:50]:
            # 读取上下文
            off = addr - base
            start = max(0, off - 16)
            end = min(len(data), off + 48)
            chunk = data[start:end]

            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            line = f"  0x{addr:08X}: {ascii_part}"
            outf.write(line + '\n')

        if len(hits) > 50:
            outf.write(f"  ... and {len(hits)-50} more\n")

    # 也搜索 push 指令引用这些字符串地址的模式
    # 在32位代码中, push addr = 68 XX XX XX XX
    outf.write(f"\n\n{'='*60}\nSearching for PUSH references to '.ppi' strings in code\n{'='*60}\n")
    print("  Searching PUSH references...")

    ppi_hits = []
    pos = 0
    while True:
        idx = data.find(b'.ppi', pos)
        if idx < 0: break
        ppi_hits.append(base + idx)
        pos = idx + 1

    for str_addr in ppi_hits[:200]:
        # 搜索 push str_addr (68 + LE addr)
        push_bytes = b'\x68' + struct.pack("<I", str_addr)
        pos = 0
        refs = []
        while True:
            idx = data.find(push_bytes, pos)
            if idx < 0: break
            refs.append(base + idx)
            pos = idx + 1

        for ref_addr in refs[:5]:
            # 读取引用点前后
            off = ref_addr - base
            ctx = data[max(0,off-8):off+16]
            hex_str = " ".join(f"{b:02x}" for b in ctx)
            outf.write(f"  0x{ref_addr:08X}: push 0x{str_addr:08X}  [{hex_str}]\n")

    outf.close()
    print(f"  Written to {outpath}")
    pm.close_process()

if __name__ == "__main__":
    main()

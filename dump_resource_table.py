"""
dump_resource_table.py — dump item_2404 区域的结构, 找 ItemCode→资源路径映射

从 find_resource_loader 结果看, item_2404 字符串集中在 0x2973XXXX 区域。
dump 这个区域看结构。
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.memory

IC_MIN = 0x02F00000
IC_MAX = 0x03200000

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("FreeStyle.exe not found"); return

    outpath = r"D:\py\反编译\FreeStyle\dump_resource_table.txt"
    outf = open(outpath, 'w', encoding='utf-8')

    def log(s):
        outf.write(s + '\n')

    log(f"PID={pm.process_id}")

    # 第一个 item_2404 命中在 0x2973D10F, 往前找结构头
    # 先 dump 0x2973D000 开始的 0x1000 字节
    base = 0x2973D000
    log(f"\n=== Dump 0x{base:08X} (around first item_2404 hit) ===\n")

    # 先以4字节为单位, 找 ItemCode 范围值
    try:
        data = pm.read_bytes(base, 0x2000)
    except:
        log("read error"); outf.close(); return

    log("--- 4-byte values in IC range (0x02F00000~0x03200000) ---")
    for i in range(0, len(data), 4):
        val = struct.unpack_from("<I", data, i)[0]
        if IC_MIN <= val <= IC_MAX:
            addr = base + i
            log(f"  0x{addr:08X} (+0x{i:04X}): 0x{val:08X} ({val})")

    # dump hex 前 0x200 字节看结构
    log("\n--- Hex dump 0x2973D000 +0x000~0x200 ---")
    for i in range(0, 0x200, 16):
        chunk = data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        log(f"  0x{base+i:08X}: {hex_part:<48s} {ascii_part}")

    # 也搜索 .ppi 路径附近的结构
    # 第一个 .ppi 路径在 0x25C6990C
    log("\n=== Around .ppi paths at 0x25C69900 ===\n")
    ppi_base = 0x25C69800
    try:
        ppi_data = pm.read_bytes(ppi_base, 0x400)
    except:
        log("read error")
        outf.close()
        return

    log("--- 4-byte values in IC range ---")
    for i in range(0, len(ppi_data), 4):
        val = struct.unpack_from("<I", ppi_data, i)[0]
        if IC_MIN <= val <= IC_MAX:
            addr = ppi_base + i
            log(f"  0x{addr:08X} (+0x{i:04X}): 0x{val:08X} ({val})")

    log("\n--- Hex dump ---")
    for i in range(0, min(len(ppi_data), 0x400), 16):
        chunk = ppi_data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        log(f"  0x{ppi_base+i:08X}: {hex_part:<48s} {ascii_part}")

    # 再看 0x29E91900 区域 (另一组 .ppi 路径)
    log("\n=== Around .ppi paths at 0x29E91900 ===\n")
    e9_base = 0x29E91800
    try:
        e9_data = pm.read_bytes(e9_base, 0x400)
    except:
        log("read error")
        outf.close()
        return

    log("--- 4-byte values in IC range ---")
    for i in range(0, len(e9_data), 4):
        val = struct.unpack_from("<I", e9_data, i)[0]
        if IC_MIN <= val <= IC_MAX:
            addr = e9_base + i
            log(f"  0x{addr:08X} (+0x{i:04X}): 0x{val:08X} ({val})")

    log("\n--- Hex dump ---")
    for i in range(0, min(len(e9_data), 0x400), 16):
        chunk = e9_data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        log(f"  0x{e9_base+i:08X}: {hex_part:<48s} {ascii_part}")

    # 搜索 0x297F5400 区域 (item_2604 命中区, 可能有 ItemCode)
    log("\n=== Around item names at 0x297F5400 ===\n")
    name_base = 0x297F5400
    try:
        name_data = pm.read_bytes(name_base, 0x400)
    except:
        log("read error")
        outf.close()
        return

    log("--- 4-byte values in IC range ---")
    for i in range(0, len(name_data), 4):
        val = struct.unpack_from("<I", name_data, i)[0]
        if IC_MIN <= val <= IC_MAX:
            addr = name_base + i
            log(f"  0x{addr:08X} (+0x{i:04X}): 0x{val:08X} ({val})")

    log("\n--- Hex dump ---")
    for i in range(0, min(len(name_data), 0x400), 16):
        chunk = name_data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        log(f"  0x{name_base+i:08X}: {hex_part:<48s} {ascii_part}")

    outf.close()
    print(f"Written to {outpath}")
    pm.close_process()

if __name__ == "__main__":
    main()

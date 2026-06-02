"""
patch_all_ic.py — 暴力 patch 内存中 ItemCode 的所有出现位置

之前改背包结构只改了 1 处，外观没变。这次改全部。
如果改了所有位置外观还不变 → ItemCode 根本不用于装备外观渲染。

用法: py patch_all_ic.py <src_itemcode> <dst_itemcode>
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.memory

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000

def scan_all(pm, needle_bytes):
    hits = []
    addr = HEAP_MIN
    while addr < HEAP_MAX:
        try:
            mbi = pymem.memory.virtual_query(pm.process_handle, addr)
        except Exception:
            addr += 0x10000; continue
        next_addr = int(mbi.BaseAddress) + int(mbi.RegionSize)
        if int(mbi.State) != 0x1000:
            addr = next_addr; continue
        protect = int(mbi.Protect) & 0xFF
        if protect not in (0x04, 0x40, 0x02, 0x20):
            addr = next_addr; continue
        r_base = max(int(mbi.BaseAddress), HEAP_MIN)
        r_end = min(int(mbi.BaseAddress) + int(mbi.RegionSize), HEAP_MAX)
        r_size = r_end - r_base
        if r_size <= 0 or r_size > 0x1000000:
            addr = next_addr; continue
        try:
            data = pm.read_bytes(r_base, r_size)
        except Exception:
            addr = next_addr; continue
        pos = 0
        while True:
            idx = data.find(needle_bytes, pos)
            if idx < 0: break
            hits.append(r_base + idx)
            pos = idx + 1
        addr = next_addr
    return hits

def main():
    if len(sys.argv) < 3:
        print("Usage: py patch_all_ic.py <src> <dst>")
        return
    src = int(sys.argv[1])
    dst = int(sys.argv[2])

    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except pymem.exception.ProcessNotFound:
        print("FreeStyle.exe not found"); return
    except pymem.exception.CouldNotOpenProcess:
        print("Run as Administrator"); return

    print(f"PID={pm.process_id}  {src} -> {dst}  (PATCH ALL)")

    needle = struct.pack("<I", src)
    hits = scan_all(pm, needle)
    print(f"Found {len(hits)} occurrences\n")

    # 保存原始数据用于恢复
    originals = {}
    for addr in hits:
        try:
            originals[addr] = pm.read_bytes(addr, 4)
            pm.write_int(addr, dst)
            print(f"  PATCHED 0x{addr:08X}")
        except Exception as e:
            print(f"  SKIP    0x{addr:08X} ({e})")

    patched = len(originals)
    print(f"\nPatched {patched} locations. Now equip the item.")
    print("Press Enter to RESTORE...")
    input()

    for addr, orig_bytes in originals.items():
        try:
            pm.write_bytes(addr, orig_bytes, 4)
        except:
            pass
    print(f"Restored {patched} locations")
    pm.close_process()

if __name__ == "__main__":
    main()

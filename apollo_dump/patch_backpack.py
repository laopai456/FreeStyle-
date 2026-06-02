"""
patch_backpack.py — 修改背包数据结构中的 ItemCode

结构 (每条目 0x30 字节):
  +0x00: ItemCode (4B)
  +0x04: ptr1 (4B)
  +0x08: ptr2 (4B)
  +0x0C: ptr3 (4B)
  +0x10: 0
  +0x14: ASCII ItemCode (12B, null-terminated)
  +0x20: 0
  +0x24: flags
  +0x28: flags
  +0x2C: 0

用法: py patch_backpack.py <src_itemcode> <dst_itemcode>
  先运行, 然后在游戏内装备 src 物品, 观察外观变化。
  回车恢复。
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.pattern

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000

def scan_all(pm, needle_bytes):
    """手动扫描所有可读内存区域"""
    hits = []
    addr = HEAP_MIN
    while addr < HEAP_MAX:
        try:
            mbi = pymem.memory.virtual_query(pm.process_handle, addr)
        except Exception:
            addr += 0x10000
            continue
        next_addr = int(mbi.BaseAddress) + int(mbi.RegionSize)
        if int(mbi.State) != 0x1000:
            addr = next_addr
            continue
        protect = int(mbi.Protect) & 0xFF
        if protect not in (0x04, 0x40, 0x02, 0x20):
            addr = next_addr
            continue
        r_base = max(int(mbi.BaseAddress), HEAP_MIN)
        r_end = min(int(mbi.BaseAddress) + int(mbi.RegionSize), HEAP_MAX)
        r_size = r_end - r_base
        if r_size <= 0 or r_size > 0x1000000:
            addr = next_addr
            continue
        try:
            data = pm.read_bytes(r_base, r_size)
        except Exception:
            addr = next_addr
            continue
        pos = 0
        while True:
            idx = data.find(needle_bytes, pos)
            if idx < 0:
                break
            hits.append(r_base + idx)
            pos = idx + 1
        addr = next_addr
    return hits

def main():
    if len(sys.argv) < 3:
        print("Usage: py patch_backpack.py <src_itemcode> <dst_itemcode>")
        print("  Example: py patch_backpack.py 50122721 50125711")
        return

    src = int(sys.argv[1])
    dst = int(sys.argv[2])

    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe not running"); return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] Run as Administrator"); return

    print(f"PID={pm.process_id}  {src} -> {dst}")

    # 搜索 src ItemCode 的二进制值
    needle = struct.pack("<I", src)
    hits = scan_all(pm, needle)
    print(f"Found {len(hits)} occurrences of {src}\n")

    patched = []
    src_ascii = str(src).encode('ascii')
    dst_ascii = str(dst).encode('ascii')

    for addr in hits:
        try:
            # 检查是否是背包结构: +0x14 应该有 ASCII ItemCode
            ascii_data = pm.read_bytes(addr + 0x14, 12)
            if src_ascii not in ascii_data:
                continue

            # 读完整条目
            entry = pm.read_bytes(addr, 0x30)
            ic = struct.unpack_from("<I", entry, 0)[0]
            ptr1 = struct.unpack_from("<I", entry, 4)[0]
            ptr2 = struct.unpack_from("<I", entry, 8)[0]
            ptr3 = struct.unpack_from("<I", entry, 12)[0]

            print(f"  BACKPACK ENTRY at 0x{addr:08X}")
            print(f"    IC=0x{ic:08X}  ptr1=0x{ptr1:08X}  ptr2=0x{ptr2:08X}  ptr3=0x{ptr3:08X}")
            print(f"    ASCII: {ascii_data}")

            # 修改 ItemCode (二进制)
            pm.write_int(addr, dst)
            # 修改 ASCII 字符串
            padded = dst_ascii + b'\x00' * (12 - len(dst_ascii))
            pm.write_bytes(addr + 0x14, padded, 12)
            patched.append(addr)
            print(f"    -> PATCHED to {dst}")

        except Exception as e:
            print(f"  0x{addr:08X} error: {e}")

    if not patched:
        print("\nNo backpack entries found.")
        print("尝试装备数组扫描...")

        # fallback: 装备数组 (相邻也是 ItemCode)
        for addr in hits:
            try:
                before = struct.unpack_from("<I", pm.read_bytes(addr - 4, 4))[0]
                after1 = struct.unpack_from("<I", pm.read_bytes(addr + 4, 4))[0]
                after2 = struct.unpack_from("<I", pm.read_bytes(addr + 8, 4))[0]
                ic_range = lambda v: 0x02F00000 <= v <= 0x03200000
                neighbors = sum(1 for v in [before, after1, after2] if ic_range(v))
                if neighbors >= 2:
                    print(f"  EQUIP ARRAY at 0x{addr:08X}")
                    pm.write_int(addr, dst)
                    patched.append(addr)
                    print(f"    -> PATCHED to {dst}")
            except Exception as e:
                pass

    if not patched:
        print("Nothing to patch. Make sure item is in backpack.")
        pm.close_process()
        return

    print(f"\nPatched {len(patched)} locations.")
    print("Now equip the item in-game. Press Enter to RESTORE...")
    input()

    for addr in patched:
        try:
            pm.write_int(addr, src)
            padded = src_ascii + b'\x00' * (12 - len(src_ascii))
            pm.write_bytes(addr + 0x14, padded, 12)
        except:
            pass
    print(f"Restored {len(patched)} locations")
    pm.close_process()

if __name__ == "__main__":
    main()

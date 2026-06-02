"""
patch_equip_slot.py — 直接修改游戏状态对象的装备 ItemCode (pymem, 无 hook)

原理: 扫描内存找到 this+0xE34 处的源 ItemCode, 直接改写为目标值。
和 patch_itemcode.py (商城描述符) 一样的方式, 但针对装备槽位数组。

用法: py patch_equip_slot.py <src_itemcode> <dst_itemcode>
  修改后装备 src 物品, 游戏会按 dst 的数据发包。
  按回车恢复。

验证逻辑: 只修改周围也是 ItemCode 值的位置 (装备数组特征)
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.pattern

# ItemCode 范围: 0x02F00000 ~ 0x03200000 (发型/衣服等物品)
IC_MIN = 0x02F00000
IC_MAX = 0x03200000

def is_ic_like(val):
    return IC_MIN <= val <= IC_MAX

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe not running")
        return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] Run as Administrator")
        return

    if len(sys.argv) < 3:
        print("Usage: py patch_equip_slot.py <src_itemcode> <dst_itemcode>")
        print("  Example: py patch_equip_slot.py 50122721 50125721")
        pm.close_process()
        return

    src = int(sys.argv[1])
    dst = int(sys.argv[2])
    print(f"PID={pm.process_id}  {src} (0x{src:08X}) -> {dst} (0x{dst:08X})")

    # 搜索所有 src ItemCode 的位置
    needle = struct.pack("<I", src)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, needle, return_multiple=True)
    print(f"\nFound {len(hits)} occurrences of ItemCode {src}")

    patched = []
    for addr in hits:
        try:
            # 检查 +0xE34 上下文: 周围也应该是 ItemCode 值
            # 即 addr-4, addr+4, addr+8 都在 ItemCode 范围内
            before = struct.unpack_from("<I", pm.read_bytes(addr - 4, 4))[0]
            after1 = struct.unpack_from("<I", pm.read_bytes(addr + 4, 4))[0]
            after2 = struct.unpack_from("<I", pm.read_bytes(addr + 8, 4))[0]

            neighbors_ic = sum(1 for v in [before, after1, after2] if is_ic_like(v))

            if neighbors_ic >= 2:
                # 这是装备数组中的位置
                print(f"  0x{addr:08X}  EQUIP ARRAY  prev=0x{before:08X} next=0x{after1:08X} next2=0x{after2:08X}")
                pm.write_int(addr, dst)
                patched.append(addr)
                print(f"    -> PATCHED")
            else:
                print(f"  0x{addr:08X}  (not equip array, neighbors_ic={neighbors_ic})  skip")
        except Exception as e:
            print(f"  0x{addr:08X}  (read error: {e})")

    if not patched:
        print(f"\nNo equip array locations found. Try equipping the item first, then run again.")
        pm.close_process()
        return

    print(f"\nPatched {len(patched)} locations. Now equip the item in-game.")
    print(f"Press Enter to RESTORE...")
    input()

    for addr in patched:
        try:
            pm.write_int(addr, src)
        except:
            pass
    print(f"Restored {len(patched)} locations")
    pm.close_process()

if __name__ == "__main__":
    main()

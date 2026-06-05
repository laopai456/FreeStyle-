"""
patch_source.py — patch 内存中所有源 ItemCode 出现的位置

思路: 游戏进商城时从持久化数据拷贝描述符。patch 源数据后,
拷贝出来的就是改过的值。

用法: py patch_source.py <src_itemcode> <dst_itemcode>
  PID 自动检测
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.pattern, pymem.process

VT = 0x027FCEA0

def main():
    # 自动获取 PID
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe not running")
        return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] Run as Administrator")
        return

    if len(sys.argv) < 3:
        print("Usage: py patch_source.py <src_itemcode> <dst_itemcode>")
        print("  PID auto-detected")
        pm.close_process()
        return

    src = int(sys.argv[1])
    dst = int(sys.argv[2])

    pid = pm.process_id
    print(f"PID={pid}  {src} -> {dst}")
    mod = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
    mod_end = mod.lpBaseOfDll + mod.SizeOfImage

    # 搜索所有出现 src ItemCode 的位置
    needle = struct.pack("<I", src)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, needle, return_multiple=True)
    print(f"\nFound {len(hits)} occurrences of ItemCode {src}:")

    patched = []
    for addr in hits:
        in_module = addr < mod_end
        location = "module" if in_module else "heap"
        try:
            ctx_before = pm.read_bytes(addr - 4, 4)
            ctx_after = pm.read_bytes(addr + 4, 4)
            before_val = struct.unpack_from("<I", ctx_before)[0]
            after_val = struct.unpack_from("<I", ctx_after)[0]

            # 检查前面是否是描述符 vtable
            is_descriptor = False
            try:
                desc_start = addr - 0x060
                vt_check = struct.unpack_from("<I", pm.read_bytes(desc_start, 4))[0]
                if vt_check == VT:
                    is_descriptor = True
            except:
                pass

            label = f"{location}  is_desc={is_descriptor}"
            print(f"  0x{addr:08X}  {label}  prev=0x{before_val:08X}  next=0x{after_val:08X}")

            # 只 patch 描述符位置 (有 vtable 标记的)
            if is_descriptor:
                pm.write_int(addr, dst)
                patched.append(addr)
                print(f"    -> PATCHED (descriptor)")
            else:
                print(f"    -> skipped (not descriptor)")
        except Exception as e:
            print(f"  0x{addr:08X}  {location}  (read error: {e})")

    print(f"\nPatched {len(patched)}/{len(hits)} locations")
    print(f"\nNow enter shop and test. Press Enter to RESTORE...")
    input()

    # 恢复
    for addr in patched:
        try:
            pm.write_int(addr, src)
        except:
            pass
    print(f"Restored {len(patched)} locations")
    pm.close_process()

if __name__ == "__main__":
    main()

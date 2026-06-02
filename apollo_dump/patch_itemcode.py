"""
patch_itemcode.py — 修改描述符 ItemCode (watch 模式)

用法: py patch_itemcode.py <pid> <src_itemcode> <dst_itemcode>
例:   py patch_itemcode.py 15676 50125691 50125721

watch 模式: 持续监控，描述符被重建后自动重新 patch。
退出商城重进也会自动生效，Ctrl+C 停止并恢复。
"""
import struct, sys, time
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.pattern, pymem.process

VT = 0x027FCEA0
SCAN_INTERVAL = 0.05  # 50ms

def find_descriptor(pm, mod_end, itemcode):
    vt_bytes = struct.pack("<I", VT)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, vt_bytes, return_multiple=True)
    heap = [a for a in (hits or []) if a > mod_end]
    for addr in heap:
        try:
            raw = pm.read_bytes(addr + 0x060, 4)
            ic = struct.unpack_from("<I", raw)[0]
            if ic == itemcode:
                return addr
        except:
            pass
    return None

def find_descriptor_fast(pm, mod_end, itemcode, known_regions):
    """只在已知区域搜索, 比全内存扫描快"""
    vt_bytes = struct.pack("<I", VT)
    for base in known_regions:
        try:
            # 搜索 64KB 范围
            data = pm.read_bytes(base, 0x10000)
            pos = 0
            while True:
                idx = data.find(vt_bytes, pos)
                if idx < 0:
                    break
                addr = base + idx
                try:
                    ic = struct.unpack_from("<I", pm.read_bytes(addr + 0x060, 4))[0]
                    if ic == itemcode:
                        return addr
                except:
                    pass
                pos = idx + 1
        except:
            pass
    return None

def main():
    if len(sys.argv) < 3:
        print("Usage: py patch_itemcode.py <src_itemcode> <dst_itemcode> [pid]")
        print("  src = 商城里你点击试用的物品")
        print("  dst = 想要伪装成的物品外观")
        print("  例: py patch_itemcode.py 50125691 50125721")
        return

    src = int(sys.argv[1])
    dst = int(sys.argv[2])

    if len(sys.argv) >= 4:
        pid = int(sys.argv[3])
    else:
        import subprocess
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                           capture_output=True, text=True)
        pid = None
        for line in r.stdout.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].isdigit():
                pid = int(parts[1])
                break
        if not pid:
            print("FreeStyle.exe not found"); return

    try:
        pm = pymem.Pymem(pid)
    except pymem.exception.CouldNotOpenProcess:
        print("Run as Administrator"); return
    print(f"PID={pid}  src={src} -> dst={dst}")
    mod = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
    mod_end = mod.lpBaseOfDll + mod.SizeOfImage

    patched_addr = None
    known_regions = []  # 记住描述符曾经出现的内存区域

    print("Watching... (Ctrl+C to stop and restore)\n")

    try:
        while True:
            if patched_addr:
                # 检查已有地址是否还有效
                try:
                    current = struct.unpack_from("<I", pm.read_bytes(patched_addr + 0x060, 4))[0]
                    if current == dst:
                        time.sleep(SCAN_INTERVAL)
                        continue
                    elif current == src:
                        pm.write_int(patched_addr + 0x060, dst)
                        print(f"  [{time.strftime('%H:%M:%S')}] Re-patched @ 0x{patched_addr:08X}")
                        time.sleep(SCAN_INTERVAL)
                        continue
                    else:
                        patched_addr = None
                        print(f"  [{time.strftime('%H:%M:%S')}] Descriptor freed, rescanning...")
                except:
                    patched_addr = None
                    print(f"  [{time.strftime('%H:%M:%S')}] Address invalid, rescanning...")

            # 先快速搜索已知区域
            addr = None
            if known_regions:
                addr = find_descriptor_fast(pm, mod_end, src, known_regions)

            # 快速搜索没找到, 全内存扫描
            if not addr:
                addr = find_descriptor(pm, mod_end, src)
                if addr:
                    # 记住这个区域 (64KB 对齐)
                    region_base = (addr & ~0xFFFF)
                    if region_base not in known_regions:
                        known_regions.append(region_base)
                        print(f"  [+] New region 0x{region_base:08X}")

            if addr:
                patched_addr = addr
                pm.write_int(addr + 0x060, dst)
                print(f"  [{time.strftime('%H:%M:%S')}] Patched {src}->{dst} @ 0x{addr:08X}")
            else:
                print(f"  [{time.strftime('%H:%M:%S')}] Waiting for {src}...")

            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n  Restoring...")
        if patched_addr:
            try:
                pm.write_int(patched_addr + 0x060, src)
                print(f"  Restored {src} @ 0x{patched_addr:08X}")
            except:
                print("  Could not restore (address invalid)")
        pm.close_process()
        print("Done.")

if __name__ == "__main__":
    main()

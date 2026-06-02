"""
阶段1: Pymem 扫描 ItemCode 定位头发 Actor 真实类

默认发型: 美丽梦想发型 (ItemCode 25461 = 0x6375)
对比发型: 破坏者超赛发型 (ItemCode 50125031, 动态)

用法:
  py scan_itemcode.py              # 单次扫描 (美丽梦想 25461)
  py scan_itemcode.py 50125031     # 扫描指定 ItemCode
  py scan_itemcode.py --diff       # 前后对比: 记录25461, 切换发型, 再扫25461, 找消失的地址
  py scan_itemcode.py --compare    # 对比静态vs动态的 vtable
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")

import pymem
import pymem.process
import pymem.memory
import pymem.exception

PROCESS_NAME = "FreeStyle.exe"

KNOWN_VTABLES = {
    0x0284E114: "DStaticActor",
    0x0284AA4C: "DDynamicActor",
}

STATIC_ITEMCODE = 25461
DYNAMIC_ITEMCODE = 50125031

VTABLE_RANGE_START = 0x00400000
VTABLE_RANGE_END = 0x02D00000

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000


def scan_addresses(pm, itemcode):
    pattern = struct.pack("<i", itemcode)
    print(f"\n[*] 扫描 ItemCode={itemcode} (0x{itemcode:X}), 字节: {pattern.hex()}")

    addresses = set()
    addr = HEAP_MIN
    scanned = 0
    regions = 0

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

        scanned += r_size
        regions += 1

        pos = 0
        while True:
            idx = data.find(pattern, pos)
            if idx < 0:
                break
            addresses.add(r_base + idx)
            pos = idx + 1

        addr = next_addr

    print(f"  [{regions} 区域, {scanned // 1024 // 1024}MB] {len(addresses)} 处命中")
    return addresses


def find_vtable_backwards(pm, hit_addr, max_backtrack=0x800):
    search_start = max(hit_addr - max_backtrack, HEAP_MIN)
    try:
        context = pm.read_bytes(search_start, hit_addr - search_start + 4)
    except Exception:
        return None, -1

    item_off = hit_addr - search_start

    for backtrack in range(0, max_backtrack, 4):
        off = item_off - backtrack
        if off < 4:
            break
        val = struct.unpack_from("<I", context, off)[0]
        if VTABLE_RANGE_START <= val <= VTABLE_RANGE_END and (val & 3) == 0:
            return val, backtrack

    return None, -1


def dump_hex(pm, addr, size=0x200):
    try:
        data = pm.read_bytes(addr, size)
    except Exception:
        print(f"  读取 0x{addr:08X} 失败")
        return
    print(f"  内存转储 0x{addr:08X} - 0x{addr + size:08X}:")
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"    0x{addr + i:08X}: {hex_part:<48s} {ascii_part}")


def analyze_address(pm, addr, label=""):
    vtable_val, backtrack = find_vtable_backwards(pm, addr)
    if vtable_val is not None:
        obj_start = addr - backtrack
        class_name = KNOWN_VTABLES.get(vtable_val, "未知类")
        print(f"\n  {label}0x{addr:08X} -> vtable=0x{vtable_val:08X} ({class_name}), obj=0x{obj_start:08X}, off=+0x{backtrack:X}")
        dump_hex(pm, obj_start, min(backtrack + 0x80, 0x300))
    else:
        print(f"\n  {label}0x{addr:08X} -> 无 vtable")
        dump_hex(pm, max(addr - 0x40, HEAP_MIN), 0x100)


def mode_single(pm, itemcode):
    addrs = scan_addresses(pm, itemcode)
    print(f"\n[*] 分析前 20 个命中的上下文...")
    for i, addr in enumerate(sorted(addrs)[:20]):
        analyze_address(pm, addr, f"[{i}] ")


def mode_diff(pm):
    print("\n" + "=" * 70)
    print("  前后对比模式: 通过切换发型定位发型专属内存")
    print("=" * 70)
    print(f"\n  原理: 扫描 ItemCode={STATIC_ITEMCODE} 的所有地址,")
    print(f"  然后你切换发型, 再扫一次, 消失的地址 = 发型专属!")

    print(f"\n[步骤1] 请确保当前装备: 美丽梦想发型 (ItemCode={STATIC_ITEMCODE})")
    input("装备好后按 Enter 开始第一次扫描...")

    print(f"\n[*] 第一次扫描...")
    before = scan_addresses(pm, STATIC_ITEMCODE)
    print(f"[*] 记录了 {len(before)} 个地址")

    print(f"\n[步骤2] 请切换为其他发型 (任意不同发型即可)")
    input("切换好后按 Enter 开始第二次扫描...")

    print(f"\n[*] 第二次扫描...")
    after = scan_addresses(pm, STATIC_ITEMCODE)
    print(f"[*] 记录了 {len(after)} 个地址")

    disappeared = before - after
    appeared = after - before
    persistent = before & after

    print(f"\n{'=' * 70}")
    print(f"  对比结果")
    print(f"{'=' * 70}")
    print(f"  第一次: {len(before)} 个")
    print(f"  第二次: {len(after)} 个")
    print(f"  消失的: {len(disappeared)} 个 <-- 发型专属!")
    print(f"  新增的: {len(appeared)} 个")
    print(f"  持续的: {len(persistent)} 个 (缓存/数据库副本)")

    if disappeared:
        print(f"\n--- 消失的地址 (发型专属) ---")
        sorted_dis = sorted(disappeared)
        for i, addr in enumerate(sorted_dis[:30]):
            analyze_address(pm, addr, f"[消失{i}] ")
        if len(sorted_dis) > 30:
            print(f"\n  ... 还有 {len(sorted_dis) - 30} 个")

        print(f"\n--- 消失地址的区域分布 ---")
        region_map = {}
        for addr in sorted_dis:
            key = addr & ~0xFFFF
            region_map[key] = region_map.get(key, 0) + 1
        for key, count in sorted(region_map.items(), key=lambda x: -x[1])[:10]:
            print(f"  区域 0x{key:08X}: {count} 个")

    if appeared:
        print(f"\n--- 新增的地址 ---")
        for i, addr in enumerate(sorted(appeared)[:10]):
            print(f"  [新增{i}] 0x{addr:08X}")


def mode_compare(pm):
    print("\n" + "=" * 70)
    print("  静态 vs 动态 vtable 对比")
    print("=" * 70)

    print(f"\n[步骤1] 请确保装备: 美丽梦想发型 (静态)")
    input("装备好后按 Enter 扫描...")
    static_addrs = scan_addresses(pm, STATIC_ITEMCODE)

    static_vts = {}
    for addr in sorted(static_addrs):
        vt, bt = find_vtable_backwards(pm, addr)
        if vt is not None:
            static_vts[addr - bt] = (vt, bt, addr)
    print(f"  {len(static_vts)} 个带 vtable 的对象")

    print(f"\n[步骤2] 请切换为: 破坏者超赛发型 (动态)")
    input("切换好后按 Enter 扫描...")
    dynamic_addrs = scan_addresses(pm, DYNAMIC_ITEMCODE)

    dynamic_vts = {}
    for addr in sorted(dynamic_addrs):
        vt, bt = find_vtable_backwards(pm, addr)
        if vt is not None:
            dynamic_vts[addr - bt] = (vt, bt, addr)
    print(f"  {len(dynamic_vts)} 个带 vtable 的对象")

    s_vts = {v[0] for v in static_vts.values()}
    d_vts = {v[0] for v in dynamic_vts.values()}

    print(f"\n  静态 vtable: {['0x%08X' % v for v in sorted(s_vts)]}")
    print(f"  动态 vtable: {['0x%08X' % v for v in sorted(d_vts)]}")
    if s_vts - d_vts:
        print(f"  仅静态: {['0x%08X' % v for v in sorted(s_vts - d_vts)]}")
    if d_vts - s_vts:
        print(f"  仅动态: {['0x%08X' % v for v in sorted(d_vts - s_vts)]}")


class Tee:
    def __init__(self, path):
        self.file = open(path, 'w', encoding='utf-8')
        self.stdout = sys.stdout
    def write(self, s):
        self.stdout.write(s)
        self.file.write(s)
    def flush(self):
        self.stdout.flush()
        self.file.flush()
    def close(self):
        self.file.close()

def main():
    tee = Tee(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_result.txt'))
    sys.stdout = tee
    print("=" * 70)
    print("  FreeStyle 阶段1: ItemCode 扫描定位头发 Actor")
    print("=" * 70)

    target = STATIC_ITEMCODE
    mode = "single"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--diff":
            mode = "diff"
        elif arg == "--compare":
            mode = "compare"
        elif arg == "--dynamic":
            target = DYNAMIC_ITEMCODE
        else:
            try:
                target = int(arg)
            except ValueError:
                print(f"[ERROR] 用法: py scan_itemcode.py [ItemCode|--diff|--compare|--dynamic]")
                return

    try:
        pm = pymem.Pymem(PROCESS_NAME)
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe 未运行")
        return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] 无法打开进程, 请以管理员权限运行")
        return

    print(f"[OK] PID={pm.process_id}, 基址=0x{pm.base_address:08X}")

    if mode == "diff":
        mode_diff(pm)
    elif mode == "compare":
        mode_compare(pm)
    else:
        mode_single(pm, target)

    pm.close_process()
    print(f"\n[*] 完成")
    sys.stdout = tee.stdout
    tee.close()
    print(f"结果已写入 scan_result.txt")


if __name__ == "__main__":
    main()

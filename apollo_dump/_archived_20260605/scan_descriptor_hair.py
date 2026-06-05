"""
描述符 + Actor 追踪扫描器

策略：
1. 扫描描述符 vtable (0x027FCEA0) 定位所有描述符
2. 读取 ItemCode (+0x060), subtype (+0x058), category (+0x04C)
3. 过滤发型 (501xxxxx) 并转储完整结构
4. 追踪描述符 +0x0F0/0x0F4 指针 → 是否指向 Actor 对象

用法（管理员）:
  py scan_descriptor_hair.py                          # 扫描所有描述符
  py scan_descriptor_hair.py 50125711                 # 扫描指定 ItemCode
  py scan_descriptor_hair.py --trace 50125711          # 追踪描述符指针
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")

import pymem
import pymem.process
import pymem.memory

PROCESS_NAME = "FreeStyle.exe"
DESC_VTABLE = b"\xA0\xCE\x7F\x02"  # 0x027FCEA0 little-endian

ACTOR_VTABLES = {
    0x0284AA4C: "DDynamicActor",
    0x0284E114: "DStaticActor",
}

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000
VTABLE_RANGE = (0x00400000, 0x02D00000)

DESC_FIELDS = [
    (0x000, "vtable", "<I"),
    (0x00C, "outer_obj_ptr", "<I"),
    (0x040, "flag_040", "<I"),
    (0x04C, "category", "<I"),
    (0x058, "subtype", "<I"),
    (0x05C, "flag_05C", "<I"),
    (0x060, "ItemCode", "<I"),
    (0x064, "flag_064", "<I"),
    (0x068, "unknown_068", "<I"),
    (0x080, "flag_080", "<I"),
    (0x084, "flag_084", "<I"),
    (0x098, "data_098", "<I"),
    (0x09C, "data_09C", "<I"),
    (0x0A0, "data_0A0", "<I"),
    (0x0A4, "data_0A4", "<I"),
    (0x0A8, "data_0A8", "<I"),
    (0x0E0, "flag_0E0", "<I"),
    (0x0EC, "flag_0EC", "<I"),
    (0x0F0, "ptr_0F0", "<I"),
    (0x0F4, "ptr_0F4", "<I"),
    (0x100, "data_100", "<I"),
    (0x104, "ptr_104", "<I"),
    (0x10C, "data_10C", "<I"),
    (0x114, "data_114", "<I"),
    (0x120, "data_120", "<I"),
    (0x124, "data_124", "<I"),
    (0x138, "data_138", "<I"),
    (0x144, "data_144", "<I"),
    (0x148, "data_148", "<I"),
    (0x14C, "data_14C", "<I"),
    (0x150, "data_150", "<I"),
    (0x158, "data_158", "<I"),
    (0x460, "phys_param1", "<f"),
    (0x464, "phys_param2", "<f"),
]


def get_pm():
    try:
        pm = pymem.Pymem(PROCESS_NAME)
        print(f"[OK] PID={pm.process_id}")
        return pm
    except Exception as e:
        print(f"[ERR] {e}")
        sys.exit(1)


def scan_vtable_pattern(pm, pattern: bytes, label=""):
    results = []
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
        r_end = min(next_addr, HEAP_MAX)
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
            idx = data.find(pattern, pos)
            if idx < 0:
                break
            results.append(r_base + idx)
            pos = idx + 1
        addr = next_addr
    return results


def read_u32(pm, addr, offset=0):
    try:
        return struct.unpack("<I", pm.read_bytes(addr + offset, 4))[0]
    except Exception:
        return None


def read_bytes(pm, addr, size):
    try:
        return pm.read_bytes(addr, size)
    except Exception:
        return None


def check_is_actor(pm, addr):
    """检查 addr 是否是 Actor 对象 (vtable 匹配)"""
    v = read_u32(pm, addr, 0)
    if v in ACTOR_VTABLES:
        return ACTOR_VTABLES[v]
    return None


def dump_descriptor(pm, addr, label=""):
    ic = read_u32(pm, addr, 0x060)
    subtype = read_u32(pm, addr, 0x058)
    cat = read_u32(pm, addr, 0x04C)
    ptr_0F0 = read_u32(pm, addr, 0x0F0)
    ptr_0F4 = read_u32(pm, addr, 0x0F4)

    print(f"\n{'='*60}")
    print(f"  {label}描述符 @ 0x{addr:08X}")
    print(f"{'='*60}")
    print(f"  ItemCode: {ic}  |  subtype: {subtype}  |  category: {cat}")

    for off, name, fmt in DESC_FIELDS:
        try:
            val = struct.unpack(fmt, pm.read_bytes(addr + off, struct.calcsize(fmt)))[0]
            extra = ""
            if name == "vtable":
                extra = f" ({ACTOR_VTABLES.get(val, '描述符')})"
            elif name.startswith("ptr_"):
                target = check_is_actor(pm, val)
                if target:
                    extra = f" → [Actor] {target} @ 0x{val:08X}"
                elif HEAP_MIN <= val <= HEAP_MAX:
                    extra = f" (heap ptr)"
            print(f"    +0x{off:03X} ({name}): {val}{extra}")
        except Exception:
            pass

    # 检查 ptr_0F0 和 ptr_0F4 是否指向 Actor
    for ptr_name, ptr_val in [("ptr_0F0", ptr_0F0), ("ptr_0F4", ptr_0F4)]:
        if ptr_val and HEAP_MIN <= ptr_val <= HEAP_MAX:
            actor_type = check_is_actor(pm, ptr_val)
            if actor_type:
                print(f"\n  ★ {ptr_name} @ 0x{ptr_val:08X} = {actor_type}!")
                dump_actor_quick(pm, ptr_val)


def dump_actor_quick(pm, addr):
    motion = read_u32(pm, addr, 0x0C0)
    flags = read_u32(pm, addr, 0x074)
    phys1 = struct.unpack("<f", pm.read_bytes(addr + 0x460, 4))[0] if read_u32(pm, addr, 0x460) is not None else 0

    print(f"      Motion: {motion} ({'Dynamic' if motion == 11 else 'Static' if motion == 12 else '?'})")
    print(f"      Flags +0x074: 0x{flags:08X} (phys_enabled={bool(flags & 0x18)})")
    print(f"      PhysParam1: {phys1}")

    for off in range(0, 0x100, 16):
        data = read_bytes(pm, addr + off, 16)
        if data:
            hex_part = " ".join(f"{b:02x}" for b in data)
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            marker = ""
            if off == 0x0C0: marker = " <-- MotionType"
            elif off == 0x074: marker = " <-- PhysicsFlags"
            print(f"      0x{addr+off:08X}: {hex_part} {asc}{marker}")


def mode_scan_all(pm):
    print("\n扫描描述符 vtable (0x027FCEA0)...")
    hits = scan_vtable_pattern(pm, DESC_VTABLE)
    print(f"找到 {len(hits)} 个描述符\n")

    hairs = []
    for addr in hits:
        ic = read_u32(pm, addr, 0x060)
        cat = read_u32(pm, addr, 0x04C)
        subtype = read_u32(pm, addr, 0x058)

        if ic and (str(ic).startswith("501") or cat == 3):
            hairs.append((addr, ic, subtype, cat))

    print(f"其中发型相关: {len(hairs)} 个\n")

    for addr, ic, subtype, cat in sorted(hairs, key=lambda x: x[1]):
        print(f"  0x{addr:08X} | ItemCode={ic} | subtype={subtype} | category={cat}")

    if hairs:
        print("\n--- 详细转储 ---")
        for addr, ic, subtype, cat in sorted(hairs, key=lambda x: x[1]):
            dump_descriptor(pm, addr, f"[发型] ")
    else:
        print("\n未找到发型描述符。尝试扫描所有 ItemCode 5012xxxx...")

        for itemcode in [50125671, 50125681, 50125691, 50125701, 50125711, 50125721]:
            print(f"\n搜索 ItemCode={itemcode} 在描述符中...")
            for addr in hits:
                ic = read_u32(pm, addr, 0x060)
                if ic == itemcode:
                    dump_descriptor(pm, addr, f"[{itemcode}] ")


def mode_single(pm, itemcode):
    print(f"\n搜索 ItemCode={itemcode}...")
    hits = scan_vtable_pattern(pm, DESC_VTABLE)

    found = []
    for addr in hits:
        ic = read_u32(pm, addr, 0x060)
        if ic == itemcode:
            found.append(addr)

    if not found:
        print(f"未找到 ItemCode={itemcode} 的描述符")
        return

    for addr in found:
        dump_descriptor(pm, addr, f"[{itemcode}] ")


def mode_trace(pm, itemcode):
    print(f"\n追踪 ItemCode={itemcode} 的描述符指针...")
    hits = scan_vtable_pattern(pm, DESC_VTABLE)

    desc_addrs = []
    for addr in hits:
        ic = read_u32(pm, addr, 0x060)
        if ic == itemcode:
            desc_addrs.append(addr)

    if not desc_addrs:
        print(f"未找到描述符")
        return

    for desc_addr in desc_addrs:
        print(f"\n{'='*60}")
        print(f"  描述符 @ 0x{desc_addr:08X}")
        dump_descriptor(pm, desc_addr, "[追踪] ")

        for ptr_off, ptr_name in [(0x0F0, "ptr_0F0"), (0x0F4, "ptr_0F4"), (0x104, "ptr_104")]:
            ptr_val = read_u32(pm, desc_addr, ptr_off)
            if not ptr_val or ptr_val < HEAP_MIN or ptr_val > HEAP_MAX:
                continue

            actor_type = check_is_actor(pm, ptr_val)
            if actor_type:
                print(f"\n  ★ {ptr_name} → Actor ({actor_type}) @ 0x{ptr_val:08X}")
                dump_actor_quick(pm, ptr_val)

            next_val = read_u32(pm, ptr_val, 0)
            if next_val and next_val in ACTOR_VTABLES:
                print(f"  ★ [{ptr_name}]→[+0x00] → Actor @ 0x{ptr_val:08X}")
                dump_actor_quick(pm, ptr_val)

        for off in range(0, 0x120, 4):
            check_val = read_u32(pm, desc_addr, off)
            if check_val and check_val in ACTOR_VTABLES:
                print(f"\n  ★ 描述符+0x{off:03X} 直接指向 Actor vtable !")
                obj_start = desc_addr + off
                for backtrack in range(0, min(off, 0x200), 4):
                    if read_u32(pm, obj_start - backtrack, 0) == check_val:
                        dump_actor_quick(pm, obj_start - backtrack)
                        break


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
    tee = Tee(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'desc_scan_result.txt'))
    sys.stdout = tee

    print("=" * 60)
    print("  描述符 + Actor 追踪扫描器")
    print("=" * 60)

    pm = get_pm()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--trace" and len(sys.argv) > 2:
            mode_trace(pm, int(sys.argv[2]))
        else:
            try:
                mode_single(pm, int(sys.argv[1]))
            except ValueError:
                print(f"用法: py scan_descriptor_hair.py [ItemCode|--trace <ItemCode>]")
    else:
        mode_scan_all(pm)

    pm.close_process()
    sys.stdout = tee.stdout
    tee.close()
    print(f"\n结果已写入 desc_scan_result.txt")


if __name__ == "__main__":
    main()
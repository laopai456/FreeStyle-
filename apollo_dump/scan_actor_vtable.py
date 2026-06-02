"""
Actor 对象扫描器：按 vtable 找 DDynamicActor / DStaticActor

用法（管理员）:
  py scan_actor_vtable.py                    # 扫描所有 Actor
  py scan_actor_vtable.py --dump <addr>      # 转储指定地址的 Actor
  py scan_actor_vtable.py --patch-static     # 尝试把 DStatic → DDynamic

已知:
  DDynamicActor vtable = 0x0284AA4C
  DStaticActor  vtable = 0x0284E114
  Actor+0x0C0: MotionType FName 索引 (11=Dynamic, 12=Static)
  Actor+0x074: Flags (&0x18 启用物理)
  Actor+0x460: 物理参数1 (非零=启用)
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

VTABLES = {
    0x0284AA4C: "DDynamicActor",
    0x0284E114: "DStaticActor",
}

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000
VTABLE_RANGE_START = 0x00400000
VTABLE_RANGE_END = 0x02D00000

KNOWN_OFFSETS = {
    0x000: "vtable",
    0x00C: "outer_object",
    0x040: "flag_040",
    0x04C: "category",
    0x058: "subtype",
    0x05C: "physics_flag",
    0x060: "ItemCode",
    0x064: "flag_064",
    0x068: "flag_068",
    0x074: "physics_flags",
    0x080: "flag_080",
    0x084: "flag_084",
    0x0C0: "motion_type",
    0x460: "physics_param1",
    0x464: "physics_param2",
}


def get_pm():
    try:
        pm = pymem.Pymem(PROCESS_NAME)
        print(f"[OK] PID={pm.process_id}, 基址=0x{pm.base_address:08X}")
        return pm
    except Exception as e:
        print(f"[ERR] 无法打开进程: {e}")
        print("请确保 FreeStyle.exe 正在运行，且以管理员权限执行此脚本")
        sys.exit(1)


def scan_vtable(pm, vtable_val, label=""):
    pattern = struct.pack("<I", vtable_val)
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


def read_field(pm, obj_addr, offset, fmt="<I"):
    try:
        val = struct.unpack(fmt, pm.read_bytes(obj_addr + offset, struct.calcsize(fmt)))[0]
        return val
    except Exception:
        return None


def read_bytes(pm, addr, size):
    try:
        return pm.read_bytes(addr, size)
    except Exception:
        return None


def dump_actor(pm, obj_addr, label=""):
    name = "?"
    for vt, n in VTABLES.items():
        v = read_field(pm, obj_addr, 0)
        if v == vt:
            name = n
            break

    itemcode = read_field(pm, obj_addr, 0x060)
    motion_type = read_field(pm, obj_addr, 0x0C0)
    physics_flags = read_field(pm, obj_addr, 0x074)
    phys1 = read_field(pm, obj_addr, 0x460)
    phys2 = read_field(pm, obj_addr, 0x464)

    print(f"\n{'='*60}")
    print(f"  {label}Actor @ 0x{obj_addr:08X} ({name})")
    print(f"{'='*60}")
    print(f"  ItemCode:     {itemcode}")
    print(f"  Motion Type:  {motion_type} ({'Dynamic' if motion_type == 11 else 'Static' if motion_type == 12 else '?'})")
    print(f"  Flags +0x074: 0x{physics_flags:08X} (phys_enabled={bool(physics_flags & 0x18)})")
    print(f"  PhysParam1:   {phys1}")
    print(f"  PhysParam2:   {phys2}")

    print(f"\n  --- 原始内存 (0x00-0x80) ---")
    data = read_bytes(pm, obj_addr, 0x80)
    if data:
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            off_label = KNOWN_OFFSETS.get(i, "")
            if off_label:
                print(f"    0x{obj_addr+i:08X}: {hex_part:<48s} {ascii_part}  <-- {off_label}")
            else:
                print(f"    0x{obj_addr+i:08X}: {hex_part:<48s} {ascii_part}")

    print(f"\n  --- 特征字段 ---")
    for off, label in sorted(KNOWN_OFFSETS.items()):
        if off > 0x80 and off <= 0x470:
            val = read_field(pm, obj_addr, off)
            if val is not None:
                extra = ""
                if off == 0x0C0:
                    extra = f" ({'Dynamic' if val == 11 else 'Static' if val == 12 else '?'})"
                elif off >= 0x460:
                    extra = f" (phys_param)"
                print(f"    +0x{off:03X} ({label}): {val}{extra}")


def mode_scan(pm):
    print("\n" + "=" * 60)
    print("  扫描 Actor 对象 (按 vtable)")
    print("=" * 60)

    for vt, name in sorted(VTABLES.items(), key=lambda x: -x[0]):
        print(f"\n[*] 扫描 {name} (vtable=0x{vt:08X})...")
        hits = scan_vtable(pm, vt, name)
        print(f"  → 找到 {len(hits)} 个对象")

        for i, addr in enumerate(hits[:20]):
            itemcode = read_field(pm, addr, 0x060)
            motion = read_field(pm, addr, 0x0C0)
            flags = read_field(pm, addr, 0x074)
            phys = read_field(pm, addr, 0x460)
            print(f"    [{i}] 0x{addr:08X} | ItemCode={itemcode} | Motion={motion} | Flags=0x{flags:08X} | Phys={phys}")

        if len(hits) > 20:
            print(f"    ... 还有 {len(hits) - 20} 个")

    item_to_find = input("\n输入 ItemCode 过滤 (直接回车跳过): ").strip()
    if item_to_find:
        try:
            ic = int(item_to_find)
        except ValueError:
            ic = None
        if ic:
            print(f"\n[*] 搜索 ItemCode={ic} 的 Actor...")
            for vt, name in sorted(VTABLES.items(), key=lambda x: -x[0]):
                hits = scan_vtable(pm, vt, name)
                for addr in hits:
                    itemcode = read_field(pm, addr, 0x060)
                    if itemcode == ic:
                        dump_actor(pm, addr, f"[{name}] ")


def mode_dump(pm, addr_str):
    try:
        if addr_str.startswith("0x") or addr_str.startswith("0X"):
            addr = int(addr_str, 16)
        else:
            addr = int(addr_str)
    except ValueError:
        print(f"[ERR] 无效地址: {addr_str}")
        return
    dump_actor(pm, addr, "[手动] ")


def mode_patch_static(pm):
    print("\n" + "=" * 60)
    print("  尝试: DStaticActor → DDynamicActor 补丁")
    print("  ⚠️  高风险! 可能导致崩溃")
    print("=" * 60)

    target_ic = input("目标 ItemCode (默认 50125691): ").strip()
    if not target_ic:
        target_ic = "50125691"

    try:
        ic = int(target_ic)
    except ValueError:
        print("[ERR] 无效 ItemCode")
        return

    hits = scan_vtable(pm, VTABLES[0x0284E114], "DStaticActor")
    targets = []
    for addr in hits:
        itemcode = read_field(pm, addr, 0x060)
        if itemcode == ic:
            targets.append(addr)

    if not targets:
        print(f"[ERR] 没有找到 ItemCode={ic} 的 DStaticActor")
        return

    print(f"[OK] 找到 {len(targets)} 个匹配的 Actor:")
    for addr in targets:
        dump_actor(pm, addr)

    confirm = input(f"\n⚠️  确认修改? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("[SKIP] 已取消")
        return

    for addr in targets:
        old_vt = read_field(pm, addr, 0)
        dd_vt = 0x0284AA4C
        try:
            pm.write_bytes(addr, struct.pack("<I", dd_vt), 4)
            print(f"[OK] 0x{addr:08X}: vtable {old_vt:08X} → {dd_vt:08X} (DStatic→DDynamic)")

            old_flags = read_field(pm, addr, 0x074)
            new_flags = old_flags | 0x18
            pm.write_bytes(addr + 0x074, struct.pack("<I", new_flags), 4)
            print(f"[OK] +0x074 flags: {old_flags:08X} → {new_flags:08X} (启用物理标志)")

            old_phys = read_field(pm, addr, 0x460)
            if old_phys == 0:
                pm.write_bytes(addr + 0x460, struct.pack("<f", 1.0), 4)
                print(f"[OK] +0x460 phys_param: 0 → 1.0")

            print(f"\n[OK] 补丁完成! 进入游戏查看效果。")
            print(f"[!] 如果崩溃: 角色创建 Actor 时 vtable 不匹配 → 说明基类构造不同")
            print(f"[!] 如果无效果: 还有前置条件不满足 → 需要 Hook CharacterMotion 解析")
        except Exception as e:
            print(f"[ERR] 写入失败: {e}")


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
    tee = Tee(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'actor_scan_result.txt'))
    sys.stdout = tee

    print("=" * 60)
    print("  FreeStyle Actor vtable 扫描器")
    print("=" * 60)

    pm = get_pm()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--dump" and len(sys.argv) > 2:
            mode_dump(pm, sys.argv[2])
        elif sys.argv[1] == "--patch-static":
            mode_patch_static(pm)
        else:
            print(f"用法:")
            print(f"  py scan_actor_vtable.py                          # 扫描所有 Actor")
            print(f"  py scan_actor_vtable.py --dump <addr>            # 转储指定地址")
            print(f"  py scan_actor_vtable.py --patch-static           # 尝试补丁")
    else:
        mode_scan(pm)

    pm.close_process()
    print(f"\n[*] 完成")
    sys.stdout = tee.stdout
    tee.close()


if __name__ == "__main__":
    main()
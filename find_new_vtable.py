"""
find_new_vtable.py — 游戏更新后重新定位描述符 vtable

思路：直接扫描已知 ItemCode (uint32 LE)，从命中地址向前搜索对象起始处的 vtable 指针。
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.pattern, pymem.process

KNOWN = {
    50125691: "黑金热血青春发型",
    50125701: "紫色护目镜马尾辫",
    50125721: "粉色超级赛亚人3",
}

DESC_SIZE = 0x100  # 假设描述符最大 0x100 字节
IC_OFFSET = 0x060  # ItemCode 在描述符内的偏移 (旧值，可能变了)

pm = pymem.Pymem("FreeStyle.exe")
print(f"PID={pm.process_id}")

mod = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
mod_end = mod.lpBaseOfDll + mod.SizeOfImage
print(f"Module: 0x{mod.lpBaseOfDll:08X} - 0x{mod_end:08X}")

# Step 1: 对每个 ItemCode 做全内存扫描
all_hits = {}  # itemcode -> [heap addrs]
for ic, name in KNOWN.items():
    needle = struct.pack("<I", ic)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, needle, return_multiple=True)
    heap_hits = [a for a in (hits or []) if a > mod_end]
    all_hits[ic] = heap_hits
    print(f"\n  {ic} ({name}): {len(heap_hits)} heap hits")
    for a in heap_hits[:5]:
        print(f"    0x{a:08X}")

# Step 2: 找交集 — 同一个描述符对象的 ItemCode 偏移
# 如果 IC_OFFSET 没变，描述符起始 = hit_addr - IC_OFFSET
# 多个 ItemCode 的描述符起始处的 vtable 应该相同
print("\n--- Trying old IC_OFFSET=0x060 ---")
vtable_candidates = {}
for ic, addrs in all_hits.items():
    for a in addrs:
        desc_start = a - IC_OFFSET
        if desc_start > mod_end:
            try:
                vt = struct.unpack_from("<I", pm.read_bytes(desc_start, 4))[0]
                if mod.lpBaseOfDll <= vt < mod_end:
                    vtable_candidates.setdefault(vt, []).append((ic, desc_start))
            except:
                pass

if vtable_candidates:
    for vt, items in sorted(vtable_candidates.items(), key=lambda x: -len(x[1])):
        ics = set(ic for ic, _ in items)
        if len(ics) >= 2:
            print(f"  vtable=0x{vt:08X}  matches={len(items)}  ItemCodes={sorted(ics)}")

# Step 3: 如果旧偏移不行，暴力搜索每个 hit 之前的 vtable
print("\n--- Brute-force: scanning backwards for vtable ptr ---")
# 对每个 ItemCode 的 hit，向前读 DESC_SIZE 字节，找第一个有效指针（指向 module 内）
vtable_map = {}  # vtable -> count
for ic, addrs in all_hits.items():
    for a in addrs:
        # 向前扫描最多 DESC_SIZE 字节
        for off in range(0, DESC_SIZE, 4):
            check = a - off
            if check <= mod_end:
                continue
            try:
                val = struct.unpack_from("<I", pm.read_bytes(check, 4))[0]
                # vtable 指针应该指向 module 的 .rdata 段
                if mod.lpBaseOfDll <= val < mod_end:
                    # 检查 vtable 前后几个 slot 是否也像指针
                    ok = True
                    for delta in [4, 8, -4]:
                        v2 = struct.unpack_from("<I", pm.read_bytes(check + delta, 4))[0]
                        if mod.lpBaseOfDll <= v2 < mod_end:
                            pass  # also a module pointer, good sign
                    if ok:
                        vtable_map.setdefault((val, off), []).append(ic)
            except:
                pass

# 找出被最多不同 ItemCode 共享的 (vtable, offset) 组合
best = sorted(vtable_map.items(), key=lambda x: -len(set(x[1])))
for (vt, off), ics in best[:10]:
    unique = set(ics)
    if len(unique) >= 2:
        print(f"  vtable=0x{vt:08X}  ItemCode_offset=+0x{off:03X}  items={len(ics)}  unique_ics={sorted(unique)}")

pm.close_process()
print("\nDone.")

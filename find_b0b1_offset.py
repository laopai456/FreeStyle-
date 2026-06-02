"""
find_b0b1_offset.py — 定位描述符中 b0/b1 (in-game part ID) 字段的偏移

通过 pymem 读取游戏内存中已知 ItemCode 的描述符，
搜索已知 b0/b1 值的字节模式，确定偏移位置。

用法:
  1. 启动游戏并登录到大厅
  2. py find_b0b1_offset.py
"""
from __future__ import annotations
import json
import os
import struct
import sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem
import pymem.exception
import pymem.process
import pymem.pattern

PROCESS_NAME = "FreeStyle.exe"
VT_DESCRIPTOR = 0x027FCEA0
SNAPSHOT_DIR = r'd:\py\反编译\FreeStyle\snapshots'

# 已知映射 (从实测验证)
# 50125691 黑金热血青春发型 → b0=0x62, b1=0x28  → uint16 LE = 0x2862
# 50125701 紫色护目镜马尾辫     → b0=0x7E, b1=0xBA  → uint16 LE = 0xBA7E
# 50125721 粉色超级赛亚人3      → b0=0x7A, b1=0xC2  → uint16 LE = 0xC27A
KNOWN_MAP = {
    50125691: (0x62, 0x28),   # uint16 LE: 0x2862
    50125701: (0x7E, 0xBA),   # uint16 LE: 0xBA7E
    50125721: (0x7A, 0xC2),   # uint16 LE: 0xC27A
}

DESC_READ_SIZE = 256  # 每个描述符读取的字节数


def main():
    print("=" * 60)
    print("  b0/b1 Offset Scanner")
    print("=" * 60)

    try:
        pm = pymem.Pymem(PROCESS_NAME)
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe not running. Start game first.")
        return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] Run as Administrator")
        return

    print(f"[OK] PID={pm.process_id}")

    # Step 1: Scan for descriptor vtable
    print("  Scanning for vtable 0x027FCEE0...", end=" ", flush=True)
    vt_bytes = struct.pack("<I", VT_DESCRIPTOR)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, vt_bytes, return_multiple=True)
    print(f"{len(hits)} hits")

    module = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
    module_end = module.lpBaseOfDll + module.SizeOfImage
    heap_hits = [a for a in (hits or []) if a > module_end]
    print(f"  Heap objects: {len(heap_hits)}")

    # Step 2: Find descriptors of our known items
    found = {}  # itemcode → addr
    for addr in heap_hits:
        raw = pm.read_bytes(addr + 0x060, 4)
        itemcode = struct.unpack_from("<I", raw)[0]
        if itemcode in KNOWN_MAP:
            found[itemcode] = addr

    print(f"\n  Found {len(found)}/3 known descriptors:")
    for ic in sorted(KNOWN_MAP.keys()):
        if ic in found:
            print(f"    {ic} → 0x{found[ic]:08X}")
        else:
            print(f"    {ic} → NOT FOUND (need re-login?)")

    if len(found) < 2:
        print("\n[ERROR] Need at least 2 known descriptors to cross-reference.")
        pm.close_process()
        return

    # Step 3: Read raw bytes and search for b0/b1 patterns
    print(f"\n  Searching for b0/b1 byte patterns (scanning offsets 0x000-0x{DESC_READ_SIZE:X})...")
    print()

    # Read raw dumps
    dumps = {}
    for ic, addr in found.items():
        dumps[ic] = pm.read_bytes(addr, DESC_READ_SIZE)

    # Search for both uint16 and two separate uint8 values at all offsets
    candidates = []

    for offset in range(0, DESC_READ_SIZE - 1):
        matches = 0
        for ic, addr in found.items():
            b0, b1 = KNOWN_MAP[ic]
            raw = dumps[ic]

            # Check as uint16 LE
            if offset + 2 <= len(raw):
                val16 = struct.unpack_from("<H", raw, offset)[0]
                expected16 = (b1 << 8) | b0  # b0 is byte[0], b1 is byte[1]
                if val16 == expected16:
                    matches += 1
                    continue

            # Check as two consecutive uint8
            if offset + 2 <= len(raw):
                byte0 = raw[offset]
                byte1 = raw[offset + 1]
                if byte0 == b0 and byte1 == b1:
                    matches += 1

        if matches >= len(found):
            # Found! Read the values at this offset for all found descriptors
            vals = {}
            for ic in found:
                raw = dumps[ic]
                vals[ic] = (raw[offset], raw[offset + 1])

            candidates.append({
                'offset': offset,
                'offset_hex': f'0x{offset:03X}',
                'values': vals,
            })

    if candidates:
        print(f"  Found {len(candidates)} candidate offset(s):")
        for c in candidates:
            print(f"\n    Offset +{c['offset_hex']}:")
            for ic in sorted(c['values'].keys()):
                b0, b1 = c['values'][ic]
                expected = KNOWN_MAP[ic]
                match = "MATCH" if (b0, b1) == expected else "MISMATCH"
                print(f"      {ic}: b0=0x{b0:02X} b1=0x{b1:02X}  ({match})")

        # Recommend the first match
        print(f"\n  >>> Use offset +{candidates[0]['offset_hex']} for b0/b1 (uint8 pair)")
    else:
        print("  No exact match found. Printing diagnostic...")
        # Diagnostic: print known values and search
        for ic in found:
            raw = dumps[ic]
            b0, b1 = KNOWN_MAP[ic]
            print(f"\n  ItemCode={ic} (b0=0x{b0:02X}, b1=0x{b1:02X}):")
            # Search for individual byte matches
            for off in range(0, min(256, len(raw))):
                if raw[off] == b0:
                    nb = raw[off + 1] if off + 1 < len(raw) else -1
                    print(f"    b1 candidate at +{off}: byte=0x{raw[off]:02X} next=0x{nb:02X}")
                if raw[off] == b1:
                    pb = raw[off - 1] if off > 0 else -1
                    print(f"    b1 candidate at +{off}: byte=0x{raw[off]:02X} prev=0x{pb:02X}")

    pm.close_process()
    print("\n  Done.")


if __name__ == "__main__":
    main()
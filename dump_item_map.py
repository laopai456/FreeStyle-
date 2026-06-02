"""
dump_item_map.py — 批量导出全量 ItemCode → b0/b1 映射表

依赖 find_b0b1_offset.py 找到的偏移位置。
从游戏内存读取所有物品描述符，提取 ItemCode 和 b0/b1，
交叉引用 itemshop.txt 的名称，输出完整 CSV。

用法:
  1. 先运行 py find_b0b1_offset.py 找到 b0/b1 偏移 (e.g. +0x???)
  2. py dump_item_map.py <offset>   或者 py dump_item_map.py 0x???

输出:
  apollo_dump/item_b0b1_map.csv
"""
from __future__ import annotations
import csv
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
VT_DESCRIPTOR = 0x027FCEE0
ITEMS_DIR = r'd:\py\反编译\FreeStyle\bin\Debug\net8.0-windows\cookies\item_text_pak'
OUT_DIR = r'd:\py\反编译\FreeStyle\apollo_dump'


def load_itemshop_names():
    """从 itemshop.txt 和 itemshopex.txt 加载 ItemCode → Name 映射"""
    names = {}
    for fname in ['itemshop.txt', 'itemshopex.txt']:
        path = os.path.join(ITEMS_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='GB18030') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4 and parts[0].isdigit():
                        code = int(parts[0])
                        name = parts[3]
                        if name and name != '--':
                            names[code] = name
        except Exception as e:
            print(f"  [WARN] Failed to load {fname}: {e}")
    return names


def main():
    if len(sys.argv) < 2:
        print("Usage: py dump_item_map.py <b0b1_offset>")
        print("  e.g.: py dump_item_map.py 0x0A0")
        print()
        print("  Run 'py find_b0b1_offset.py' first to find the offset.")
        return

    offset_str = sys.argv[1]
    if offset_str.lower().startswith('0x'):
        B0B1_OFFSET = int(offset_str, 16)
    else:
        B0B1_OFFSET = int(offset_str)

    print("=" * 60)
    print(f"  Item Map Dumper (b0/b1 @ +0x{B0B1_OFFSET:X})")
    print("=" * 60)

    # Load item names
    print("  Loading itemshop names...", end=" ", flush=True)
    names = load_itemshop_names()
    print(f"{len(names)} names loaded")

    # Attach to game
    try:
        pm = pymem.Pymem(PROCESS_NAME)
    except pymem.exception.ProcessNotFound:
        print("[ERROR] FreeStyle.exe not running. Start game first.")
        return
    except pymem.exception.CouldNotOpenProcess:
        print("[ERROR] Run as Administrator")
        return

    print(f"[OK] PID={pm.process_id}")

    # Scan for descriptors
    print("  Scanning for vtable 0x027FCEE0...", end=" ", flush=True)
    vt_bytes = struct.pack("<I", VT_DESCRIPTOR)
    hits = pymem.pattern.pattern_scan_all(pm.process_handle, vt_bytes, return_multiple=True)
    print(f"{len(hits)} hits")

    module = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
    module_end = module.lpBaseOfDll + module.SizeOfImage
    heap_hits = [a for a in (hits or []) if a > module_end]
    print(f"  Heap objects: {len(heap_hits)}")

    # Read all descriptors
    items = []
    seen = set()

    for addr in heap_hits:
        try:
            raw = pm.read_bytes(addr + 0x060, 4)
            itemcode = struct.unpack_from("<I", raw)[0]
        except Exception:
            continue

        if itemcode == 0 or itemcode > 99999999:
            continue
        if itemcode in seen:
            continue
        seen.add(itemcode)

        try:
            b0b1_raw = pm.read_bytes(addr + B0B1_OFFSET, 2)
            b0 = b0b1_raw[0]
            b1 = b0b1_raw[1]
        except Exception:
            continue

        name = names.get(itemcode, '')

        items.append({
            'itemcode': itemcode,
            'b0': b0,
            'b1': b1,
            'b0_hex': f'0x{b0:02X}',
            'b1_hex': f'0x{b1:02X}',
            'name': name,
        })

    pm.close_process()

    # Sort by b0, b1
    items.sort(key=lambda x: (x['b0'], x['b1']))

    print(f"\n  Total items with valid b0/b1: {len(items)}")

    # Print summary by b0
    b0_counts = {}
    for item in items:
        b0_counts[item['b0']] = b0_counts.get(item['b0'], 0) + 1
    print(f"\n  b0 distribution ({len(b0_counts)} unique values):")
    for b0 in sorted(b0_counts.keys()):
        print(f"    0x{b0:02X}: {b0_counts[b0]} items")

    # Print hair items (b0 in 0x60-0x7F range, typical for hair)
    hair_items = [i for i in items if 0x60 <= i['b0'] <= 0x7F]
    print(f"\n  Hair-range items (b0 0x60-0x7F): {len(hair_items)} total")
    named_hair = [i for i in hair_items if i['name']]
    print(f"  Named hair items: {len(named_hair)}")
    print(f"\n  {'ItemCode':>10s}  b0    b1    Name")
    print(f"  {'-'*55}")
    for item in named_hair:
        print(f"  {item['itemcode']:>10d}  0x{item['b0']:02X}  0x{item['b1']:02X}  {item['name']}")

    # Save CSV
    os.makedirs(OUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUT_DIR, 'item_b0b1_map.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['itemcode', 'b0_hex', 'b1_hex', 'b0', 'b1', 'name'])
        writer.writeheader()
        for item in items:
            writer.writerow(item)

    print(f"\n  Saved: {csv_path}")
    print(f"  Done.")


if __name__ == "__main__":
    main()
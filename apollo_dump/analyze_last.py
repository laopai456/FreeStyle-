#!/usr/bin/env python3
"""
analyze_last.py — 读取 frida dump CSV, 详细分析最后 N 个包

用法:
    py analyze_last.py <csv_file> [-n 5] [-a]
    -n: 分析最后 N 个包 (默认 5)
    -a: 显示全部包摘要
"""

import csv, sys, os
from collections import Counter

# 已知的 (d0, plen) 标签
KNOWN_LABELS = {
    (0x01, 4): '心跳/Alive',
    (0x01, 8): '心跳(8B)',
    (0x05, 8): '移动/坐标',
    (0x05, 12): '移动(12B)',
    (0x09, 8): '动作/Action',
    (0x0b, 8): '聊天?',
    (0x0d, 8): '未知0D',
    (0x0f, 8): '未知0F',
    (0x11, 8): '未知11',
    (0x13, 8): '未知13',
    (0x15, 8): '未知15',
    (0x17, 8): '未知17',
    (0x19, 8): '未知19',
    (0x1d, 8): '未知1D',
    (0x1f, 8): '未知1F',
    (0x21, 8): '未知21',
    (0x23, 8): '未知23',
    (0x25, 8): '未知25',
    (0x27, 8): '未知27',
    (0x29, 8): '未知29',
    (0x2b, 8): '未知2B',
    (0x35, 8): '未知35',
    (0x37, 8): '未知37',
    (0x85, 0): '小包(空)',
}

def label(d0, plen):
    key = (d0, plen)
    if key in KNOWN_LABELS:
        return KNOWN_LABELS[key]
    if (d0, 8) in KNOWN_LABELS and plen > 8:
        return KNOWN_LABELS[(d0, 8)] + f'?({plen}B)'
    return f'??(d0=0x{d0:02X},plen={plen})'

def hexdump(data, width=32):
    """以 hex string 形式显示数据"""
    return ' '.join(data[i:i+2] for i in range(0, len(data), 2))

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', help='CSV file from frida dump')
    ap.add_argument('-n', type=int, default=5, help='Analyze last N packets')
    ap.add_argument('-a', action='store_true', help='Show all packets summary')
    args = ap.parse_args()

    pkts = []
    with open(args.csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # 检测新旧格式
        has_raw_field = 'raw_hex' in fieldnames  # 旧格式 (S4)
        for row in reader:
            if has_raw_field:
                # 旧格式: idx,len,f12,seq,plen,enc_prefix,dec_prefix,raw_hex — 全 OUT
                raw = row['raw_hex']
                enc_len = len(row['enc_prefix']) // 2
                dec_len = len(row['dec_prefix']) // 2
                pkts.append({
                    'idx': int(row['idx']),
                    'dir': 'OUT',
                    'f12': int(row['f12']),
                    'seq': int(row['seq']),
                    'plen': int(row['plen']),
                    'b0': int(raw[40:42], 16) if len(raw) >= 42 else 0,
                    'd0': int(row['dec_prefix'][:2], 16) if dec_len > 0 else 0,
                    'enc': row['enc_prefix'],
                    'dec': row['dec_prefix'],
                })
            else:
                # 新格式: idx,dir,f12,seq,plen,b0,d0,enc,dec
                pkts.append({
                    'idx': int(row['idx']),
                    'dir': row.get('dir', 'OUT'),
                    'f12': int(row['f12']),
                    'seq': int(row['seq']),
                    'plen': int(row['plen']),
                    'b0': int(row.get('b0', 0)),
                    'd0': int(row.get('d0', 0)),
                    'enc': row.get('enc', ''),
                    'dec': row.get('dec', ''),
                })

    if not pkts:
        print("No packets found.")
        return

    # === 全局摘要 ===
    print(f"=" * 70)
    print(f"  FILE: {os.path.basename(args.csv)}")
    print(f"  Total packets: {len(pkts)}")
    print(f"  Seq range: {pkts[0]['seq']} → {pkts[-1]['seq']}")
    print(f"  d0 range: 0x{pkts[0]['d0']:02X} → 0x{pkts[-1]['d0']:02X}")
    print()

    # 统计 d0 频次
    d0_counts = Counter(p['d0'] for p in pkts)
    print("  d0 distribution (top 20):")
    for d0, cnt in d0_counts.most_common(20):
        plens = Counter(p['plen'] for p in pkts if p['d0'] == d0)
        plen_str = ', '.join(f'{l}B×{c}' for l, c in plens.most_common(5))
        lbl = KNOWN_LABELS.get((d0, plens.most_common(1)[0][0]), '')
        if not lbl:
            lbl = KNOWN_LABELS.get((d0, 8), '')
        print(f"    0x{d0:02X}: {cnt:4d} pkts  | plens: {plen_str}  {lbl}")

    # plen 分布
    plen_counts = Counter(p['plen'] for p in pkts)
    print(f"\n  plen distribution:")
    for pl, cnt in plen_counts.most_common():
        print(f"    {pl:4d}B: {cnt:4d} pkts")

    # === 最后 N 个包详细分析 ===
    n = min(args.n, len(pkts))
    last = pkts[-n:]
    print(f"\n{'='*70}")
    print(f"  DETAILED ANALYSIS: last {n} packets")
    print(f"{'='*70}")

    for i, p in enumerate(last):
        idx_in_all = len(pkts) - n + i + 1
        print(f"\n--- Packet #{idx_in_all} (idx={p['idx']}) ---")
        print(f"  Dir   : {'OUT ▶' if p['dir']=='OUT' else 'IN ◀'}   Seq: {p['seq']}")
        print(f"  d0/b0 : 0x{p['d0']:02X} / 0x{p['b0']:02X}   f12: {p['f12']} (0x{p['f12']:08X})")
        print(f"  plen  : {p['plen']} bytes   Label: {label(p['d0'], p['plen'])}")
        print(f"  Enc   : {hexdump(p['enc'])}")
        print(f"  Dec   : {hexdump(p['dec'])}")

        # 如果是 plen>8 的包，显示更多解密数据
        if p['plen'] > 8 and len(p['dec']) > 64:
            print(f"  Dec[8:40]: {hexdump(p['dec'][16:96])}")

    # === 比较最后几个包的 d0 模式 ===
    print(f"\n{'='*70}")
    print(f"  PATTERN: last {n} packets comparison")
    print(f"{'='*70}")
    # 显示简洁的一行对比
    print(f"  {'#':>4} {'Seq':>5} {'d0':>5} {'plen':>5} {'f12':>12}  Label")
    for i, p in enumerate(last):
        idx = len(pkts) - n + i + 1
        print(f"  {idx:>4} {p['seq']:>5} 0x{p['d0']:02X}  {p['plen']:>5} {p['f12']:>12}  {label(p['d0'], p['plen'])}")

    # === 异常检测 ===
    print(f"\n{'='*70}")
    print(f"  ANOMALIES / NEW PATTERNS")
    print(f"{'='*70}")
    for p in last:
        key = (p['d0'], p['plen'])
        if key not in KNOWN_LABELS:
            print(f"  NEW: (d0=0x{p['d0']:02X}, plen={p['plen']}) — seq={p['seq']}")
            print(f"    Full raw: {hexdump(p['enc'])}")
            if p['plen'] > 8:
                print(f"    Dec[8:]: {hexdump(p['dec'][16:96])}")

    # 展示完整毒包 hex dump
    print(f"\n{'='*70}")
    print(f"  FULL HEX DUMP (all {n} packets)")
    print(f"{'='*70}")
    for i, p in enumerate(last):
        idx = len(pkts) - n + i + 1
        print(f"\n  [#{idx}] seq={p['seq']} d0=0x{p['d0']:02X} plen={p['plen']} f12={p['f12']}")
        enc = p['enc']
        for off in range(0, len(enc), 32):
            chunk = enc[off:off+32]
            if chunk:
                print(f"    ENC [{off:3d}]: {hexdump(chunk)}")
        dec = p['dec']
        for off in range(0, len(dec), 32):
            chunk = dec[off:off+32]
            if chunk:
                print(f"    DEC [{off:3d}]: {hexdump(chunk)}")

if __name__ == '__main__':
    main()
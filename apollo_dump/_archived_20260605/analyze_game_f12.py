"""
分析游戏包 (magic 43d58b80) 的 f12 计算模式。
目标: 找出 f12(bytes 12-15) 与 seq/payload 的关系。
"""
import csv, os, struct
from collections import defaultdict

DUMP = os.path.join(os.path.dirname(__file__), "apollo_dump")

KEY = bytes([0x4d, 0xb8, 0xa8, 0x54])

def xor_dec(data, offset=0):
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = data[i] ^ KEY[(i + offset) % 4]
    return bytes(out)

# 加载一个大 session (S8: 136包, 大厅+商城)
packets = []
for fname in ['f12_20260520_111101.csv', 'f12_20260519_181141.csv', 'f12_20260519_221539.csv']:
    path = os.path.join(DUMP, fname)
    if not os.path.exists(path):
        continue
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        if 'raw_hex' not in cols and 'enc' not in cols:
            continue
        for row in reader:
            if row.get('dir', 'OUT') != 'OUT':
                continue
            # 从 raw_hex 或 enc/dec 提取数据
            if 'raw_hex' in row and row['raw_hex']:
                raw = bytes.fromhex(row['raw_hex'])
                if len(raw) < 20 or raw[:4] != b'\x43\xd5\x8b\x80':
                    continue
                f12_wire = struct.unpack_from('<I', raw, 12)[0]
                seq_wire = struct.unpack_from('<I', raw, 16)[0]
                enc = raw[20:]
                dec = xor_dec(enc)
                b0 = enc[0] if enc else 0
                d0 = dec[0] if dec else 0
                plen = len(dec)
            elif 'enc' in row and row['enc']:
                enc = bytes.fromhex(row['enc'])
                dec = bytes.fromhex(row['dec'])
                f12_wire = int(row['f12']) & 0xFFFFFFFF
                seq_wire = int(row['seq'])
                b0 = int(row.get('b0', str(enc[0]))) if enc else 0
                d0 = int(row.get('d0', str(dec[0]))) if dec else 0
                plen = int(row['plen'])
            else:
                continue
            packets.append({
                'f12': f12_wire, 'f12_u': f12_wire,
                'seq': seq_wire, 'plen': plen, 'b0': b0, 'd0': d0,
                'enc': enc, 'dec': dec, 'raw': raw if 'raw_hex' in row and row.get('raw_hex') else None,
                'source': fname
            })

print(f"Loaded {len(packets)} game packets")
print()

# 1. f12 与 seq 的关系 (同 d0)
print("=" * 60)
print("1. f12 vs seq (same d0=opcode, plen=8)")
print("=" * 60)
by_d0 = defaultdict(list)
for p in packets:
    if p['plen'] == 8:
        by_d0[p['d0']].append(p)

for d0 in sorted(by_d0.keys()):
    pkts = by_d0[d0]
    if len(pkts) < 2:
        continue
    print(f"\n  d0=0x{d0:02X} ({len(pkts)} packets):")
    for p in pkts[:8]:
        print(f"    seq={p['seq']:3d}  f12=0x{p['f12_u']:08X}  b0=0x{p['b0']:02X}")

    # 检查同 d0 的 f12 是否固定
    f12s = set(p['f12_u'] for p in pkts)
    if len(f12s) == 1:
        print(f"    → f12 FIXED = 0x{pkts[0]['f12_u']:08X}")
    else:
        print(f"    → f12 VARIES ({len(f12s)} unique values)")

        # 检查 f12 与 b0 的关系
        by_b0 = defaultdict(set)
        for p in pkts:
            by_b0[p['b0']].add(p['f12_u'])
        one_to_one = all(len(v) == 1 for v in by_b0.values())
        if one_to_one:
            print(f"    → f12 = F(b0), 1-to-1 mapping:")
            for b0_val in sorted(by_b0.keys()):
                f12_val = list(by_b0[b0_val])[0]
                print(f"      b0=0x{b0_val:02X} → f12=0x{f12_val:08X}")

# 2. f12 与 b0 的关系 (所有 plen=8)
print("\n" + "=" * 60)
print("2. f12 vs b0 (all plen=8, cross-d0)")
print("=" * 60)
f12_by_b0 = defaultdict(set)
for p in packets:
    if p['plen'] == 8:
        f12_by_b0[p['b0']].add(p['f12_u'])

consistent = 0
inconsistent = 0
for b0 in sorted(f12_by_b0.keys()):
    vals = f12_by_b0[b0]
    if len(vals) == 1:
        consistent += 1
    else:
        inconsistent += 1
        if inconsistent <= 5:
            print(f"  b0=0x{b0:02X}: {len(vals)} different f12 values: {[f'0x{v:08X}' for v in sorted(vals)]}")

print(f"\n  Consistent (1 f12 per b0): {consistent}")
print(f"  Inconsistent (>1 f12 per b0): {inconsistent}")

# 3. 如果 f12 = F(b0), 输出完整映射表
print("\n" + "=" * 60)
print("3. f12(b0) lookup table (plen=8)")
print("=" * 60)
print(f"  {'b0':>4s}  {'f12':>10s}  {'d0':>4s}  {'dec[0:8]':>20s}")
for b0 in sorted(f12_by_b0.keys()):
    vals = f12_by_b0[b0]
    # 找一个代表包
    rep = next(p for p in packets if p['plen'] == 8 and p['b0'] == b0)
    f12_str = f"0x{list(vals)[0]:08X}" if len(vals) == 1 else f"VAR({len(vals)})"
    print(f"  0x{b0:02X}  {f12_str:>10s}  0x{rep['d0']:02X}  {rep['dec'][:8].hex()}")

# 4. 对于 plen>8 的包, f12 是否也有规律
print("\n" + "=" * 60)
print("4. f12 for plen>8 packets (first 20)")
print("=" * 60)
for p in packets:
    if p['plen'] > 8:
        print(f"  seq={p['seq']:3d} plen={p['plen']:3d} d0=0x{p['d0']:02X} b0=0x{p['b0']:02X} f12=0x{p['f12_u']:08X}  dec_head={p['dec'][:12].hex()}")

# 5. 检查 wire 包 bytes 4-11 (session token)
print("\n" + "=" * 60)
print("5. Wire packet bytes 4-11 pattern")
print("=" * 60)
# 需要完整 wire 数据，从 enc 字段无法直接获取
# 但我们可以从 raw 数据分析...
# 先检查 dec 的前几个字节
print("  Checking decrypted payload structure:")
for p in packets[:5]:
    print(f"    plen={p['plen']} d0=0x{p['d0']:02X} dec={p['dec'][:16].hex()}")

# 6. seq 递增模式
print("\n" + "=" * 60)
print("6. Seq increment pattern (first 30 packets)")
print("=" * 60)
prev = None
for p in packets[:30]:
    diff = p['seq'] - prev if prev is not None else '-'
    print(f"  seq={p['seq']:4d}  Δ={str(diff):>4s}  plen={p['plen']:3d}  d0=0x{p['d0']:02X}  f12=0x{p['f12_u']:08X}")
    prev = p['seq']

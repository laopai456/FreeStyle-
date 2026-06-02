"""Check cross-session consistency of T[b0] using multiple reference b0 values"""
import csv, os, re
from collections import defaultdict

U_PARITY = 0xDD45AAB8
K_X = 0xBF672381
def u32(v): return v & 0xFFFFFFFF

def parse_correct_buf(path):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f: text = f.read()
    for m in re.finditer(r'\[GAME_PKT#\d+\]\s+seq=(\d+)\s+len=\d+\s+field12=0x([-0-9A-Fa-f]+)\s*\n\s+enc_full:\s+([0-9A-Fa-f\s]+)', text):
        seq, f12 = int(m.group(1)), int(m.group(2), 16)
        enc = m.group(3).replace(' ', '')
        b0, plen = int(enc[:2], 16), len(enc)//2
        if plen == 8:
            pkts.append({'session': 'S1', 'seq': seq, 'b0': b0, 'sk_xor_t': u32(f12) ^ (U_PARITY if seq & 1 else 0)})
    return pkts

def parse_old_csv(path, sname):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if int(row['plen']) != 8: continue
            seq, f12 = int(row['seq']), int(row['f12'])
            raw = row.get('raw_hex', '')
            b0 = int(raw[40:42], 16) if len(raw) >= 42 else 0
            pkts.append({'session': sname, 'seq': seq, 'b0': b0, 'sk_xor_t': u32(f12) ^ (U_PARITY if seq & 1 else 0)})
    return pkts

def parse_new_csv(path, sname):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if int(row['plen']) != 8: continue
            seq, f12, b0 = int(row['seq']), int(row['f12']), int(row['b0'])
            pkts.append({'session': sname, 'seq': seq, 'b0': b0, 'sk_xor_t': u32(f12) ^ (U_PARITY if seq & 1 else 0)})
    return pkts

dump_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')
all_pkts = []
all_pkts.extend(parse_correct_buf(os.path.join(dump_dir, 'correct_buf.txt')))
all_pkts.extend(parse_old_csv(os.path.join(dump_dir, 'f12_samples.csv'), 'S3'))
all_pkts.extend(parse_old_csv(os.path.join(dump_dir, 'f12_20260519_181141.csv'), 'S4'))
all_pkts.extend(parse_new_csv(os.path.join(dump_dir, 'f12_20260519_221539.csv'), 'S5'))

# Per session: b0 -> unique sk_xor_t
sess_t = defaultdict(lambda: defaultdict(set))
for p in all_pkts:
    sess_t[p['session']][p['b0']].add(p['sk_xor_t'])

# Check each session's b0 consistency (same b0 should have same sk_xor_t)
print("=== Intra-session consistency ===")
for sname in ['S1', 'S3', 'S4', 'S5']:
    multi = [(b0, vals) for b0, vals in sess_t[sname].items() if len(vals) > 1]
    if multi:
        print(f"  {sname}: {len(multi)} b0 values have multiple sk_xor_t:")
        for b0, vals in multi[:5]:
            print(f"    0x{b0:02X}: {[f'0x{v:08X}' for v in vals]}")
    else:
        print(f"  {sname}: all b0 values consistent ✓")

# Cross-session offset consistency
print("\n=== Cross-session offset consistency ===")
for pair in [('S4', 'S5'), ('S3', 'S5'), ('S1', 'S5')]:
    s_a, s_b = pair
    common = set(sess_t[s_a].keys()) & set(sess_t[s_b].keys())
    offsets = {}
    for b0 in sorted(common):
        va = next(iter(sess_t[s_a][b0]))
        vb = next(iter(sess_t[s_b][b0]))
        offsets[b0] = va ^ vb

    mode_off = max(set(offsets.values()), key=list(offsets.values()).count)
    mismatches = {b0: off for b0, off in offsets.items() if off != mode_off}

    print(f"\n  {s_a} ↔ {s_b}: {len(common)} common b0, mode offset=0x{mode_off:08X}")
    if mismatches:
        print(f"  MISMATCH: {len(mismatches)} b0 values differ from mode offset:")
        for b0, off in sorted(mismatches.items()):
            delta = off ^ mode_off
            print(f"    0x{b0:02X}: off=0x{off:08X} delta=0x{delta:08X}")
    else:
        print(f"  All consistent ✓")

# Also check: do S3/S4/S5 share T[b0] (after session offset)?
print("\n=== Cross-session T consistency (offset applied) ===")
ref = 'S5'
ref_vals = {b0: next(iter(vals)) for b0, vals in sess_t[ref].items()}
for sname in ['S4', 'S3', 'S1']:
    common = set(ref_vals.keys()) & set(sess_t[sname].keys())
    s_vals = {b0: next(iter(vals)) for b0, vals in sess_t[sname].items()}

    # Find best offset
    best_off = max(set(s_vals[b0] ^ ref_vals[b0] for b0 in common), key=list(common).count)

    # Count matches
    matches = sum(1 for b0 in common if s_vals[b0] ^ best_off == ref_vals[b0])
    mismatch_b0s = [b0 for b0 in common if s_vals[b0] ^ best_off != ref_vals[b0]]

    print(f"  {sname} → {ref}: offset=0x{best_off:08X}, {matches}/{len(common)} match")
    if mismatch_b0s:
        print(f"    Mismatches ({len(mismatch_b0s)}): {[f'0x{b:02X}' for b in sorted(mismatch_b0s)[:15]]}")
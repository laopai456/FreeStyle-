"""Quick diagnostic: 检查 pattern mismatches 的跨 session 来源"""
import csv, os, re, sys
from collections import defaultdict

U_PARITY = 0xDD45AAB8
K_X = 0xBF672381

def to_unsigned(v):
    return v & 0xFFFFFFFF

# ---- parse all sources (same as fill_t_table) ----
def parse_correct_buf(path):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    pattern = r'\[GAME_PKT#\d+\]\s+seq=(\d+)\s+len=\d+\s+field12=0x([-0-9A-Fa-f]+)\s*\n\s+enc_full:\s+([0-9A-Fa-f ]+)\s*\n\s+pl_full:\s+([0-9A-Fa-f ]+)'
    for m in re.finditer(pattern, text):
        seq = int(m.group(1))
        f12 = int(m.group(2), 16)
        enc_hex = m.group(3).replace(' ', '')
        b0 = int(enc_hex[:2], 16)
        plen = len(enc_hex) // 2
        pkts.append({'session': 'S1', 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

def parse_old_csv(path, sname):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plen = int(row['plen'])
            seq = int(row['seq'])
            f12 = int(row['f12'])
            raw = row.get('raw_hex', '')
            if len(raw) >= 42:
                b0 = int(raw[40:42], 16)
            else:
                enc = row.get('enc_prefix', '')
                b0 = int(enc[:2], 16) if enc else 0
            pkts.append({'session': sname, 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

def parse_new_csv(path, sname):
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plen = int(row['plen'])
            seq = int(row['seq'])
            f12 = int(row['f12'])
            b0 = int(row['b0'])
            pkts.append({'session': sname, 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

dump_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')
all_pkts = []

all_pkts.extend(parse_correct_buf(os.path.join(dump_dir, 'correct_buf.txt')))
all_pkts.extend(parse_old_csv(os.path.join(dump_dir, 'f12_samples.csv'), 'S3a'))
all_pkts.extend(parse_old_csv(os.path.join(dump_dir, 'f12_s3_102rec.csv'), 'S3b'))
all_pkts.extend(parse_old_csv(os.path.join(dump_dir, 'f12_20260519_181141.csv'), 'S4'))
all_pkts.extend(parse_new_csv(os.path.join(dump_dir, 'f12_20260519_221539.csv'), 'S5'))

plen8 = [p for p in all_pkts if p['plen'] == 8]

# Group by session, compute sk_xor_t = f12 ^ parity
sessions = defaultdict(list)
for p in plen8:
    p['sk_xor_t'] = to_unsigned(p['f12']) ^ (U_PARITY if p['seq'] & 1 else 0)
    sessions[p['session']].append(p)

# For each b0, show which sessions contributed and their sk_xor_t values
b0_session_vals = defaultdict(lambda: defaultdict(list))
for sname, pkts in sessions.items():
    for p in pkts:
        b0_session_vals[p['b0']][sname].append(p['sk_xor_t'])

# Check specific mismatches
mismatch_b0s = [
    (44, 47, 'ModeA T[4k]==T[4k+3]'),
    (56, 59, 'ModeA T[4k]==T[4k+3]'),
    (60, 63, 'ModeA T[4k]==T[4k+3]'),
    (194, 195, 'ModeB T[4k]==T[4k+1]'),
    (198, 199, 'ModeB T[4k]==T[4k+1]'),
    (220, 221, 'ModeB T[4k]==T[4k+1]'),
    (222, 223, 'ModeB T[4k]==T[4k+1]'),
    (230, 231, 'ModeB T[4k]==T[4k+1]'),
]

print("="*70)
print("MISMATCH DIAGNOSTIC")
print("="*70)
for b0_a, b0_b, desc in mismatch_b0s:
    print(f"\n{desc}: 0x{b0_a:02X}(k={b0_a>>2},p={b0_a&3}) vs 0x{b0_b:02X}(k={b0_b>>2},p={b0_b&3})")
    for b0 in [b0_a, b0_b]:
        vals = b0_session_vals.get(b0, {})
        print(f"  T[0x{b0:02X}] from sessions:")
        for sname in sorted(vals.keys()):
            unique_vals = set(vals[sname])
            print(f"    {sname}: values={[f'0x{v:08X}' for v in unique_vals]}")

# Also check specific mismatches for T[4k+2] vs T[4k]^K_X
mismatch_b0s2 = [
    (56, 58, 'ModeA T[4k+2]==T[4k]^K_X'),  # k=14: T[56] vs T[58? no, T[56+2]=T[58]]
    (104, 106, 'ModeA T[4k+2]==T[4k]^K_X'), # k=26: T[104] vs T[106]
]

# Wait, the original mismatches list T[58]=286B1FDB != T[56]^K_X=30EAB79F
# T[56]=0x8F8D941E, T[56]^K_X = 0x8F8D941E ^ 0xBF672381 = 0x30EAB79F
# But T[58]=0x286B1FDB, so they're different.

# And: T[106]=5C0BDB16 != T[104]^K_X=B56F6A2B
# T[104] = ?, need to check
print("\n\n--- Checking T[4k+2] vs T[4k]^K_X ---")
for b0_k, b0_k2, desc in [(56,58,'k=14'), (104,106,'k=26')]:
    print(f"\nk={b0_k>>2}: T[0x{b0_k:02X}] vs T[0x{b0_k2:02X}]")
    for b0 in [b0_k, b0_k2]:
        vals = b0_session_vals.get(b0, {})
        print(f"  T[0x{b0:02X}]:")
        for sname in sorted(vals.keys()):
            unique_vals = set(vals[sname])
            print(f"    {sname}: {[f'0x{v:08X}' for v in unique_vals]}")
    # compute T[b0_k]^K_X
    if b0_k in b0_session_vals:
        for sname in sorted(b0_session_vals[b0_k].keys()):
            v = b0_session_vals[b0_k][sname][0]
            print(f"  Expected T[0x{b0_k2:02X}] from {sname}: 0x{v:08X} ^ K_X = 0x{(v^K_X):08X}")
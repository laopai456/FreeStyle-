"""
深入分析 38 包 enc (wire) 数据:
1. 哪些字节是 session-constant (跨 session 不同，session 内固定)
2. 哪些字节是 per-packet varying (每包都变)
3. 哪些字节是完全固定的
"""
import csv, re, os

DUMP = os.path.join(os.path.dirname(__file__), "apollo_dump")

def parse_correct_buf(path):
    pkts = {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    blocks = re.findall(r'\[GAME_PKT#(\d+)\] seq=(\d+) len=\d+ .*?\s+enc_full:\s*([0-9a-f ]+)\s+pl_full:\s*([0-9a-f ]+)', text)
    for _, seq_s, enc_s, _ in blocks:
        seq = int(seq_s)
        enc = bytes.fromhex(enc_s.replace(" ", ""))
        pkts[seq] = enc
    return pkts

def parse_csv(path):
    pkts = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seq = int(row["seq"])
            enc = bytes.fromhex(row["enc"])
            pkts[seq] = enc
    return pkts

s1 = parse_correct_buf(os.path.join(DUMP, "correct_buf.txt"))
s11 = parse_csv(os.path.join(DUMP, "f12_20260520_121326.csv"))
s12 = parse_csv(os.path.join(DUMP, "f12_20260520_104951.csv"))

print("=" * 80)
print("ENC (wire) DATA: Session-constant vs Per-packet analysis")
print("=" * 80)

# For each byte position, check:
# - Is it the same across all 3 sessions for ALL packets? → FIXED
# - Is it different across sessions but same within session? → SESSION_CONST
# - Does it vary within a session? → PER_PACKET
print("\n--- Per-byte classification (enc wire data) ---")
for pos in range(20):
    s1_vals = []
    s11_vals = []
    s12_vals = []
    all_same_across = True
    for seq in range(3, 39):  # skip seq 1-2 (they're identical)
        b1 = s1.get(seq, b"")
        b11 = s11.get(seq, b"")
        b12 = s12.get(seq, b"")
        if pos >= len(b1) or pos >= len(b11) or pos >= len(b12):
            continue
        s1_vals.append(b1[pos])
        s11_vals.append(b11[pos])
        s12_vals.append(b12[pos])
        if b1[pos] != b11[pos] or b1[pos] != b12[pos]:
            all_same_across = False

    if not s1_vals:
        continue

    # Check if constant within each session
    s1_const = len(set(s1_vals)) == 1
    s11_const = len(set(s11_vals)) == 1
    s12_const = len(set(s12_vals)) == 1

    if all_same_across:
        tag = "FIXED"
    elif s1_const and s11_const and s12_const:
        tag = f"SESSION_CONST (S1={s1_vals[0]:02x} S11={s11_vals[0]:02x} S12={s12_vals[0]:02x})"
    else:
        tag = f"PER_PACKET  (S1 range={min(s1_vals):02x}-{max(s1_vals):02x} unique={len(set(s1_vals))})"

    print(f"  byte[{pos:2d}]: {tag}")

# Detailed per-packet diff for small packets (8B)
print("\n--- Detailed 8-byte packet comparison (seq 1-4, 16-17) ---")
for seq in [1, 2, 3, 4, 16, 17]:
    e1 = s1.get(seq, b"")
    e11 = s11.get(seq, b"")
    e12 = s12.get(seq, b"")
    print(f"\n  seq {seq}:")
    print(f"    S1:  {e1.hex()}")
    print(f"    S11: {e11.hex()}")
    print(f"    S12: {e12.hex()}")
    # XOR between sessions
    xor_1_11 = bytes(a ^ b for a, b in zip(e1, e11))
    xor_1_12 = bytes(a ^ b for a, b in zip(e1, e12))
    xor_11_12 = bytes(a ^ b for a, b in zip(e11, e12))
    print(f"    S1^S11:  {xor_1_11.hex()}")
    print(f"    S1^S12:  {xor_1_12.hex()}")

# Check if the XOR between sessions is constant across packets
print("\n--- Inter-session XOR consistency ---")
for pair_name, pair in [("S11^S12", (s11, s12)), ("S1^S11", (s1, s11)), ("S1^S12", (s1, s12))]:
    print(f"\n  {pair_name}:")
    sa, sb = pair
    xors_by_pos = {}
    for seq in range(1, 39):
        ea = sa.get(seq, b"")
        eb = sb.get(seq, b"")
        if not ea or not eb:
            continue
        minlen = min(len(ea), len(eb))
        for i in range(minlen):
            x = ea[i] ^ eb[i]
            if i not in xors_by_pos:
                xors_by_pos[i] = []
            xors_by_pos[i].append(x)

    for pos in sorted(xors_by_pos.keys())[:20]:
        vals = xors_by_pos[pos]
        unique = set(vals)
        if len(unique) == 1:
            print(f"    byte[{pos:2d}]: CONSTANT xor={vals[0]:02x} ★")
        else:
            print(f"    byte[{pos:2d}]: VARIES ({len(unique)} values)")

# Analyze b0/d0 pattern (first byte and 4th byte in plaintext)
print("\n--- First 8 bytes of enc for all 38 packets ---")
print(f"  {'seq':>3} | {'S1':>20} | {'S11':>20} | {'S12':>20} | byte3 match?")
for seq in range(1, 39):
    e1 = s1.get(seq, b"")[:8].hex()
    e11 = s11.get(seq, b"")[:8].hex()
    e12 = s12.get(seq, b"")[:8].hex()
    # Check byte[2:4] match within session
    s1_b23 = s1.get(seq, b"")[2:4].hex()
    s11_b23 = s11.get(seq, b"")[2:4].hex()
    s12_b23 = s12.get(seq, b"")[2:4].hex()
    b3_match = "SAME" if s1_b23 == s11_b23 == s12_b23 else f"diff ({s1_b23}/{s11_b23}/{s12_b23})"
    print(f"  {seq:3} | {e1:>20} | {e11:>20} | {e12:>20} | {b3_match}")

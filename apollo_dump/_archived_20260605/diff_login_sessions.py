"""
对比三次登录 session 的 38 包，逐字节找出固定/变化字段。
S1 = correct_buf.txt
S11 = f12_20260520_121326.csv
S12 = f12_20260520_104951.csv
"""
import csv, re, os

DUMP = os.path.join(os.path.dirname(__file__), "apollo_dump")

def parse_correct_buf(path):
    """Parse S1 correct_buf.txt format"""
    pkts = {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    blocks = re.findall(r'\[GAME_PKT#(\d+)\] seq=(\d+) len=(\d+) field12=(0x[0-9a-fA-F-]+)\s+enc_full:\s*([0-9a-f ]+)\s+pl_full:\s*([0-9a-f ]+)', text)
    for idx_s, seq_s, len_s, f12_s, enc_s, pl_s in blocks:
        seq = int(seq_s)
        enc = bytes.fromhex(enc_s.replace(" ", ""))
        dec = bytes.fromhex(pl_s.replace(" ", ""))
        pkts[seq] = {"enc": enc, "dec": dec, "f12": f12_s}
    return pkts

def parse_csv(path):
    """Parse CSV format"""
    pkts = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seq = int(row["seq"])
            enc = bytes.fromhex(row["enc"])
            dec = bytes.fromhex(row["dec"])
            pkts[seq] = {"enc": enc, "dec": dec, "f12": row["f12"]}
    return pkts

s1 = parse_correct_buf(os.path.join(DUMP, "correct_buf.txt"))
s11 = parse_csv(os.path.join(DUMP, "f12_20260520_121326.csv"))
s12 = parse_csv(os.path.join(DUMP, "f12_20260520_104951.csv"))

print("=" * 80)
print("LOGIN SESSION DIFF ANALYSIS: S1 vs S11 vs S12")
print("=" * 80)

# F12 comparison
print("\n--- F12 per seq ---")
for seq in range(1, 39):
    f12s = []
    for name, s in [("S1", s1), ("S11", s11), ("S12", s12)]:
        f12s.append(s.get(seq, {}).get("f12", "MISSING"))
    # Normalize f12 to int for comparison
    def f12_to_int(v):
        if isinstance(v, str) and v.startswith("0x"):
            v = v[2:]
            neg = v.startswith("-")
            if neg: v = v[1:]
            return (-1 if neg else 1) * int(v, 16)
        return int(v)
    vals = [f12_to_int(f) for f in f12s if f != "MISSING"]
    same = len(set(vals)) <= 1
    marker = "  FIXED" if same else "★ VARIES"
    print(f"  seq {seq:2d}: {marker}  S1={f12s[0]}  S11={f12s[1]}  S12={f12s[2]}")

# Byte-by-byte diff in plaintext (dec) domain
print("\n--- Plaintext (dec) byte-by-byte diff ---")
for seq in range(1, 39):
    d1 = s1.get(seq, {}).get("dec", b"")
    d11 = s11.get(seq, {}).get("dec", b"")
    d12 = s12.get(seq, {}).get("dec", b"")
    if not d1 or not d11 or not d12:
        print(f"  seq {seq:2d}: MISSING")
        continue
    plen = max(len(d1), len(d11), len(d12))
    diffs = []
    fixed_bytes = []
    for i in range(plen):
        b1 = d1[i] if i < len(d1) else None
        b11 = d11[i] if i < len(d11) else None
        b12 = d12[i] if i < len(d12) else None
        if b1 == b11 == b12:
            fixed_bytes.append(f"{i:2d}={b1:02x}")
        else:
            def fb(b): return f"{b:02x}" if b is not None else "??"
            diffs.append(f"{i:2d}: S1={fb(b1)} S11={fb(b11)} S12={fb(b12)}")

    if diffs:
        print(f"  seq {seq:2d} ({plen}B): VARIES at [{', '.join(d[0:3] for d in diffs)}]")
        if len(diffs) <= 4:
            for d in diffs:
                print(f"          {d}")
    else:
        print(f"  seq {seq:2d} ({plen}B): ALL FIXED")

# Also diff in enc domain
print("\n--- Encrypted (enc) byte-by-byte diff ---")
for seq in range(1, 39):
    e1 = s1.get(seq, {}).get("enc", b"")
    e11 = s11.get(seq, {}).get("enc", b"")
    e12 = s12.get(seq, {}).get("enc", b"")
    if not e1 or not e11 or not e12:
        continue
    plen = max(len(e1), len(e11), len(e12))
    diff_positions = []
    for i in range(plen):
        b1 = e1[i] if i < len(e1) else None
        b11 = e11[i] if i < len(e11) else None
        b12 = e12[i] if i < len(e12) else None
        if not (b1 == b11 == b12):
            diff_positions.append(i)

    if diff_positions:
        print(f"  seq {seq:2d}: varies at bytes {diff_positions}")
    else:
        print(f"  seq {seq:2d}: ALL IDENTICAL")

# Summary: which byte positions ALWAYS change, which are ALWAYS fixed
print("\n--- SUMMARY: Byte position consistency across all 38 packets ---")
always_fixed = set(range(300))  # start with all, remove on any diff
always_varies = set()
sometimes_varies = set()

for seq in range(1, 39):
    d1 = s1.get(seq, {}).get("dec", b"")
    d11 = s11.get(seq, {}).get("dec", b"")
    d12 = s12.get(seq, {}).get("dec", b"")
    if not d1 or not d11 or not d12:
        continue
    plen = max(len(d1), len(d11), len(d12))
    for i in range(plen):
        b1 = d1[i] if i < len(d1) else None
        b11 = d11[i] if i < len(d11) else None
        b12 = d12[i] if i < len(d12) else None
        if b1 == b11 == b12:
            if i in always_varies:
                sometimes_varies.add(i)
                always_varies.discard(i)
        else:
            if i in always_fixed:
                always_fixed.discard(i)
                if i not in sometimes_varies:
                    always_varies.add(i)

print(f"  ALWAYS FIXED positions: {sorted(always_fixed)}")
print(f"  ALWAYS VARIES positions: {sorted(always_varies)}")
print(f"  SOMETIMES VARIES: {sorted(sometimes_varies)}")

# Print the actual values at varying positions
print("\n--- Varying byte values (plaintext) ---")
for pos in sorted(always_varies):
    vals = []
    for seq in range(1, 39):
        d1 = s1.get(seq, {}).get("dec", b"")
        d11 = s11.get(seq, {}).get("dec", b"")
        d12 = s12.get(seq, {}).get("dec", b"")
        if pos < len(d1):
            vals.append(f"seq{seq:2d}: S1={d1[pos]:02x} S11={d11[pos]:02x} S12={d12[pos]:02x}")
    print(f"  byte[{pos}]:")
    for v in vals[:10]:
        print(f"    {v}")
    if len(vals) > 10:
        print(f"    ... ({len(vals)-10} more)")

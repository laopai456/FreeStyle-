"""
UDP encryption key cracking — v2
Target: 93B S2C heartbeat packets (0x17.0xfe) — 16,507 copies.

Strategies:
  A) Frequency analysis per byte position — most common ciphertext byte
  B) Pairwise XOR — detect keystream period/reuse
  C) Simple XOR key brute-force (len=1..32)
  D) C2S header known-plaintext via sequence matching
"""
import struct, os
from collections import Counter

PCAP = r'apollo_dump\raw_20260520_154224.pcap'

def read_pcap(path):
    """Yield (timestamp, payload) for S2C UDP packets."""
    with open(path, 'rb') as f:
        f.read(24)  # global header
        while True:
            hdr = f.read(16)
            if len(hdr) < 16: break
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack('<IIII', hdr)
            pkt = f.read(incl_len)
            if len(pkt) < incl_len: break
            
            if len(pkt) < 14: continue
            eth_type = struct.unpack('!H', pkt[12:14])[0]
            if eth_type != 0x0800: continue
            
            ip_start = 14
            if len(pkt) < ip_start + 20: continue
            ip_hdr = pkt[ip_start:ip_start+20]
            protocol = ip_hdr[9]
            ihl = (ip_hdr[0] & 0x0F) * 4
            
            if protocol != 17: continue
            udp_start = ip_start + ihl
            if len(pkt) < udp_start + 8: continue
            udp_hdr = pkt[udp_start:udp_start+8]
            src_port = struct.unpack('!H', udp_hdr[0:2])[0]
            dst_port = struct.unpack('!H', udp_hdr[2:4])[0]
            payload = pkt[udp_start+8:]
            
            # S2C only
            if src_port == 18417 and len(payload) >= 8:
                ts = ts_sec + ts_usec / 1e6
                yield ts, bytes(payload)

# ================================================================
# Extract all 0x17.0xfe packets (93B)
# ================================================================
print("=== Step 1: Extract 0x17.0xfe 93B packets ===")
hb_pkts = []
all_s2c = 0
for ts, payload in read_pcap(PCAP):
    all_s2c += 1
    if payload[0] == 0x17 and payload[1] == 0xfe and len(payload) == 93:
        hb_pkts.append(payload)

print(f"Total S2C: {all_s2c}")
print(f"0x17.0xfe (93B): {len(hb_pkts)}")
print(f"Avg interval: {len(hb_pkts)/all_s2c*100:.1f}% of S2C traffic")
print()

# ================================================================
# A) Frequency analysis per byte position
# ================================================================
print("=== Step 2: Byte-level frequency analysis (header bytes only) ===")
for pos in range(8):
    counter = Counter(p[pos] for p in hb_pkts)
    top = counter.most_common(3)
    uniq = len(counter)
    line = f"  B[{pos}]: unique={uniq}"
    for rank, (val, cnt) in enumerate(top):
        line += f"  #{rank+1}=0x{val:02x}({cnt})"
    print(line)

# For payload bytes (offset 8+), find top value per position
print(f"\n  Payload bytes (offsets 8-92):")
zero_count = 0
for pos in range(8, 93):
    counter = Counter(p[pos] for p in hb_pkts)
    top = counter.most_common(1)[0]
    top_ratio = top[1] / len(hb_pkts) * 100
    if top_ratio > 90:
        zero_count += 1

print(f"  Positions with >90% same byte: {zero_count}/85")

# Show distribution of top-value concentration
bins = {">99.9%": 0, ">99%": 0, ">95%": 0, ">90%": 0, ">80%": 0, "<=80%": 0}
concentrations = []
for pos in range(8, 93):
    counter = Counter(p[pos] for p in hb_pkts)
    top_ratio = counter.most_common(1)[0][1] / len(hb_pkts) * 100
    concentrations.append((pos, top_ratio, counter.most_common(1)[0][0]))
    if top_ratio > 99.9: bins[">99.9%"] += 1
    elif top_ratio > 99: bins[">99%"] += 1
    elif top_ratio > 95: bins[">95%"] += 1
    elif top_ratio > 90: bins[">90%"] += 1
    elif top_ratio > 80: bins[">80%"] += 1
    else: bins["<=80%"] += 1

print(f"  Concentration distribution:")
for label, cnt in bins.items():
    bar = '#' * (cnt // 2)
    print(f"    {label:>6s}: {cnt:3d} {bar}")

# Show the "almost constant" bytes — candidates where plaintext is likely 0x00
print(f"\n  Positions with >99.9% stability (candidate for plaintext=0x00):")
for pos, ratio, val in concentrations:
    if ratio > 99.9:
        print(f"    B[{pos:2d}]: 0x{val:02x} ({ratio:.2f}%)")

print()
print("=== Step 3: Pairwise XOR — keystream reuse detection ===")
# Sample: first N packets XOR'd pairwise
N = 200
sample = hb_pkts[:N]

# For each byte position, XOR all pairs and count zero XOR = same keystream byte
reuse_counts = [0] * 93
pair_count = N * (N - 1) // 2
for i in range(N):
    for j in range(i + 1, N):
        for pos in range(93):
            xor = sample[i][pos] ^ sample[j][pos]
            if xor == 0:
                reuse_counts[pos] += 1

print(f"  Sample: {N} pkts, {pair_count} pairs")
print(f"  Keystream byte reuse (zero XOR) per position:")
for pos in range(93):
    rate = reuse_counts[pos] / pair_count * 100
    if rate > 0.1:  # only show notable positions
        print(f"    B[{pos:2d}]: {reuse_counts[pos]:5d}/{pair_count} ({rate:.2f}%)")

# ================================================================
# C) Simple XOR key brute-force
# ================================================================
print()
print("=== Step 4: Simple repeating XOR key test ===")

def score_plaintext(data):
    """Score likelihood of being valid plaintext (high entropy = bad)."""
    if len(data) < 4: return 0
    # Penalize non-printable bytes, reward ASCII range
    s = 0
    runs = 0
    prev = -1
    for b in data:
        if 0x20 <= b <= 0x7E:
            s += 2  # printable ASCII
        elif b == 0x00:
            s += 1  # null padding
        elif b == 0x0A or b == 0x0D:
            s += 1  # newline
        else:
            s -= 0.5  # non-printable
        
        if b == prev:
            runs += 1
        prev = b
    
    # Penalize long runs of same byte
    return s - runs * 0.5

# Try key lengths 1..32 on header bytes (0-7) which we expect to be structural
best_overall = (0, 0, b'', 0)
for keylen in range(1, 33):
    # For each keylen, find the best key that maximizes plaintext score
    # We brute-force each key byte separately for positions 0-7
    best_score = -9999
    best_key = None
    
    # For header bytes, try to find key that produces recognizable structure
    # B[4:6] should be 0x0000, B[6:8] should be 0x0001
    
    # For each byte position in header, find the most likely key byte
    # Key byte = ciphertext XOR expected_plaintext
    # For B[0]: expected = 0x17, B[1]: expected = 0xfe
    # For B[4]: expected = 0x00, B[5]: expected = 0x00
    # For B[6]: expected = 0x00, B[7]: expected = 0x01
    
    expected = {0: 0x17, 1: 0xfe, 4: 0x00, 5: 0x00, 6: 0x00, 7: 0x01}
    
    # Use the first packet to derive candidate key
    ref = hb_pkts[0]
    key_candidates = []
    for pos in range(min(keylen, 93)):
        if pos in expected:
            key_candidates.append(ref[pos] ^ expected[pos])
        else:
            # Try all 256 values, pick the one that gives best score across all pkts
            best_byte = 0
            best_byte_score = -9999
            for kb in range(256):
                score = sum(score_plaintext(bytes([p[pos] ^ kb])) for p in hb_pkts[:50])
                if score > best_byte_score:
                    best_byte_score = score
                    best_byte = kb
            key_candidates.append(best_byte)
    
    key = bytes(key_candidates)
    
    # Validate: decrypt first 50 packets and check if B[0] = 0x17, B[1] = 0xfe consistently
    valid = 0
    for p in hb_pkts[:50]:
        dec = bytes(p[i] ^ key[i % keylen] for i in range(min(8, len(p))))
        if dec[0] == 0x17 and dec[1] == 0xfe:
            valid += 1
    
    valid_rate = valid / 50 * 100
    if valid_rate > best_overall[3]:
        best_overall = (keylen, valid_rate, key, valid)

for keylen in [1, 2, 4, 8, 16, 32]:
    pass  # already handled above

# Also try: if key repeats every 4 bytes, what do we get?
print(f"  Best keylen={best_overall[0]} with {best_overall[1]:.0f}% valid on first 50 pkts")
print(f"  Key bytes: {best_overall[2].hex()}")

# ================================================================
# D) Show a few decrypted payloads with the best key
# ================================================================
print()
print("=== Step 5: Decrypt samples with best key ===")
keylen, _, key, _ = best_overall
for i in range(min(3, len(hb_pkts))):
    p = hb_pkts[i]
    dec = bytes(p[j] ^ key[j % keylen] for j in range(len(p)))
    print(f"  Pkt {i}:")
    print(f"    raw: {p[:32].hex()}")
    print(f"    dec: {dec[:32].hex()}")
    # Show as ASCII if readable
    try:
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dec[:64])
        print(f"    ascii: {ascii_str}")
    except:
        pass
    print()

# ================================================================
# E) Key insight: try to find pairs where XOR = 0x00 * 85 bytes
#    (same plaintext, different keystream → keystream XOR keystream)
# ================================================================
print("=== Step 6: Detect repeating keystream structure ===")

# Group packets by their first 4 encrypted header bytes (excluding timing-variant parts)
# If header is: op(1) subop(1) field(2) 0x0000 0x0001 payload(85)
# The field at B[2:4] might vary, rest should be constant
# Find groups where the encrypted representation is identical → keystream reused
from collections import defaultdict

groups = defaultdict(list)
for p in hb_pkts:
    # Group by full 93B ciphertext
    groups[p].append(p)

identical_groups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"  Completely identical 93B ciphertexts: {len(identical_groups)} groups")
total_identical = sum(len(v) for v in identical_groups.values())
print(f"  Total packets in identical groups: {total_identical}")

# Show top duplicates
sorted_groups = sorted(identical_groups.items(), key=lambda x: -len(x[1]))
for ctext, pkts in sorted_groups[:5]:
    print(f"    {len(pkts):4d} copies: {ctext[:16].hex()}...")

# Group by payload only (skip header bytes 0-7)
payload_groups = defaultdict(list)
for p in hb_pkts:
    payload_groups[p[8:]].append(p)

identical_payloads = {k: v for k, v in payload_groups.items() if len(v) > 1}
print(f"\n  Identical 85B payload (after 8B header): {len(identical_payloads)} groups")
total = sum(len(v) for v in identical_payloads.values())
print(f"  Total packets with duplicate payload: {total}")

print()
print("=== DONE ===")
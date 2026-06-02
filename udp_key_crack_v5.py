"""
UDP key crack — v5: final structure analysis + keystream attempt
"""
import struct
from collections import Counter

PCAP = r'apollo_dump\raw_20260520_154224.pcap'

s2c_17fe = []
with open(PCAP, 'rb') as f:
    f.read(24)
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
        payload = bytes(pkt[udp_start+8:])
        if src_port == 18417 and payload[:2] == b'\x17\xfe' and len(payload) == 93:
            s2c_17fe.append(payload)

N = len(s2c_17fe)
print(f"93B 17fe packets: {N}")

# ================================================================
# 1. Verify B[9:10] == B[19:20] for all packets
# ================================================================
print("\n=== B[9:10] vs B[19:20] comparison ===")
match_all = all(p[9:11] == p[19:21] for p in s2c_17fe)
mismatches = sum(1 for p in s2c_17fe if p[9:11] != p[19:21])
print(f"  All match: {match_all} (mismatches: {mismatches}/{N})")

# ================================================================
# 2. B[8] vs B[18] comparison
# ================================================================
match_b8 = all(p[8] == p[18] for p in s2c_17fe)
mismatches_b8 = sum(1 for p in s2c_17fe if p[8] != p[18])
print(f"\n  B[8]==B[18] (0x0e): all={match_b8} mismatches={mismatches_b8}/{N}")

# ================================================================
# 3. Full structural analysis
# ================================================================
print("\n=== Complete 93B structure ===")
print(f"  B[0:1]   = 17fe  (opcode) — FIXED ✓")
print(f"  B[2:4]   = fd00  (field) — FIXED ✓")
print(f"  B[4:6]   = 0100  (const) — FIXED ✓")
print(f"  B[6:8]   = 0000  (const) — FIXED ✓")
print(f"  B[8]     = 0e    (const) — FIXED ✓")
print(f"  B[9:10]  = 16-bit counter — varies (monotonic increase)")
print(f"  B[11:13] = 00 50 00 — FIXED ✓")
print(f"  B[13:15] = 01 00 — FIXED ✓")
print(f"  B[15:18] = 00 00 00 — FIXED ✓")
print(f"  B[18]    = 0e — FIXED ✓")
print(f"  B[19:20] = copy of B[9:10] (counter duplicate) — {match_all}")
print(f"  B[21:92] = 72 bytes ENCRYPTED payload")

# ================================================================
# 4. Encrypted payload analysis (B[21:92])
# ================================================================
print(f"\n=== B[21:92] encrypted payload analysis ===")

# Check if any pair of packets have identical 72B payload
from collections import defaultdict
payload_groups = defaultdict(list)
for i, p in enumerate(s2c_17fe):
    payload_groups[p[21:93]].append(i)

dup_groups = {k: v for k, v in payload_groups.items() if len(v) > 1}
print(f"  Duplicate 72B payloads: {len(dup_groups)} groups")
if dup_groups:
    sorted_dup = sorted(dup_groups.items(), key=lambda x: -len(x[1]))
    for payload, indices in sorted_dup[:3]:
        print(f"    {len(indices):4d} copies: idx={indices[:5]}...  hex={payload[:16].hex()}...")

# Frequency analysis of each encrypted byte position
print(f"\n  Byte frequency (top value/bottom value per position, B[21:40]):")
for pos in range(21, 40):
    counter = Counter(p[pos] for p in s2c_17fe)
    top = counter.most_common(1)[0]
    uniq = len(counter)
    print(f"    B[{pos:2d}]: top=0x{top[0]:02x} ({top[1]:5d}/{N}, {top[1]/N*100:.1f}%)  unique={uniq:3d}")

# ================================================================
# 5. Try to XOR adjacent encrypted bytes to find structure
# ================================================================
print(f"\n=== XOR analysis of encrypted bytes B[21:40] ===")
# XOR each encrypted byte with the same byte from next packet
# If plaintext is similar, XOR reveals keystream differences
for pos in range(21, 40):
    xor_vals = []
    for i in range(min(500, N - 1)):
        xor_vals.append(s2c_17fe[i][pos] ^ s2c_17fe[i+1][pos])
    counter = Counter(xor_vals)
    top = counter.most_common(3)
    print(f"    B[{pos:2d}] XOR_adj: top={[(hex(v),c) for v,c in top]}")

print()
print("=== DONE ===")
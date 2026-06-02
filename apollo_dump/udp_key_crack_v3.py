"""
UDP key crack — v3: pinpoint encryption boundary + C2S-S2C timing correlation
"""
import struct
from collections import Counter, defaultdict

PCAP = r'apollo_dump\raw_20260520_154224.pcap'

# Read ALL S2C and C2S with timestamps
s2c_all = []  # (ts, payload)
c2s_all = []  # (ts, payload) — only 907f magic
s2c_17fe = []  # (ts, payload) 93B heartbeat

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
        dst_port = struct.unpack('!H', udp_hdr[2:4])[0]
        payload = bytes(pkt[udp_start+8:])
        ts = ts_sec + ts_usec / 1e6
        
        if src_port == 18417 and len(payload) >= 8:
            s2c_all.append((ts, payload))
            if payload[0] == 0x17 and payload[1] == 0xfe and len(payload) == 93:
                s2c_17fe.append((ts, payload))
        elif dst_port == 18417 and len(payload) >= 16:
            magic = struct.unpack('<H', payload[0:2])[0]
            if magic == 0x7f90:  # 907f little-endian
                c2s_all.append((ts, payload))

print(f"S2C total: {len(s2c_all)}")
print(f"C2S total (907f): {len(c2s_all)}")
print(f"S2C 0x17.0xfe 93B: {len(s2c_17fe)}")
print()

# ================================================================
# 1. Pinpoint the exact encryption boundary in 93B packets
# ================================================================
print("=== 1. Encryption boundary in 93B 0x17.0xfe ===")
# Which bytes are identical across ALL 16073 packets?
fixed_positions = []
varying_positions = []
for pos in range(93):
    counter = Counter(p[pos] for _, p in s2c_17fe)
    if len(counter) == 1:
        fixed_positions.append(pos)
    else:
        varying_positions.append(pos)

print(f"  Fixed bytes (same in all 16K pkts): {len(fixed_positions)} / 93")
print(f"  Varying bytes: {len(varying_positions)} / 93")

# Show groups
def format_ranges(positions):
    if not positions: return "none"
    ranges = []
    start = positions[0]
    end = positions[0]
    for p in positions[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append((start, end))
            start = end = p
    ranges.append((start, end))
    return ', '.join(f'{s}-{e}' if s != e else f'{s}' for s, e in ranges)

print(f"  Fixed ranges: {format_ranges(fixed_positions)}")
print(f"  Varying ranges: {format_ranges(varying_positions)}")

# Show the actual byte values for fixed positions
print(f"\n  Fixed bytes dump:")
for start, end in [(0,19), (20,40), (41,60), (61,80), (81,92)]:
    seg = []
    for pos in range(max(start,0), min(end+1, 93)):
        if pos in fixed_positions:
            val = s2c_17fe[0][1][pos]
            seg.append(f"B[{pos:2d}]=0x{val:02x}")
    if seg:
        print(f"    {', '.join(seg)}")

# ================================================================
# 2. Analyze B[10] (varies per packet) — is it a counter?
# ================================================================
print(f"\n=== 2. B[10] analysis (varies per 93B pkt) ===")
b10_values = [p[10] for _, p in s2c_17fe]
b10_counter = Counter(b10_values)
print(f"  Unique B[10] values: {len(b10_counter)}")
print(f"  Top 10: {b10_counter.most_common(10)}")
print(f"  Min=0x{min(b10_values):02x} Max=0x{max(b10_values):02x}")

# Check if monotonically increasing
prev = -1
mono_inc = 0
mono_dec = 0
for v in b10_values:
    if v > prev:
        mono_inc += 1
    elif v < prev:
        mono_dec += 1
    prev = v
print(f"  Monotonic increase: {mono_inc}/{len(b10_values)} ({mono_inc/len(b10_values)*100:.1f}%)")
print(f"  Monotonic decrease: {mono_dec}/{len(b10_values)} ({mono_dec/len(b10_values)*100:.1f}%)")

# ================================================================
# 3. Show first 10 93B packets hex dump
# ================================================================
print(f"\n=== 3. First 10 93B packets (hex) ===")
for i in range(min(10, len(s2c_17fe))):
    ts, p = s2c_17fe[i]
    # Show fixed vs varying with markers
    parts = []
    for pos in range(min(32, len(p))):
        if pos in varying_positions:
            parts.append(f"[{p[pos]:02x}]")  # vary = brackets
        else:
            parts.append(f"{p[pos]:02x}")    # fixed = plain
    print(f"  #{i:4d} ts={ts:.3f}  {' '.join(parts)}")

# ================================================================
# 4. C2S ↔ S2C timing correlation
# ================================================================
print(f"\n=== 4. C2S ↔ S2C timing correlation ===")
print(f"  First C2S: ts={c2s_all[0][0]:.3f}")
print(f"  First S2C: ts={s2c_all[0][0]:.3f}")
print(f"  Last C2S:  ts={c2s_all[-1][0]:.3f}")
print(f"  Last S2C:  ts={s2c_all[-1][0]:.3f}")

# For each S2C 17fe, find the closest preceding C2S
matched = []
c2s_idx = 0
for ts_s2c, p_s2c in s2c_17fe[:500]:  # first 500 for speed
    # Find closest C2S before this S2C
    best_c2s = None
    best_dt = 999
    # Walk forward through C2S
    while c2s_idx < len(c2s_all) and c2s_all[c2s_idx][0] < ts_s2c:
        dt = ts_s2c - c2s_all[c2s_idx][0]
        if dt < best_dt and dt > 0:
            best_dt = dt
            best_c2s = c2s_all[c2s_idx]
        c2s_idx += 1
    # Don't rewind too far
    c2s_idx = max(0, c2s_idx - 20)
    
    if best_c2s:
        c2s_seq = struct.unpack('<H', best_c2s[1][2:4])[0]
        matched.append((ts_s2c, best_dt, c2s_seq, p_s2c[19]))

# Show timing distribution
dts = [m[1] for m in matched]
print(f"\n  Matched S2C→C2S pairs: {len(matched)}")
print(f"  Response delay (C2S→S2C 17fe):")
print(f"    Min={min(dts)*1000:.1f}ms  Max={max(dts)*1000:.1f}ms  Avg={sum(dts)/len(dts)*1000:.1f}ms")

# ================================================================
# 5. Try XOR of S2C B[19] with C2S seq_lo to see if there's correlation
# ================================================================
print(f"\n=== 5. S2C B[19] vs C2S seq correlation ===")
print(f"  First 20 matched pairs (ts, dt_ms, c2s_seq, s2c_B19):")
for i in range(min(20, len(matched))):
    ts, dt, c2s_seq, s2c_b19 = matched[i]
    xor_val = (c2s_seq & 0xFF) ^ s2c_b19
    print(f"    S2C ts={ts:.3f}  dt={dt*1000:6.1f}ms  c2s_seq=0x{c2s_seq:04x}  s2c_B19=0x{s2c_b19:02x}  XOR=0x{xor_val:02x}")

# ================================================================
# 6. Try to extract C2S header fields for known-plaintext
# ================================================================
print(f"\n=== 6. C2S packet structure summary ===")
# Show first 5 C2S packets with parsed header
for i in range(min(5, len(c2s_all))):
    ts, p = c2s_all[i]
    magic = struct.unpack('<H', p[0:2])[0]
    seq = struct.unpack('<H', p[2:4])[0]
    session = p[4:8].hex()
    const = p[8:12].hex()
    flags = p[12:16].hex()
    plen = len(p)
    print(f"  C2S ts={ts:.3f}  magic=0x{magic:04x} seq=0x{seq:04x} sess={session} const={const} flags={flags} plen={plen}")

print()
print("=== DONE ===")
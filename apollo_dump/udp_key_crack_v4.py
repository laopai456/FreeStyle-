"""
UDP key crack — v4: verify B[10] key discovery + extend to full payload
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

print(f"Total 93B 17fe packets: {len(s2c_17fe)}")
print()

# ================================================================
# 1. Verify: is B[9] always 0x89?
# ================================================================
b9_counter = Counter(p[9] for p in s2c_17fe)
print("=== B[9] distribution ===")
print(f"  Unique values: {len(b9_counter)}")
for val, cnt in b9_counter.most_common(5):
    print(f"    0x{val:02x}: {cnt}")
print()

# ================================================================
# 2. Verify B[10] = counter XOR 0x14
# ================================================================
print("=== B[10] analysis (XOR 0x14 with packet index) ===")
matches = 0
key_byte = -1
for i, p in enumerate(s2c_17fe[:2000]):
    # If key[i%N] XOR plaintext_counter = ciphertext
    # B[10] should decrypt to (i & 0xFF)
    for kb in range(256):
        pt = p[10] ^ kb
        if pt == (i & 0xFF):
            if key_byte < 0:
                key_byte = kb
            if kb == key_byte:
                matches += 1
            break

print(f"  Using key_byte=0x{key_byte:02x} ({key_byte}):")
print(f"  B[10] XOR 0x{key_byte:02x} = packet_index_lo: {matches}/{min(2000, len(s2c_17fe))} match")
print(f"  Rate: {matches/min(2000,len(s2c_17fe))*100:.1f}%")
print()

# Show first 20 verification
print("  First 20 packets:")
for i in range(20):
    p = s2c_17fe[i]
    decrypted = p[10] ^ key_byte
    expected = i & 0xFF
    ok = "✓" if decrypted == expected else f"✗(got {decrypted})"
    print(f"    pkt#{i:4d}: B[10]=0x{p[10]:02x}  XOR 0x{key_byte:02x} = {decrypted:3d}  expected={expected:3d}  {ok}")

# ================================================================
# 3. Try to derive full 74-byte keystream
#    Assumption: plaintext is mostly zeros for idle heartbeat
# ================================================================
print()
print("=== Full keystream derivation (assume plaintext is mostly 0x00) ===")

# If the heartbeat is an ACK with minimal data, the encrypted payload
# might be mostly zeros. Let's check frequency of each ciphertext byte
# position. The most common ciphertext byte = most likely keystream byte.

# But first, let's analyze: for bytes B[20-92], what's the distribution?
# Are they random or structured?

# Let's take the first 1000 packets and look at the encrypted payload
# XOR with packet index to see if there's a counter-based pattern
print("  B[20-92]: testing counter-based XOR...")
for shift_offset in range(10):  # try offset 0..9
    match_count = 0
    for i, p in enumerate(s2c_17fe[:1000]):
        idx = i & 0xFF
        # Try B[20] through B[29] with different key assumptions
        for byte_off in range(10):
            pos = 20 + byte_off
            if pos >= 93: break
            ct = p[pos]
            # If key = counter, then ct = pt XOR counter
            # pt probably = 0 for idle → ct = counter
            if ct == ((idx + shift_offset) & 0xFF):
                match_count += 1
    rate = match_count / (1000 * 10) * 100 if 1000 * 10 > 0 else 0
    if rate > 5:
        print(f"    offset={shift_offset}: {match_count}/{1000*10} ({rate:.1f}%)")

# Direct approach: show B[20] for first 30 packets
print()
print("  B[20:30] raw values for first 30 pkts:")
header = "    pkt#  " + " ".join(f"B[{p}]" for p in range(20, 30))
print(header)
for i in range(min(30, len(s2c_17fe))):
    vals = " ".join(f"  {s2c_17fe[i][p]:02x}" for p in range(20, 30))
    print(f"    {i:4d}  {vals}")

# ================================================================
# 4. Try the TCP key approach: XOR with 4db8a854 at offsets
# ================================================================
print()
print("=== Try TCP-style 4-byte repeating key ===")
tcp_key = bytes([0x4d, 0xb8, 0xa8, 0x54])
# Check if XOR with tcp_key at any offset reveals structure
for key_off in range(4):
    ok = 0
    for i, p in enumerate(s2c_17fe[:50]):
        dec_at_10 = p[10] ^ tcp_key[(10 + key_off) % 4]
        if dec_at_10 == (i & 0xFF):
            ok += 1
    print(f"  key_offset={key_off}: B[10] matches={ok}/50")

print()
print("=== DONE ===")
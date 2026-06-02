"""
udp_key_crack.py — 自动检测 UDP XOR key
聚焦 S2C 93B 高频包, 尝试已知 plaintext 推断 key
"""
import sys, os, struct
from collections import defaultdict, Counter

try:
    from scapy.all import rdpcap, IP, Raw
except ImportError:
    print("需要 scapy"); sys.exit(1)

if len(sys.argv) < 2:
    print("用法: py udp_key_crack.py apollo_dump/raw_XXXXXX.pcap")
    sys.exit(1)

pkts = rdpcap(sys.argv[1])

# 提取 S2C UDP: 223.166.22.186:18417 → 192.168.3.2:62204
s2c = []
c2s = []
for p in pkts:
    if not p.haslayer(IP) or not p.haslayer('UDP') or not p.haslayer(Raw):
        continue
    ip = p[IP]
    udp = p['UDP']
    payload = bytes(p[Raw].load)
    if ip.src == '223.166.22.186' and udp.sport == 18417 and ip.dst == '192.168.3.2':
        s2c.append((p.time, payload))
    elif ip.src == '192.168.3.2' and udp.sport == 62204 and ip.dst == '223.166.22.186':
        c2s.append((p.time, payload))

print(f'S2C: {len(s2c)} pkts, C2S: {len(c2s)} pkts')

# ================================================================
# 1. S2C header 分析
# ================================================================
print('\n========== S2C Header Analysis ==========')

# B[0-1] opcode
opcode_dist = Counter()
for ts, p in s2c:
    opcode_dist[p[0]] += 1
print('B[0] (opcode_hi) distribution:')
for k, v in sorted(opcode_dist.items()):
    print(f'  0x{k:02X}: {v:4d} pkts')

# B[1] sub-opcode
sub_dist = Counter()
for ts, p in s2c:
    sub_dist[(p[0], p[1])] += 1
print('\nB[0:1] (opcode pair) top 10:')
for (k1, k2), v in sorted(sub_dist.items(), key=lambda x: -x[1])[:10]:
    print(f'  {k1:02X}{k2:02X}: {v:4d} pkts')

# B[2-3] length field
print('\nB[2:3] (len field) sample:')
for ts, p in s2c[:10]:
    print(f'  op={p[0]:02X}{p[1]:02X}  len_LE={struct.unpack_from("<H", p, 2)[0]}  total_pkt_len={len(p)}')

# ================================================================
# 2. 93B 包深度分析 (1631 个)
# ================================================================
p93 = [(ts, p) for ts, p in s2c if len(p) == 93]
print(f'\n========== S2C 93B packets ({len(p93)} total) ==========')

# 前 20 个 93B 包 full hex
print('\nFirst 10 × 93B packets (full hex):')
for i in range(min(10, len(p93))):
    ts, p = p93[i]
    print(f'  [{i}] {p.hex()}')

# B[0:1] opcode distribution for 93B
op93 = Counter()
for ts, p in p93:
    op93[p[1]] += 1
print('\n93B B[1] distribution:')
for k, v in sorted(op93.items()):
    print(f'  0x{k:02X}: {v:4d}')

# ================================================================
# 3. XOR key auto-detect
# 假设: header[0:8] 明文不变, 加密从 offset 8 开始
# 如果 93B 包都是同类型 (相同 plaintext), XOR 后应得到相同结果
# ================================================================
print('\n========== XOR key auto-detect ==========')

# 取所有 93B 包, 同 opcode 分组
by_op = defaultdict(list)
for ts, p in p93:
    by_op[p[1]].append(p)

# 对每组, 假设 body (offset 8+) 明文相同, 则 XOR(p1[8:], p2[8:]) = XOR(plain, plain) = 0
# 如果不为 0, 说明要么 key 不同, 要么 body 不同
for b1_val, pkts_list in sorted(by_op.items()):
    if len(pkts_list) < 2:
        continue
    p0 = pkts_list[0]
    p1 = pkts_list[1]
    xored = bytes(p0[i] ^ p1[i] for i in range(8, len(p0)))
    zeros = sum(1 for b in xored if b == 0)
    print(f'\nB[1]=0x{b1_val:02X} ({len(pkts_list)} pkts):')
    print(f'  P0[0:8] = {p0[:8].hex()}')
    print(f'  P1[0:8] = {p1[:8].hex()}')
    print(f'  XOR body[8:]: {zeros}/{len(xored)} zero bytes ({100*zeros//len(xored)}%)')
    print(f'  first 32B of XOR: {xored[:32].hex()}')
    if xored[:16] == b'\x00' * 16:
        print(f'  ★ Body is CONSTANT across these packets! (XOR = all zeros)')
    else:
        print(f'  Body varies between packets (XOR ≠ all zeros)')

# ================================================================
# 4. 尝试 key = C2S session_id 或其变体
# ================================================================
print('\n========== Key candidates ==========')
if c2s:
    c0 = c2s[0][1]
    # C2S header: 907f [seq] [sid_hi] [sid_lo] [flags]
    sid_hi = struct.unpack_from('<I', c0, 4)[0]   # 7cd4f44f
    sid_lo = struct.unpack_from('<I', c0, 8)[0]   # 9ae530cb
    seq = struct.unpack_from('<H', c0, 2)[0]       # 0e39
    print(f'C2S seq={seq:04X}')
    print(f'C2S sid_h={sid_hi:08X}  sid_l={sid_lo:08X}')

    # Try as XOR key
    keys = [
        (b'sid_h', struct.pack('<I', sid_hi)),
        (b'sid_l', struct.pack('<I', sid_lo)),
        (b'seq_le', struct.pack('<H', seq)),
        (b'magic', b'\x90\x7f'),
        (b'sid_h+sid_l', struct.pack('<II', sid_hi, sid_lo)),
    ]

    if s2c:
        # Take first S2C 93B with most common opcode
        s0 = p93[0][1]
        for name, key in keys:
            try:
                dec = bytes((s0[8+i] ^ key[i % len(key)]) & 0xFF for i in range(min(32, len(s0)-8)))
                print(f'Key {name.decode()}: {key.hex():20s} → dec[8:40]: {dec.hex()}')
            except:
                print(f'Key {name.decode()}: {key.hex():20s} → ERROR')

# ================================================================
# 5. 跨 93B 包 body 稳定性检查
# 如果 B[1] 相同但 body XOR ≠ 0, 分析差异位置
# ================================================================
print('\n========== Body diff analysis (93B, same B[1]) ==========')
for b1_val, pkts_list in sorted(by_op.items()):
    if len(pkts_list) < 3:
        continue
    # 比较前 3 个, 看哪些 byte position 不同
    diffs = set()
    p0 = pkts_list[0]
    for p in pkts_list[1:4]:
        for i in range(8, len(p0)):
            if p0[i] != p[i]:
                diffs.add(i - 8)  # relative to body start
    diff_pct = len(diffs) / (len(p0) - 8) * 100
    if diff_pct < 20:
        print(f'B[1]=0x{b1_val:02X}: only {len(diffs)}/{len(p0)-8} bytes differ ({diff_pct:.1f}%) '
              f'at positions: {sorted(diffs)[:20]}...')
"""
udp_diag.py — 从 pcap 提取 UDP 游戏流量, 分析头部格式
用法: py udp_diag.py <pcap_file>
"""
import sys, os, struct
from collections import defaultdict

try:
    from scapy.all import rdpcap, IP, Raw
except ImportError:
    print("需要 scapy"); sys.exit(1)

if len(sys.argv) < 2:
    print("用法: py udp_diag.py apollo_dump/raw_XXXXXX.pcap")
    sys.exit(1)

pkts = rdpcap(sys.argv[1])
print(f'Total: {len(pkts)} packets')

# 分组 UDP 流: (src_ip, src_port, dst_ip, dst_port)
udp_flows = defaultdict(list)
for p in pkts:
    if not p.haslayer(IP) or not p.haslayer('UDP') or not p.haslayer(Raw):
        continue
    ip = p[IP]
    udp = p['UDP']
    payload = bytes(p[Raw].load)
    if len(payload) < 4:
        continue
    udp_flows[(ip.src, udp.sport, ip.dst, udp.dport)].append(payload)

# 按数据量排序
print(f'\nUDP flows (by volume):')
flow_by_size = sorted(udp_flows.items(), key=lambda x: -sum(len(p) for p in x[1]))
for key, pkts_list in flow_by_size[:6]:
    total = sum(len(p) for p in pkts_list)
    print(f'  {key[0]}:{key[1]} -> {key[2]}:{key[3]}  |  {len(pkts_list)} pkts, {total/1024:.1f} KB')

# 找客户端→服务器的流 (192.168.3.2 → remote)
# 和服务端→客户端的流 (remote → 192.168.3.2)
client_key = None
server_key = None
for key in udp_flows:
    if key[0] == '192.168.3.2' and not client_key:
        client_key = key
    elif key[2] == '192.168.3.2' and not server_key:
        server_key = key

if not client_key:
    # 找第一个出站流
    for key in udp_flows:
        if key[0] == '192.168.3.2':
            client_key = key
            break
    if not client_key:
        print('No client→server UDP flow found')
        sys.exit(0)

# 找对应的入站流
rev = (client_key[2], client_key[3], client_key[0], client_key[1])
if rev in udp_flows:
    server_key = rev

print(f'\nClient→Server: {client_key[0]}:{client_key[1]} -> {client_key[2]}:{client_key[3]}')
if server_key:
    print(f'Server→Client: {server_key[0]}:{server_key[1]} -> {server_key[2]}:{server_key[3]}')

# 分析客户端包
client_pkts = udp_flows[client_key]
print(f'\n========== CLIENT packets (first 5) ==========')
for i, p in enumerate(client_pkts[:5]):
    print(f'\n--- C2S #{i} ({len(p)}B) ---')
    print(f'  FULL HEX: {p.hex()}')
    # 尝试分析首字节模式
    print(f'  B[0:4]:  {p[0]:02x} {p[1]:02x} {p[2]:02x} {p[3]:02x}  '
          f'(LE u32={struct.unpack_from("<I", p)[0]})')
    if len(p) >= 8:
        print(f'  B[4:8]:  {p[4]:02x} {p[5]:02x} {p[6]:02x} {p[7]:02x}  '
              f'(LE u32={struct.unpack_from("<I", p, 4)[0]})')
    if len(p) >= 12:
        print(f'  B[8:12]: {p[8]:02x} {p[9]:02x} {p[10]:02x} {p[11]:02x}  '
              f'(LE u32={struct.unpack_from("<I", p, 8)[0]})')

# 分析服务端包
if server_key:
    server_pkts = udp_flows[server_key]
    print(f'\n========== SERVER packets (first 5) ==========')
    for i, p in enumerate(server_pkts[:5]):
        print(f'\n--- S2C #{i} ({len(p)}B) ---')
        print(f'  FULL HEX: {p.hex()}')
        print(f'  B[0:4]:  {p[0]:02x} {p[1]:02x} {p[2]:02x} {p[3]:02x}  '
              f'(LE u32={struct.unpack_from("<I", p)[0]})')
        if len(p) >= 8:
            print(f'  B[4:8]:  {p[4]:02x} {p[5]:02x} {p[6]:02x} {p[7]:02x}  '
                  f'(LE u32={struct.unpack_from("<I", p, 4)[0]})')

# 尝试 XOR KEY 解密
print(f'\n========== XOR key search ==========')
# 已知 TCP key: 4db8a854
KEY = [0x4d, 0xb8, 0xa8, 0x54]
if client_pkts:
    sample = client_pkts[0][:16]
    xored = bytes((sample[i] ^ KEY[i % 4]) & 0xFF for i in range(len(sample)))
    print(f'  KEY=4db8a854  C2S dec(16B): {xored.hex()}')

if server_key and server_pkts:
    sample = server_pkts[0][:16]
    xored = bytes((sample[i] ^ KEY[i % 4]) & 0xFF for i in range(len(sample)))
    print(f'  KEY=4db8a854  S2C dec(16B): {xored.hex()}')

# 包大小分布
print(f'\n========== Packet size distribution ==========')
sz_dist = defaultdict(int)
for p in client_pkts:
    sz_dist[len(p)] += 1
print(f'C2S: {dict(sorted(sz_dist.items()))}')

if server_key:
    sz_dist2 = defaultdict(int)
    for p in server_pkts:
        sz_dist2[len(p)] += 1
    print(f'S2C: {dict(sorted(sz_dist2.items()))}')

# 搜索 TCP 游戏 magic 也搜一下
MAGIC = bytes([0x43, 0xd5, 0x8b, 0x80])
found_magic = False
for key, pkts_list in udp_flows.items():
    for p in pkts_list:
        if MAGIC in p:
            print(f'\n*** FOUND TCP MAGIC in UDP {key} ! ***')
            found_magic = True
if not found_magic:
    print(f'\nNo TCP magic (43d58b80) in UDP flows (UDP uses different format)')
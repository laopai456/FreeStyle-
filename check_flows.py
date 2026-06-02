from scapy.all import rdpcap, IP, Raw
from collections import defaultdict
import sys

pkts = rdpcap(r'D:\py\反编译\FreeStyle\apollo_dump\raw_20260520_152136.pcap')
udp_flows = defaultdict(list)
tcp_game = defaultdict(list)

for p in pkts:
    if not p.haslayer(IP):
        continue
    ip = p[IP]
    if p.haslayer('UDP') and p.haslayer(Raw):
        udp_flows[(ip.src, p['UDP'].sport, ip.dst, p['UDP'].dport)].append(p)
    elif p.haslayer('TCP') and p.haslayer(Raw):
        payload = bytes(p[Raw].load)
        if b'\x43\xd5\x8b\x80' in payload:
            tcp_game[(ip.src, p['TCP'].sport, ip.dst, p['TCP'].dport)].append(p)

print('Game TCP flows:')
for k, v in tcp_game.items():
    payloads = [bytes(p[Raw].load) for p in v if p.haslayer(Raw)]
    total = sum(len(p) for p in payloads)
    print(f'  {k[0]}:{k[1]} -> {k[2]}:{k[3]}  x{len(v)} pkts, {total} bytes')

print(f'\nUDP flows (all):')
for k, v in sorted(udp_flows.items(), key=lambda x: -len(x[1]))[:10]:
    payloads = [bytes(p[Raw].load) for p in v if p.haslayer(Raw)]
    total = sum(len(p) for p in payloads)
    print(f'  {k[0]}:{k[1]} -> {k[2]}:{k[3]}  x{len(v)} pkts, {total//1024}KB')

print(f'\nUDP flows matching prev game IP (223.166.22.186):')
game_udp = {k: v for k, v in udp_flows.items() if '223.166.22.186' in k}
if game_udp:
    for k, v in game_udp.items():
        print(f'  {k[0]}:{k[1]} -> {k[2]}:{k[3]}  x{len(v)} pkts')
else:
    print('  NONE — no UDP to 223.166.22.186')
    print('  (game may use different server IP this session)')

# Also check for game-like UDP traffic (907f magic)
print(f'\nUDP flows with 907f magic:')
for k, v in udp_flows.items():
    for p in v:
        if p.haslayer(Raw):
            raw = bytes(p[Raw].load)
            if len(raw) >= 2 and raw[0] == 0x90 and raw[1] == 0x7f:
                print(f'  {k[0]}:{k[1]} -> {k[2]}:{k[3]}  x{len(v)} pkts')
                break
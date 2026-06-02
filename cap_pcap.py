"""
cap_pcap.py — 网卡层双向抓包 (Npcap/scapy)
输出: apollo_dump/raw_YYYYMMDD_HHMMSS.pcap
Ctrl+C 停止
"""
import os, sys, time, datetime
sys.path.insert(0, os.path.dirname(__file__))

from scapy.all import sniff, wrpcap, conf

OUT_DIR = os.path.join(os.path.dirname(__file__), 'apollo_dump')
os.makedirs(OUT_DIR, exist_ok=True)

ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_FILE = os.path.join(OUT_DIR, f'raw_{ts}.pcap')

print(f'[cap] Output: {OUT_FILE}')
print(f'[cap] Interfaces:')
for i, iface in enumerate(conf.ifaces):
    print(f'  [{i}] {iface}')
print()

# 自动选默认路由的接口
try:
    IFACE = conf.iface
    print(f'[cap] Using: {IFACE}')
except:
    IFACE = None
    print('[cap] Auto-detect failed, sniffing on all...')

print(f'[cap] Sniffing ALL traffic on [{IFACE}]... (Ctrl+C to stop)')
pkts = []

try:
    pkts = sniff(iface=IFACE, store=True,
                 timeout=None, count=0)  # no filter, capture everything
except KeyboardInterrupt:
    pass
except Exception as e:
    print(f'[cap] Admin mode required! 请以管理员身份运行终端。')
    print(f'[cap] Error: {e}')
    sys.exit(1)

if pkts:
    wrpcap(OUT_FILE, pkts)
    print(f'\n[cap] Saved {len(pkts)} packets to {OUT_FILE}')
    print(f'[cap] Run: py analyze_pcap.py {OUT_FILE}')
else:
    print('\n[cap] No packets captured.')
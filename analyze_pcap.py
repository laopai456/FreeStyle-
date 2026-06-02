"""
analyze_pcap.py — 从 pcap 提取游戏包
识别 magic 43d58b80, 按 TCP 流分离 IN/OUT, 解密, 输出 CSV
用法: py analyze_pcap.py apollo_dump/raw_20260520_HHMMSS.pcap
"""
import os, sys, csv, struct, datetime
from collections import defaultdict

KEY = [0x4d, 0xb8, 0xa8, 0x54]
MAGIC = bytes([0x43, 0xd5, 0x8b, 0x80])

try:
    from scapy.all import rdpcap, IP, TCP, Raw
except ImportError:
    print("需要 scapy: py -m pip install scapy")
    sys.exit(1)

def xor_dec(data, off=0):
    return bytes((data[i] ^ KEY[(i - off) % 4]) & 0xFF for i in range(off, len(data)))

def extract_packet(data, direction, pkt_idx, src_ip, src_port, dst_ip, dst_port):
    """从 TCP payload 提取游戏包. data 从 43d58b80 magic 开始."""
    if len(data) < 20:
        return None
    f12 = struct.unpack_from('<I', data, 12)[0]
    seq = struct.unpack_from('<I', data, 16)[0]
    enc = data[20:]
    dec = xor_dec(data, 20)
    plen = len(dec)
    b0 = enc[0] if enc else 0
    d0 = dec[0] if dec else 0

    return {
        'idx': pkt_idx,
        'dir': direction,
        'conn': f'{src_ip}:{src_port}↔{dst_ip}:{dst_port}',
        'f12': f12,
        'seq': seq,
        'plen': plen,
        'b0': b0,
        'd0': d0,
        'enc': enc.hex(),
        'dec': dec.hex(),
        'raw': data.hex(),
        'raw_len': len(data),
    }

def analyze_pcap(filepath):
    print(f'[analyze] Loading {filepath}...')
    pkts = rdpcap(filepath)
    print(f'[analyze] {len(pkts)} total packets')

    # 按 (src_ip, src_port, dst_ip, dst_port) 分组, 支持 TCP & UDP
    flows = defaultdict(list)
    for pkt in pkts:
        if not pkt.haslayer(IP):
            continue
        ip = pkt[IP]
        proto = ip.proto
        if pkt.haslayer(TCP):
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
        elif pkt.haslayer('UDP'):
            sport = pkt['UDP'].sport
            dport = pkt['UDP'].dport
        else:
            continue
        if not pkt.haslayer(Raw):
            continue
        payload = bytes(pkt[Raw].load)
        if len(payload) < 8:
            continue
        flows[(ip.src, sport, ip.dst, dport, proto)].append((pkt.time, payload))

    print(f'[analyze] {len(flows)} IP flows with payload')

    # 找包含 game magic 的流
    game_flows = []
    for key, segments in flows.items():
        for ts, payload in segments:
            if MAGIC in payload:
                game_flows.append((key, segments))
                break

    if not game_flows:
        print('[analyze] No game packets found (magic 43d58b80 not in any IP flow)')
        # 列出所有流的前 32 字节帮助诊断
        print('\n[analyze] All IP flows first 32 bytes (diagnostic):')
        proto_names = {6: 'TCP', 17: 'UDP'}
        for key, segments in sorted(flows.items(), key=lambda x: -sum(len(s[1]) for s in x[1]))[:20]:
            total = sum(len(s[1]) for s in segments)
            preview = segments[0][1][:32].hex()
            proto_str = proto_names.get(key[4], str(key[4]))
            print(f'  {proto_str} {key[0]}:{key[1]} → {key[2]}:{key[3]}  ({total}B)  {preview}')
        return

    print(f'[analyze] Found {len(game_flows)} game flow(s)')

    results = []
    seen_seq = set()

    for flow_key, segments in game_flows:
        src_ip, src_port, dst_ip, dst_port, proto = flow_key

        # 推断方向: 第一个出现 magic 的方向是 OUT (客户端→服务器)
        # 反向流 = IN (服务器→客户端)
        rev_key = (dst_ip, dst_port, src_ip, src_port, proto)

        for ts, payload in segments:
            data = payload
            offset = 0
            while True:
                idx = data.find(MAGIC, offset)
                if idx < 0:
                    break
                packet_data = data[idx:]
                if len(packet_data) < 20:
                    offset = idx + 1
                    continue

                direction = 'OUT'
                seq_f12 = (struct.unpack_from('<I', packet_data, 16)[0],
                           struct.unpack_from('<I', packet_data, 12)[0])
                if seq_f12 in seen_seq:
                    offset = idx + 4
                    continue
                seen_seq.add(seq_f12)

                pkt = extract_packet(packet_data, direction, len(results) + 1,
                                     src_ip, src_port, dst_ip, dst_port)
                if pkt:
                    results.append(pkt)
                offset = idx + 4

        # 处理反向流 (服务端→客户端 IN)
        rev_segments = flows.get(rev_key, [])
        for ts, payload in rev_segments:
            data = payload
            offset = 0
            while True:
                idx = data.find(MAGIC, offset)
                if idx < 0:
                    break
                packet_data = data[idx:]
                if len(packet_data) < 20:
                    offset = idx + 1
                    continue

                direction = 'IN'
                seq_f12 = (struct.unpack_from('<I', packet_data, 16)[0],
                           struct.unpack_from('<I', packet_data, 12)[0])
                if seq_f12 in seen_seq:
                    offset = idx + 4
                    continue
                seen_seq.add(seq_f12)

                pkt = extract_packet(packet_data, direction, len(results) + 1,
                                     dst_ip, dst_port, src_ip, src_port)
                if pkt:
                    results.append(pkt)
                offset = idx + 4

    # 按时间排序 (pcap 本身已按时间)
    if not results:
        print('[analyze] No game packets extracted.')
        return

    # 统计数据
    out_count = sum(1 for r in results if r['dir'] == 'OUT')
    in_count = sum(1 for r in results if r['dir'] == 'IN')
    unknown_count = sum(1 for r in results if r['dir'] == '??')
    print(f'[analyze] Extracted: OUT={out_count} IN={in_count} UNK={unknown_count} TOTAL={len(results)}')

    # 输出 CSV
    csv_path = filepath.replace('.pcap', '.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'idx', 'dir', 'conn', 'f12', 'seq', 'plen', 'b0', 'd0', 'enc', 'dec'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    print(f'[analyze] Saved {csv_path}')

    # 简要分析
    d0_dist = defaultdict(list)
    for r in results:
        d0_dist[r['d0']].append(r['plen'])
    print(f'\n[analyze] d0 distribution (top 15):')
    for d0, plens in sorted(d0_dist.items(), key=lambda x: -len(x[1]))[:15]:
        extra = f'  {"":10s}'
        if len(plens) > 5:
            plen_sum = defaultdict(int)
            for p in plens:
                plen_sum[p] += 1
            plen_str = ', '.join(f'{s}B×{c}' for s, c in sorted(plen_sum.items()))
        else:
            plen_str = ', '.join(f'{p}B' for p in plens)
        print(f'  0x{d0:02X}: {len(plens):4d} pkts | {plen_str}')

    # IN 包是否有数据
    if in_count > 0:
        print(f'\n========== INBOUND PACKETS FOUND! ==========')
        for r in results:
            if r['dir'] == 'IN':
                print(f'  IN seq={r["seq"]} d0=0x{r["d0"]:02X} plen={r["plen"]}B  dec={r["dec"][:32]}...')
    else:
        print(f'\n[analyze] IN still 0. d0の方向可能未正确推断.')

    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: py analyze_pcap.py apollo_dump/raw_YYYYMMDD_HHMMSS.pcap")
        sys.exit(1)
    analyze_pcap(sys.argv[1])
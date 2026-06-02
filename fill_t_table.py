#!/usr/bin/env python3
"""
fill_t_table.py — 合并 S1-S5 全部 plen=8 包，填充 T[b0] 256 条目表

T[b0] 公式:
  f12(b0, seq) = SessionKey XOR T[b0] XOR ((seq & 1) ? U_PARITY : 0)
  where U_PARITY = 0xDD45AAB8

策略:
  1. 所有 session 内部先消除 seq parity → 得到 SK_XOR_T = SessionKey XOR T[b0]
  2. 用最常见的 b0 (通常是 0x00 心跳) 跨 session 对齐 → 得到相对 T[b0]
  3. 缺失条目用 Mode A / Mode B 模式推断
"""

import csv, re, os, sys
from collections import defaultdict

# ============================================================
# 常量
# ============================================================
U_PARITY   = 0xDD45AAB8       # seq 奇偶交替微分
K_X        = 0xBF672381       # T 的 pair 间差分 (b0 & 2)
ROOT       = os.path.dirname(os.path.abspath(__file__))
DUMP_DIR   = os.path.join(ROOT, 'apollo_dump')
MAGIC      = b'\x80\x8b\xd5\x43'  # 43d58b80 little-endian

# Mode A 的 D[k] 值 (k mod 4)
D_TABLE = {
    1: 0xC4451272,
    2: 0x32017194,
    3: 0xC4451272,
    # k mod 4 = 0: 随 k 变化
    0:  {0: 0, 4: 0x0C40D422, 8: 0xDB65C0A9, 12: 0xDB65C0A9,
         16: 0xDB65C0A9, 20: 0x0C40D422, 24: 0x0C40D422, 28: 0xDB65C0A9,
         # >= 0x20: D=0 (conjecture)
         }
}

def to_unsigned(v32):
    """把有符号 int32 转无符号"""
    return v32 & 0xFFFFFFFF

def parse_correct_buf(path):
    """解析 correct_buf.txt (S1, 纯文本格式)"""
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 匹配每一块: [GAME_PKT#N] seq=N len=N field12=0xHEX ... enc_full: HEX ... pl_full: HEX ...
    pattern = r'\[GAME_PKT#\d+\]\s+seq=(\d+)\s+len=\d+\s+field12=0x([-0-9A-Fa-f]+)\s*\n\s+enc_full:\s+([0-9A-Fa-f ]+)\s*\n\s+pl_full:\s+([0-9A-Fa-f ]+)'
    for m in re.finditer(pattern, text):
        seq = int(m.group(1))
        f12 = int(m.group(2), 16)
        enc_hex = m.group(3).replace(' ', '')
        b0 = int(enc_hex[:2], 16)
        plen = len(enc_hex) // 2  # payload length in bytes
        pkts.append({'session': 'S1', 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

def parse_old_csv(path, session_name):
    """解析旧格式 CSV: idx,len,f12,seq,plen,enc_prefix,dec_prefix,raw_hex"""
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plen = int(row['plen'])
            seq = int(row['seq'])
            f12 = int(row['f12'])
            raw = row.get('raw_hex', '')
            if len(raw) >= 42:
                b0 = int(raw[40:42], 16)
            else:
                enc = row.get('enc_prefix', '')
                b0 = int(enc[:2], 16) if enc else 0
            pkts.append({'session': session_name, 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

def parse_new_csv(path, session_name):
    """解析新格式 CSV: idx,dir,f12,seq,plen,b0,d0,enc,dec"""
    pkts = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plen = int(row['plen'])
            seq = int(row['seq'])
            f12 = int(row['f12'])
            b0 = int(row['b0'], 16) if row['b0'].startswith('0x') or row['b0'].startswith('-') \
                 else int(row['b0'])
            pkts.append({'session': session_name, 'seq': seq, 'f12': f12, 'b0': b0, 'plen': plen})
    return pkts

def calc_session_skt(entries):
    """对单个 session 的条目，计算 SK_XOR_T = f12 ^ parity_adj"""
    result = []
    for e in entries:
        f12_u = to_unsigned(e['f12'])
        parity_adj = U_PARITY if (e['seq'] & 1) else 0
        sk_xor_t = f12_u ^ parity_adj  # = SessionKey ^ T[b0]
        result.append({**e, 'sk_xor_t': sk_xor_t})
    return result

def align_sessions(all_sessions):
    """
    跨 session 对齐 T[b0] 表
    策略: 对每个 b0 值, 收集所有 session 的 sk_xor_t。
    T_ref[b0] = 最频繁的 session 的 sk_xor_t, 其他 session 偏移量由公共 b0 导出。
    """
    # 收集每个 session 的 (b0 → sk_xor_t) 映射
    sess_b0_map = defaultdict(dict)  # session → {b0: sk_xor_t}
    for sess_name, entries in all_sessions.items():
        for e in entries:
            b0 = e['b0']
            # 同 b0 多包取最新的(最后出现的)
            sess_b0_map[sess_name][b0] = e['sk_xor_t']

    # 找所有 session 都有的公共 b0
    common_b0s = set.intersection(*[set(m.keys()) for m in sess_b0_map.values()]) if len(sess_b0_map) > 1 else set()
    if common_b0s:
        ref_b0 = min(common_b0s)  # 取最小的 (通常是 0x00)
    else:
        ref_b0 = next(iter(sess_b0_map[list(sess_b0_map.keys())[0]].keys()))  # fallback

    # 选 S5 (最新的) 作为 reference session
    sess_names = sorted(sess_b0_map.keys())
    ref_session = sess_names[-1]  # S5
    ref_map = sess_b0_map[ref_session]

    # 对每个 session 计算偏移: offset[sess] = sk_xor_t[ref_b0]_ref ^ sk_xor_t[ref_b0]_sess
    sess_offset = {}
    for sess_name in sess_names:
        if ref_b0 in sess_b0_map[sess_name]:
            sess_offset[sess_name] = ref_map[ref_b0] ^ sess_b0_map[sess_name][ref_b0]
        else:
            sess_offset[sess_name] = 0

    # 构建合并的 sk_xor_t 表: 对每个 b0, 取 ref_session 的值, 其他 session 用偏移修正后平均
    # 简化: 每个 b0 取 ref_session 的值 (如果有), 否则用其他 session 修正
    merged = {}
    for b0 in range(256):
        candidates = []
        for sess_name in sess_names:
            if b0 in sess_b0_map[sess_name]:
                corrected = sess_b0_map[sess_name][b0] ^ sess_offset[sess_name]
                candidates.append(corrected)
        if candidates:
            # 取众数, 如果都一样就取第一个
            from collections import Counter
            merged[b0] = Counter(candidates).most_common(1)[0][0]
    return merged, sess_offset, ref_b0, ref_session

def analyze_patterns(t_ref):
    """分析 T[b0] 表是否符合 Mode A / Mode B 模式"""
    filled = set(t_ref.keys())
    total = len(filled)

    # 分类
    mode_a_ok = 0    # b0 < 0x80, 符合模式 A
    mode_b_ok = 0    # b0 >= 0x80, 符合模式 B
    mode_a_expected = set(range(0, 0x80))
    mode_b_expected = set(range(0x80, 0x100))

    missing = [b0 for b0 in range(256) if b0 not in filled]
    missing_a = [b0 for b0 in missing if b0 < 0x80]
    missing_b = [b0 for b0 in missing if b0 >= 0x80]

    print(f"\n{'='*60}")
    print(f"  T[b0] TABLE STATUS")
    print(f"{'='*60}")
    print(f"  Filled: {total}/256 ({total*100/256:.1f}%)")
    print(f"  Mode A (b0 < 0x80): {len(filled & mode_a_expected)}/128 filled, {len(missing_a)} missing")
    print(f"  Mode B (b0 >= 0x80): {len(filled & mode_b_expected)}/128 filled, {len(missing_b)} missing")

    # 缺失分布分析
    print(f"\n  --- Missing b0 distribution ---")
    if missing:
        # 按 nibble group (b0 >> 2) 统计
        groups = defaultdict(list)
        for b0 in missing:
            groups[b0 >> 2].append(b0)
        print(f"  Missing across {len(groups)} nibble groups:")
        for g in sorted(groups.keys()):
            b0s = sorted(groups[g])
            b0_range = f"0x{g*4:02X}-0x{g*4+3:02X}"
            missing_in_group = [f"0x{b:02X}" for b in b0s]
            mode = 'A' if g*4 < 0x80 else 'B'
            k = g
            k_mod_4 = k % 4
            d_info = ""
            if mode == 'A':
                d_info = f" k%4={k_mod_4}"
                if k_mod_4 == 0 and k in D_TABLE[0]:
                    d_info += f" D=0x{D_TABLE[0][k]:08X}"
                elif k_mod_4 == 0 and k >= 0x20:
                    d_info += " D=0(subgroup)"
            print(f"    {b0_range} ({mode}, k={g}){d_info}: {' '.join(missing_in_group)}")
    else:
        print("  NONE — 全部 256 条目已填满!")

    # 验证已填充条目的模式一致性
    print(f"\n  --- Pattern validation ---")
    mismatches = []
    for k in range(64):
        base = k * 4
        b0_set = set(range(base, base+4))
        have = b0_set & filled
        if len(have) < 2:
            continue
        if base < 0x80:
            # Mode A: T[4k] == T[4k+3], T[4k+2] == T[4k] ^ K_X
            if base in t_ref and base+3 in t_ref:
                if t_ref[base] != t_ref[base+3]:
                    mismatches.append(f"ModeA T[{base}]={t_ref[base]:08X} != T[{base+3}]={t_ref[base+3]:08X}")
            if base in t_ref and base+2 in t_ref:
                expected = t_ref[base] ^ K_X
                if t_ref[base+2] != expected:
                    mismatches.append(f"ModeA T[{base+2}]={t_ref[base+2]:08X} != T[{base}]^K_X={expected:08X}")
        else:
            # Mode B: T[4k] == T[4k+1], T[4k+2] == T[4k+3] == T[4k] ^ K_X
            if base in t_ref and base+1 in t_ref:
                if t_ref[base] != t_ref[base+1]:
                    mismatches.append(f"ModeB T[{base}]={t_ref[base]:08X} != T[{base+1}]={t_ref[base+1]:08X}")
            if base in t_ref and base+2 in t_ref:
                expected = t_ref[base] ^ K_X
                if t_ref[base+2] != expected:
                    mismatches.append(f"ModeB T[{base+2}]={t_ref[base+2]:08X} != T[{base}]^K_X={expected:08X}")
            if base+2 in t_ref and base+3 in t_ref:
                if t_ref[base+2] != t_ref[base+3]:
                    mismatches.append(f"ModeB T[{base+2}]={t_ref[base+2]:08X} != T[{base+3}]={t_ref[base+3]:08X}")

    if mismatches:
        print(f"  WARNING: {len(mismatches)} pattern mismatches!")
        for m in mismatches[:10]:
            print(f"    {m}")
    else:
        print(f"  All filled entries consistent with Mode A/B patterns ✓")

    return missing

def fill_missing_by_pattern(t_ref, missing):
    """根据 Mode A/B 模式推断缺失条目"""
    inferred = {}
    levels = []  # 迭代填充层级

    def try_fill():
        newly = {}
        for b0 in list(missing):
            if b0 in t_ref or b0 in inferred:
                continue
            k = b0 >> 2
            base = k * 4
            offset = b0 - base  # 0,1,2,3

            all_vals = {}
            for i in range(4):
                bi = base + i
                if bi in t_ref:
                    all_vals[i] = t_ref[bi]
                elif bi in inferred:
                    all_vals[i] = inferred[bi]

            if b0 < 0x80:
                # Mode A
                if offset == 0 and 3 in all_vals:
                    newly[b0] = all_vals[3]
                elif offset == 3 and 0 in all_vals:
                    newly[b0] = all_vals[0]
                elif offset == 2 and 0 in all_vals:
                    newly[b0] = all_vals[0] ^ K_X
                elif offset == 2 and 3 in all_vals:
                    newly[b0] = all_vals[3] ^ K_X
                elif offset == 0 and 2 in all_vals:
                    newly[b0] = all_vals[2] ^ K_X
                elif offset == 3 and 2 in all_vals:
                    newly[b0] = all_vals[2] ^ K_X
                # Mode A: T[4k+1] = T[4k] ^ D[k]
                if offset == 1:
                    k_mod = k % 4
                    d_val = None
                    if k_mod == 0:
                        d_val = D_TABLE[0].get(k, 0)
                    elif k_mod in D_TABLE:
                        d_val = D_TABLE[k_mod]
                    if d_val is not None and 0 in all_vals:
                        newly[b0] = all_vals[0] ^ d_val
                    elif d_val is not None and 3 in all_vals:
                        newly[b0] = all_vals[3] ^ d_val
                elif offset == 0 and 1 in all_vals and (b0>>2)%4 in D_TABLE:
                    # only if D[k] is known
                    k_mod = k % 4
                    if k_mod == 0:
                        d_val = D_TABLE[0].get(k, None)
                    else:
                        d_val = D_TABLE.get(k_mod)
                    if d_val is not None:
                        newly[b0] = all_vals[1] ^ d_val
            else:
                # Mode B
                if offset == 0 and 1 in all_vals:
                    newly[b0] = all_vals[1]
                elif offset == 1 and 0 in all_vals:
                    newly[b0] = all_vals[0]
                elif offset == 2 and 3 in all_vals:
                    newly[b0] = all_vals[3]
                elif offset == 3 and 2 in all_vals:
                    newly[b0] = all_vals[2]
                elif offset == 2 and 0 in all_vals:
                    newly[b0] = all_vals[0] ^ K_X
                elif offset == 0 and 2 in all_vals:
                    newly[b0] = all_vals[2] ^ K_X
                elif offset == 3 and 0 in all_vals:
                    newly[b0] = all_vals[0] ^ K_X
                elif offset == 0 and 3 in all_vals:
                    newly[b0] = all_vals[3] ^ K_X
                elif offset == 2 and 1 in all_vals:
                    newly[b0] = all_vals[1] ^ K_X
                elif offset == 1 and 2 in all_vals:
                    newly[b0] = all_vals[2] ^ K_X
        return newly

    # 迭代填充直到稳定
    for iteration in range(10):
        new = try_fill()
        if not new:
            break
        inferred.update(new)
        levels.append(len(new))
        missing = [b for b in missing if b not in inferred]

    print(f"\n  --- Pattern-based inference ---")
    print(f"  Iterations: {len(levels)}, filled: {sum(levels)} entries")
    for i, n in enumerate(levels):
        print(f"    Pass {i+1}: +{n} entries")

    still_missing = [b for b in range(256) if b not in t_ref and b not in inferred]
    print(f"  Remaining gaps: {len(still_missing)}/256")

    return inferred, still_missing

def dump_t_table(t_ref, inferred, missing):
    """输出完整的 T[b0] 表"""
    print(f"\n{'='*60}")
    print(f"  T[b0] TABLE (hex)")
    print(f"{'='*60}")
    full = dict(t_ref)
    full.update(inferred)

    for b0 in range(256):
        if b0 in full:
            val = full[b0]
            source = 'E' if b0 in t_ref else 'I'
            mode = 'A' if b0 < 0x80 else 'B'
            print(f"  [{b0:3d}] 0x{b0:02X} = 0x{val:08X}  ({source},{mode})")
        else:
            print(f"  [{b0:3d}] 0x{b0:02X} = ----------  (X)")

def export_t_table(t_ref, inferred):
    """导出为 Python dict 字符串"""
    full = dict(t_ref)
    full.update(inferred)
    lines = []
    for b0 in range(256):
        if b0 in full:
            lines.append(f"  0x{b0:02X}: 0x{full[b0]:08X},")
    return '\n'.join(lines)

# ============================================================
# MAIN
# ============================================================
def main():
    all_pkts = []

    # S1: correct_buf.txt
    s1_path = os.path.join(DUMP_DIR, 'correct_buf.txt')
    if os.path.exists(s1_path):
        s1 = parse_correct_buf(s1_path)
        all_pkts.extend(s1)
        print(f"S1 (correct_buf.txt): {len(s1)} pkts")

    # S3: two CSVs
    for fname, sname in [('f12_samples.csv', 'S3a'), ('f12_s3_102rec.csv', 'S3b')]:
        path = os.path.join(DUMP_DIR, fname)
        if os.path.exists(path):
            pkts = parse_old_csv(path, sname)
            all_pkts.extend(pkts)
            print(f"{sname} ({fname}): {len(pkts)} pkts")

    # S4: old format
    s4_path = os.path.join(DUMP_DIR, 'f12_20260519_181141.csv')
    if os.path.exists(s4_path):
        s4 = parse_old_csv(s4_path, 'S4')
        all_pkts.extend(s4)
        print(f"S4 (f12_20260519_181141.csv): {len(s4)} pkts")

    # S5: new format (use 221539, skip 221543 which is a duplicate)
    s5_path = os.path.join(DUMP_DIR, 'f12_20260519_221539.csv')
    if os.path.exists(s5_path):
        s5 = parse_new_csv(s5_path, 'S5')
        all_pkts.extend(s5)
        print(f"S5 (f12_20260519_221539.csv): {len(s5)} pkts")

    print(f"\nTotal raw packets: {len(all_pkts)}")

    # 过滤 plen=8
    plen8 = [p for p in all_pkts if p['plen'] == 8]
    print(f"plen=8 packets: {len(plen8)}")

    # 每个 session 计算 sk_xor_t
    sessions = defaultdict(list)
    for p in plen8:
        sessions[p['session']].append(p)

    sess_data = {}
    for sname, entries in sessions.items():
        sess_data[sname] = calc_session_skt(entries)

    print(f"\nSession counts (plen=8):")
    for sname, entries in sess_data.items():
        # 统计唯一条目 (同 b0 多次出现选最新)
        unique_b0 = {}
        for e in entries:
            unique_b0[e['b0']] = e['sk_xor_t']
        print(f"  {sname}: {len(entries)} pkts, {len(unique_b0)} unique b0")

    # 跨 session 对齐
    t_ref, offsets, ref_b0, ref_session = align_sessions(sess_data)

    print(f"\nCross-session alignment:")
    print(f"  Reference session: {ref_session}")
    print(f"  Reference b0: 0x{ref_b0:02X}")
    for sname, off in offsets.items():
        print(f"  {sname} offset: 0x{off:08X}")

    # 分析
    missing = analyze_patterns(t_ref)

    # 推断
    inferred, final_missing = fill_missing_by_pattern(t_ref, missing)

    # 最终统计
    final_filled = len(t_ref) + len(inferred)
    print(f"\n{'='*60}")
    print(f"  FINAL: {final_filled}/256 filled ({final_filled*100/256:.1f}%)")
    print(f"  Empirical: {len(t_ref)}, Inferred: {len(inferred)}, Missing: {len(final_missing)}")
    print(f"{'='*60}")

    if final_missing:
        print(f"\n  Missing b0 values ({len(final_missing)}):")
        for b0 in final_missing:
            mode = 'A' if b0 < 0x80 else 'B'
            k = b0 >> 2
            pos = b0 & 3
            print(f"    0x{b0:02X} (b0={b0:3d}) — k={k}, pos={pos}, Mode {mode}")

    # 输出完整 T 表
    # dump_t_table(t_ref, inferred, final_missing)

    # 导出供其他脚本使用
    out_path = os.path.join(DUMP_DIR, 't_table_merged.txt')
    full = dict(t_ref)
    full.update(inferred)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"# T[b0] table - {len(full)}/256 filled\n")
        f.write(f"# Empirical: {len(t_ref)}, Inferred: {len(inferred)}\n\n")
        f.write("T_TABLE = {\n")
        for b0 in sorted(full.keys()):
            source = 'E' if b0 in t_ref else 'I'
            f.write(f"  0x{b0:02X}: 0x{full[b0]:08X},  # {source}\n")
        f.write("}\n")
    print(f"\nExported to: {out_path}")

if __name__ == '__main__':
    main()
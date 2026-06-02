"""
crack_f12_algo.py — 尝试从 f12 查找表推导生成算法

已知:
- f12(1) = 0xA848F08D (seed)
- Δ(even) = 0xDD45AAB8 (constant)
- Δ(odd) varies

尝试:
1. f12 = LCG(seq)
2. f12 = xorshift(f12(seq-1))
3. f12 = hash(seq)
4. 分解为 4 个独立字节通道
"""
import struct

# f12 查找表 (seq 1-194, 投票结果)
F12 = {
    1:0xA848F08D, 2:0xCA6A79B4, 3:0x172FD30C, 4:0x0E2F6BC6,
    5:0xD36AC17E, 6:0xB1484847, 7:0x6C0DE2FF, 8:0x834939D3,
    9:0x5E0C936B, 10:0x3C2E1A52, 11:0xE16BB0EA, 12:0xF86B0820,
    13:0x252EA298, 14:0x470C2BA1, 15:0x9A498119, 16:0x9C69EB08,
    17:0x412C41B0, 18:0x230EC889, 19:0xFE4B6231, 20:0xE74BDAFB,
    21:0x3A0E7043, 22:0x582CF97A, 23:0x856953C2, 24:0x6A2D88EE,
    25:0xB7682256, 26:0xD54AAB6F, 27:0x080F01D7, 28:0x110FB91D,
    29:0xCC4A13A5, 30:0xAE689A9C, 31:0x732D3024, 32:0xA2284EBE,
    33:0x7F6DE406, 34:0x1D4F6D3F, 35:0xC00AC787, 36:0xD90A7F4D,
    37:0x044FD5F5, 38:0x666D5CCC, 39:0xBB28F674, 40:0x546C2D58,
    41:0x892987E0, 42:0xEB0B0ED9, 43:0x364EA461, 44:0x2F4E1CAB,
    45:0xF20BB613, 46:0x79C9F7F8, 47:0xA48C5D40, 48:0xA2AC3751,
    49:0x7FE99DE9, 50:0x1DCB14D0, 51:0xC08EBE68, 52:0xD98E06A2,
    53:0x04CBAC1A, 54:0x66E92523, 55:0xBBAC8F9B, 56:0x54E854B7,
    57:0x89ADFE0F, 58:0xEB8F7736, 59:0x36CADD8E, 60:0x2FCA6544,
    61:0xF28FCFFC, 62:0x90AD46C5, 63:0x4DE8EC7D, 64:0x374BCD00,
    65:0xEA0E67B8, 66:0x882CEE81, 67:0x55694439, 68:0x4C69FCF3,
    69:0x912C564B, 70:0xF30EDF72, 71:0x2E4B75CA, 72:0xC10FAEE6,
    73:0x1C4A045E, 74:0x7E688D67, 75:0xA32D27DF, 76:0xBA2D9F15,
    77:0x676835AD, 78:0x054ABC94, 79:0xD80F162C, 80:0xDE2F7C3D,
    81:0x036AD685, 82:0x61485FBC, 83:0xBC0DF504, 84:0xA50D4DCE,
    85:0x7848E776, 86:0x1A6A6E4F, 87:0xC72FC4F7, 88:0x286B1FDB,
    89:0xF52EB563, 90:0x970C3C5A, 91:0x4A4996E2, 92:0x53492E28,
    93:0x8E0C8490, 94:0xEC2E0DA9, 95:0x316BA711, 96:0xE06ED98B,
    97:0x3D2B7333, 98:0x5F09FA0A, 99:0x824C50B2, 100:0x9B4CE878,
    101:0x460942C0, 102:0x242BCBF9, 103:0xF96E6141, 104:0x162ABA6D,
    105:0xCB6F10D5, 106:0xA94D99EC, 107:0x74083354, 108:0x6D088B9E,
    109:0xB04D2126, 110:0xD26FA81F, 111:0x0F2A02A7, 112:0x090A68B6,
    113:0xD44FC20E, 114:0xB66D4B37, 115:0x6B28E18F, 116:0x72285945,
    117:0xAF6DF3FD, 118:0xCD4F7AC4, 119:0x100AD07C, 120:0xFF4E0B50,
    121:0x220BA1E8, 122:0x402928D1, 123:0x9D6C8269, 124:0x846C3AA3,
    125:0x5929901B, 126:0x3B0B1922, 127:0xE64EB39A, 128:0xCE4D5BD8,
    129:0x1308F160, 130:0x712A7859, 131:0xAC6FD2E1, 132:0xB56F6A2B,
    133:0x682AC093, 134:0x0A0849AA, 135:0xD74DE312, 136:0x3809383E,
    137:0xE54C9286, 138:0x876E1BBF, 139:0x5A2BB107, 140:0x432B09CD,
    141:0x9E6EA375, 142:0xFC4C2A4C, 143:0x210980F4, 144:0x2729EAE5,
    145:0xFA6C405D, 146:0x984EC964, 147:0x450B63DC, 148:0xCE235529,
    149:0x1366FF91, 150:0x714476A8, 151:0xAC01DC10, 152:0x4345073C,
    153:0x9E00AD84, 154:0xFC2224BD, 155:0x21678E05, 156:0x386736CF,
    157:0xE5229C77, 158:0x8700154E, 159:0x5A45BFF6, 160:0x8B40C16C,
    161:0x56056BD4, 162:0x3427E2ED, 163:0xE9624855, 164:0xF062F09F,
    165:0x2D275A27, 166:0x4F05D31E, 167:0x924079A6, 168:0x7D04A28A,
    169:0xA0410832, 170:0xC263810B, 171:0x1F262BB3, 172:0x06269379,
    173:0xDB6339C1, 174:0xB941B0F8, 175:0x64041A40, 176:0x62247051,
    177:0xBF61DAE9, 178:0x376D93A3, 179:0xEA28391B, 180:0xF32881D1,
    181:0x2E6D2B69, 182:0x4C4FA250, 183:0x910A08E8, 184:0x3DD7ABEC,
    185:0xE0920154, 186:0x82B0886D, 187:0x5FF522D5, 188:0x46F59A1F,
    189:0x9BB030A7, 190:0xF992B99E, 191:0x24D71326, 192:0x5E74325B,
    193:0x833198E3, 194:0xE11311DA,
}

EVEN_MAGIC = 0xDD45AAB8
MASK = 0xFFFFFFFF

# ====== 方法1: xorshift 变体 ======
print("=" * 60)
print("Method 1: xorshift variants")
print("=" * 60)

def xorshift32(state, a, b, c):
    state &= MASK
    state ^= (state << a) & MASK
    state ^= (state >> b)
    state ^= (state << c) & MASK
    return state

# 暴力搜索 3 个参数 (a, b, c)
# 搜索范围: a,c = 1-16, b = 1-16
found = False
for a in range(1, 17):
    for b in range(1, 17):
        for c in range(1, 17):
            ok = True
            for seq in range(1, min(20, max(F12.keys()))):
                expected = F12.get(seq + 1)
                if expected is None:
                    break
                # 尝试: f12(seq+1) = xorshift(f12(seq), a, b, c) XOR (0 if even else MAGIC)
                state = F12[seq]
                v = xorshift32(state, a, b, c)
                if seq % 2 == 0:
                    v ^= EVEN_MAGIC
                if v != expected:
                    ok = False
                    break
            if ok:
                print(f"  MATCH! xorshift({a},{b},{c}) with even XOR")
                # 验证全部
                all_ok = True
                for seq in range(1, max(F12.keys())):
                    if seq + 1 not in F12:
                        break
                    state = F12[seq]
                    v = xorshift32(state, a, b, c)
                    if seq % 2 == 0:
                        v ^= EVEN_MAGIC
                    if v != F12[seq + 1]:
                        all_ok = False
                        print(f"    FAIL at seq {seq}")
                        break
                if all_ok:
                    print(f"    PERFECT MATCH for all {len(F12)} entries!")
                    found = True

if not found:
    # 尝试不加 even XOR
    for a in range(1, 17):
        for b in range(1, 17):
            for c in range(1, 17):
                ok = True
                for seq in range(1, min(10, max(F12.keys()))):
                    expected = F12.get(seq + 1)
                    if expected is None:
                        break
                    v = xorshift32(F12[seq], a, b, c)
                    if v != expected:
                        ok = False
                        break
                if ok:
                    print(f"  MATCH (no even XOR)! xorshift({a},{b},{c})")

# ====== 方法2: f12(seq) = MUL + SHIFT hash ======
print("\n" + "=" * 60)
print("Method 2: integer hash f12 = hash(seq)")
print("=" * 60)

# 尝试各种整数哈希
for C in [0x9E3779B9, 0x6C078965, 0x01000193, 0x27BB2EE6, 0x811C9DC5]:
    for shift in range(0, 32, 4):
        # h = ((seq * C) >> shift) ^ something
        ok = True
        for seq in range(1, min(20, max(F12.keys()) + 1)):
            if seq not in F12:
                continue
            h = ((seq * C) & MASK) >> shift
            if h != F12[seq]:
                ok = False
                break
        if ok:
            print(f"  MATCH! ((seq * 0x{C:08X}) >> {shift})")

# ====== 方法3: 分离偶数/奇数子序列 ======
print("\n" + "=" * 60)
print("Method 3: Separate even/odd subsequences")
print("=" * 60)

# 偶数 seq 的 f12
even_seq = [(s, F12[s]) for s in sorted(F12.keys()) if s % 2 == 0]
odd_seq = [(s, F12[s]) for s in sorted(F12.keys()) if s % 2 == 1]

print(f"  Even subsequence ({len(even_seq)} entries):")
for i, (s, v) in enumerate(even_seq[:10]):
    print(f"    E[{i}] = f12({s}) = 0x{v:08X}")

# 偶数子序列: E[i] = F12(2*(i+1))
# E[0]=F12(2)=0xCA6A79B4, E[1]=F12(4)=0x0E2F6BC6, ...
# 检查 E[i+1] XOR E[i] 是否有规律
even_diffs = []
for i in range(1, len(even_seq)):
    d = even_seq[i][1] ^ even_seq[i-1][1]
    even_diffs.append(d)
    if i <= 10:
        print(f"    E[{i}] XOR E[{i-1}] = 0x{d:08X}")

# 检查偶数子序列差分是否周期
print(f"\n  Even subsequence XOR diff period check:")
from collections import Counter
even_diff_counter = Counter(hex(d) for d in even_diffs)
print(f"    Unique diffs: {len(even_diff_counter)}")
for val, cnt in even_diff_counter.most_common(5):
    print(f"    {val}: {cnt} times")

# ====== 方法4: f12 = LFSR state = f12(seq-2) XOR step ======
print("\n" + "=" * 60)
print("Method 4: 2-step recurrence f12(seq+2) = f12(seq) XOR step(seq)")
print("=" * 60)

# 已知 2-step XOR: f12(seq+2) = f12(seq) XOR step_2(seq)
step2 = {}
for seq in range(1, max(F12.keys()) - 1):
    if seq in F12 and seq + 2 in F12:
        step2[seq] = F12[seq] ^ F12[seq + 2]

# 按 seq mod 4 分类
by_mod4 = {}
for mod in range(4):
    vals = [(s, step2[s]) for s in sorted(step2.keys()) if s % 4 == mod]
    by_mod4[mod] = vals
    unique_vals = set(v for _, v in vals)
    if len(unique_vals) <= 3:
        print(f"  seq mod 4 = {mod}: {len(unique_vals)} unique: {[f'0x{v:08X}' for v in sorted(unique_vals)]}")
    else:
        print(f"  seq mod 4 = {mod}: {len(unique_vals)} unique values")
        # 检查是否有周期
        val_list = [v for _, v in vals]
        for period in range(1, min(33, len(val_list) // 2 + 1)):
            periodic = True
            for i in range(period, len(val_list)):
                if val_list[i] != val_list[i % period]:
                    periodic = False
                    break
            if periodic:
                print(f"    Period = {period}!")
                for j in range(period):
                    print(f"      [{j}] = 0x{val_list[j]:08X}")
                break

# ====== 方法5: 分字节分析 ======
print("\n" + "=" * 60)
print("Method 5: Per-byte analysis")
print("=" * 60)

for byte_idx in range(4):
    vals = [(s, (F12[s] >> (byte_idx * 8)) & 0xFF) for s in sorted(F12.keys())]
    # 差分
    diffs = [(vals[i][0], vals[i][1] ^ vals[i-1][1]) for i in range(1, len(vals))]
    unique_diffs = set(d for _, d in diffs)
    print(f"\n  Byte {byte_idx}: {len(unique_diffs)} unique diffs")
    if len(unique_diffs) <= 8:
        print(f"    Values: {[f'0x{d:02X}' for d in sorted(unique_diffs)]}")
        # 检查周期
        diff_list = [d for _, d in diffs]
        for period in range(1, min(33, len(diff_list) // 2 + 1)):
            periodic = True
            for i in range(period, len(diff_list)):
                if diff_list[i] != diff_list[i % period]:
                    periodic = False
                    break
            if periodic:
                print(f"    Period = {period}!")
                print(f"    Pattern: {[f'0x{diff_list[j]:02X}' for j in range(period)]}")
                break

# ====== 方法6: 纯暴力 - f12(seq) = T[seq & mask] XOR ROR(seq, n) ======
print("\n" + "=" * 60)
print("Method 6: Table + rotation f12 = T[seq & 0xFF] XOR ROR(seq*const, n)")
print("=" * 60)

# 如果 f12 只取决于低 8 位, 那么同 mod 256 的 f12 应该相同
f12_by_mod256 = {}
for s, v in F12.items():
    m = s % 256
    if m not in f12_by_mod256:
        f12_by_mod256[m] = set()
    f12_by_mod256[m].add(v)

consistent_mod256 = sum(1 for v in f12_by_mod256.values() if len(v) == 1)
print(f"  f12 consistent per seq%256: {consistent_mod256}/{len(f12_by_mod256)}")
# (注意: 我们的表只到 194, 所以 seq%256 每个值最多出现一次)

# ====== 方法7: 累积 XOR 分析 ======
print("\n" + "=" * 60)
print("Method 7: Cumulative XOR from seed")
print("=" * 60)

# f12(seq) = seed XOR cumulative_Δ(1..seq-1)
# seed = 0xA848F08D
# cumulative_Δ(seq) = Δ(1) XOR Δ(2) XOR ... XOR Δ(seq-1)

seed = F12[1]
cum = 0
for seq in range(1, max(F12.keys())):
    if seq in F12 and seq + 1 in F12:
        delta = F12[seq] ^ F12[seq + 1]
        cum ^= delta
        reconstructed = seed ^ cum
        if reconstructed != F12[seq + 1]:
            print(f"  BUG at seq {seq + 1}")
            break
        if seq <= 5:
            print(f"  cum_Δ(1..{seq}) = 0x{cum:08X}  f12({seq+1}) = seed ^ cum = 0x{reconstructed:08X}")

# 累积 Δ 本身是否有规律?
print("\n  Cumulative Δ sequence:")
cum = 0
cum_list = [0]  # cum_Δ(0) = 0
for seq in range(1, max(F12.keys())):
    if seq in F12 and seq + 1 in F12:
        delta = F12[seq] ^ F12[seq + 1]
        cum ^= delta
        cum_list.append(cum)

# 检查 cum_list[i] XOR cum_list[i-1] = Δ(i)
# 检查 cum_list 是否有周期
for period in [4, 8, 16, 32, 64]:
    periodic = True
    for i in range(period, len(cum_list)):
        if cum_list[i] != cum_list[i % period]:
            periodic = False
            break
    if periodic:
        print(f"  cum_Δ has period {period}!")
        break

# ====== 方法8: 最简暴力 — 直接搜索 f12(seq) = a*seq^2 + b*seq + c mod 2^32 ======
print("\n" + "=" * 60)
print("Method 8: Polynomial f12(seq) mod 2^32")
print("=" * 60)

# 用前 3 个值解方程: f12 = a*s^2 + b*s + c
# f12(1) = a + b + c = 0xA848F08D
# f12(2) = 4a + 2b + c = 0xCA6A79B4
# f12(3) = 9a + 3b + c = 0x172FD30C

v1 = 0xA848F08D
v2 = 0xCA6A79B4
v3 = 0x172FD30C

# 3a + b = v2 - v1
# 5a + b = v3 - v2
# 2a = (v3 - v2) - (v2 - v1) = v3 - 2*v2 + v1
M = MASK
two_a = (v3 - 2 * v2 + v1) & M
# Need modular inverse of 2 mod 2^32 — 2 is not invertible mod 2^32!
# Try: a = two_a / 2 (only works if two_a is even)
if two_a % 2 == 0:
    a = (two_a // 2) & M
    b = (v2 - v1 - 3 * a) & M
    c = (v1 - a - b) & M
    print(f"  Quadratic: a=0x{a:08X} b=0x{b:08X} c=0x{c:08X}")
    ok = True
    for seq in range(1, min(20, max(F12.keys()) + 1)):
        if seq not in F12:
            continue
        expected = (a * seq * seq + b * seq + c) & M
        if expected != F12[seq]:
            ok = False
            print(f"    FAIL at seq={seq}: expected 0x{expected:08X} got 0x{F12[seq]:08X}")
            break
    if ok:
        print(f"    Matches first 20! Checking all...")
        for seq in range(1, max(F12.keys()) + 1):
            if seq not in F12:
                continue
            expected = (a * seq * seq + b * seq + c) & M
            if expected != F12[seq]:
                print(f"    FAIL at seq={seq}")
                ok = False
                break
        if ok:
            print(f"    PERFECT! f12(seq) = 0x{a:08X}*seq^2 + 0x{b:08X}*seq + 0x{c:08X} mod 2^32")
else:
    print(f"  two_a = 0x{two_a:08X} is odd, can't divide by 2 mod 2^32")
    # Try linear: f12 = m*seq + b
    # m = (v2 - v1) / (2-1) = v2 - v1
    m = (v2 - v1) & M
    b = (v1 - m) & M
    print(f"  Linear: m=0x{m:08X} b=0x{b:08X}")
    if ((m * 3 + b) & M) == v3:
        print(f"    Matches first 3! But unlikely to match all...")

# ====== 方法9: 直接暴力乘法哈希 ======
print("\n" + "=" * 60)
print("Method 9: MurmurHash3-style finalizer")
print("=" * 60)

def murmur3_fina(v):
    v &= MASK
    v ^= v >> 16
    v = (v * 0x85EBCA6B) & MASK
    v ^= v >> 13
    v = (v * 0xC2B2AE35) & MASK
    v ^= v >> 16
    return v

# 检查 f12(seq) = murmur3_fina(seq)
ok = True
for seq in range(1, min(10, max(F12.keys()) + 1)):
    if seq not in F12:
        continue
    if murmur3_fina(seq) != F12[seq]:
        ok = False
        break
if ok:
    print(f"  MATCH! f12(seq) = murmur3_fina(seq)")
else:
    print(f"  No match")

# 尝试各种常量组合
import itertools
consts = [0x85EBCA6B, 0xC2B2AE35, 0x9E3779B9, 0x6C078965, 0x01000193,
          0x27BB2EE6, 0x811C9DC5, 0x45D9F3B, 0x1B873593, 0xCC9E2D51]
for c1 in consts:
    for s1 in [13, 16, 17]:
        h = seq
        h ^= h >> s1
        h = (h * c1) & MASK
        if F12.get(1) == h:
            print(f"  Partial match with c1=0x{c1:08X} s1={s1}")

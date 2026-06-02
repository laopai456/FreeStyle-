"""
verify_level_period.py — 验证 LEVEL 周期=8 预测, 生成完整算法
"""
M = 0xFFFFFFFF

SEED = 0xA848F08D
EVEN_MAGIC = 0xDD45AAB8
BASE_G = 0x62228939

# 已知 6 个 LEVEL 值
L_known = {
    1: 0x7B2231F3,
    2: 0x8D665215,
    3: 0x6402E328,
    4: 0xB327F7A3,
    5: 0x1881A844,
    6: 0x4A21617B,
}

# d5 = 0xA4E4AAD9 (5th XOR diff is constant)
D5 = 0xA4E4AAD9

# 从 d5 向下递推预测 L[7], L[8]
# d4 cycles with period 2
d4 = [0x63A399B7, 0xC747336E]
# 扩展 d4
for i in range(2, 20):
    d4.append(d4[-1] ^ D5)

# d3[i+1] = d3[i] ^ d4[i]
d3 = [0x2161776D, 0x42C2EEDA, 0x8585DDB4]
for i in range(3, 20):
    d3.append(d3[-1] ^ d4[i-1])

# d2[i+1] = d2[i] ^ d3[i]
d2 = [0x1F20D2DB, 0x3E41A5B6, 0x7C834B6C, 0xF90696D8]
for i in range(4, 20):
    d2.append(d2[-1] ^ d3[i-1])

# d1[i+1] = d1[i] ^ d2[i]
d1 = [0xF64463E6, 0xE964B13D, 0xD725148B, 0xABA65FE7, 0x52A0C93F]
for i in range(5, 20):
    d1.append(d1[-1] ^ d2[i-1])

# L[k+1] = L[k] ^ d1[k]
L = dict(L_known)
for k in range(6, 16):
    L[k+1] = (L[k] ^ d1[k-1]) & M

print("=" * 60)
print("Predicted LEVEL values (period-8)")
print("=" * 60)
for k in range(1, 17):
    tag = "KNOWN" if k <= 6 else "PREDICTED"
    print(f"  L[{k:2d}] = 0x{L[k]:08X}  {tag}")

# 验证周期
print(f"\n  L[1] = 0x{L[1]:08X}")
print(f"  L[9] = 0x{L[9]:08X}  {'= L[1] ✓' if L[9] == L[1] else '≠ L[1] ✗'}")
print(f"  L[2] = 0x{L[2]:08X}")
print(f"  L[10] = 0x{L[10]:08X}  {'= L[2] ✓' if L[10] == L[2] else '≠ L[2] ✗'}")

# 构建 LEVEL 数组 (0-indexed for convenience)
LEVEL = [0]  # LEVEL[0] = 0
for k in range(1, 9):
    LEVEL.append(L[k])

print(f"\n  LEVEL array (period 8):")
for k in range(9):
    print(f"    LEVEL[{k}] = 0x{LEVEL[k]:08X}")

# ====== 完整算法验证 ======
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

EXCEPTIONS = {
    23: 0xE9E0C8D2,
    74: 0xE90ABFCC,
    89: 0xEA2EC073,
    92: 0xCEFF2A3D,
}

def ctz(n):
    if n == 0: return 32
    c = 0
    while (n & 1) == 0:
        c += 1
        n >>= 1
    return c

def get_level(k):
    """Get LEVEL[k] with period 8"""
    if k == 0: return 0
    return LEVEL[((k - 1) % 8) + 1]

def compute_g(n):
    if n in EXCEPTIONS:
        return (BASE_G ^ EXCEPTIONS[n]) & M
    return (BASE_G ^ get_level(ctz(n))) & M

def compute_delta(s):
    if s % 2 == 0:
        return EVEN_MAGIC
    else:
        return compute_g((s + 1) // 2)

# 验证全部 194 个条目
print("\n" + "=" * 60)
print("Verification with period-8 LEVEL")
print("=" * 60)

state = SEED
errors = 0
for seq in range(1, max(F12.keys()) + 1):
    if seq not in F12:
        continue
    if state != F12[seq]:
        errors += 1
        print(f"  FAIL at seq={seq}: got 0x{state:08X} expected 0x{F12[seq]:08X}")
    if seq < max(F12.keys()):
        state = (state ^ compute_delta(seq)) & M

if errors == 0:
    print(f"  PERFECT MATCH for all {len(F12)} entries!")
else:
    print(f"  {errors} errors")

# ====== 预测 seq > 194 ======
print("\n" + "=" * 60)
print("Predicted f12(seq) for seq 195-250")
print("=" * 60)

state = F12[194]
for seq in range(194, 251):
    state = (state ^ compute_delta(seq)) & M
    if seq >= 195:
        print(f"  f12({seq:3d}) = 0x{state:08X}")

# ====== 生成 JS 代码 ======
print("\n" + "=" * 60)
print("JavaScript f12 algorithm (unlimited seq)")
print("=" * 60)

js_code = """// f12(seq) computation algorithm
// XOR binary counter with period-8 LEVEL values
var F12_SEED = 0xA848F08D;
var F12_EVEN_MAGIC = 0xDD45AAB8;
var F12_BASE_G = 0x62228939;
var F12_LEVEL = [0x00000000, 0x7B2231F3, 0x8D665215, 0x6402E328,
                 0xB327F7A3, 0x1881A844, 0x4A21617B, 0x07A17A9F, 0x7460C4CD];
var F12_EXCEPTIONS = {23: 0xE9E0C8D2, 74: 0xE90ABFCC, 89: 0xEA2EC073, 92: 0xCEFF2A3D};

function f12Ctz(n) {
    if (n === 0) return 32;
    var c = 0;
    while ((n & 1) === 0) { c++; n >>>= 1; }
    return c;
}

function f12GetLevel(k) {
    if (k === 0) return 0;
    return F12_LEVEL[((k - 1) % 8) + 1];
}

function f12ComputeG(n) {
    var h = F12_EXCEPTIONS[n];
    if (h !== undefined) return (F12_BASE_G ^ h) >>> 0;
    return (F12_BASE_G ^ f12GetLevel(f12Ctz(n))) >>> 0;
}

// Incremental: f12(seq+1) from f12(seq)
function f12Next(currentF12, seq) {
    if (seq % 2 === 0) {
        return (currentF12 ^ F12_EVEN_MAGIC) >>> 0;
    } else {
        return (currentF12 ^ f12ComputeG((seq + 1) >>> 1)) >>> 0;
    }
}

// Full: f12(seq) from scratch (slower)
function f12Compute(seq) {
    var state = F12_SEED;
    for (var s = 1; s < seq; s++) {
        if (s % 2 === 0) {
            state = (state ^ F12_EVEN_MAGIC) >>> 0;
        } else {
            state = (state ^ f12ComputeG((s + 1) >>> 1)) >>> 0;
        }
    }
    return state >>> 0;
}
"""
print(js_code)

# 保存到文件
with open("f12_algorithm.js", "w", encoding="utf-8") as f:
    f.write(js_code)
print("(saved to f12_algorithm.js)")

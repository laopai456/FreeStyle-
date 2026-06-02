// f12(seq) computation algorithm
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

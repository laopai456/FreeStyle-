# hook_manager.py — 多装备位 Frida Hook 管理器
# v7: 回归 Memory.scanSync（唯一验证过特效能生效的方案）
#     不在 REPLACE 时自动扫描，改为手动触发避免卡顿
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

def create_js(replace_map, effect_map=None, collect_mode=True, enable_effect=True):
    map_json = json.dumps(replace_map)
    effect_json = json.dumps(effect_map or {})
    collect = "true" if collect_mode else "false"
    effect_flag = "true" if enable_effect else "false"

    return r"""
'use strict';

var REPLACE_MAP = """ + map_json + """;
var EFFECT_MAP = """ + effect_json + """;
var COLLECT_MODE = """ + collect + """;
var ENABLE_EFFECT = """ + effect_flag + """;

var collected = {};
var collectIndex = 0;
var patchCount = 0;
var seenCodes = {};  // 去重：记录当前批次已收集的 ItemCode
var collectedCCodes = [];  // 收集 c%d.xml 的角色码
var currentCharCcode = null;  // 当前角色 c-code；变化即切换角色，自动隔离上一角色的收集数据避免污染
var consecutiveMiss = 0;  // 异常检测：连续 sprintf MISS 计数
var CONSECUTIVE_MISS_THRESHOLD = 15;  // 超过此数报警

// 预计算
var SRC_HEX_MAP = {};
var DST_HEX_MAP = {};
var SRC_INT_MAP = {};
var DST_INT_MAP = {};

for (var src in REPLACE_MAP) {
    var dst = REPLACE_MAP[src];
    var srcVal = parseInt(src);
    var dstVal = parseInt(dst);
    if (!isNaN(srcVal)) {
        SRC_HEX_MAP[src] = intToLeHex(srcVal);
        SRC_INT_MAP[src] = srcVal;
    }
    if (!isNaN(dstVal)) {
        DST_HEX_MAP[dst] = intToLeHex(dstVal);
        DST_INT_MAP[dst] = dstVal;
    }
}

// 快速预过滤
var CUSTOMIZE_PREFIX = 0x74737563;

function fastCheckCustomize(ptr) {
    try { return ptr.readU32() === CUSTOMIZE_PREFIX; } catch(e) { return false; }
}

function readAscii(buf, maxLen) {
    try { return buf.readUtf8String(maxLen); } catch(e) {
        var s = '';
        for (var i = 0; i < maxLen; i++) {
            var c = buf.add(i).readU8();
            if (c === 0) break;
            s += String.fromCharCode(c);
        }
        return s;
    }
}

function replaceStr(buf, src, dst) {
    var content = readAscii(buf, 120);
    var idx = content.indexOf(src);
    if (idx < 0) return false;
    var replaced = content.substring(0, idx) + dst + content.substring(idx + src.length);
    for (var i = 0; i < replaced.length; i++) buf.add(i).writeU8(replaced.charCodeAt(i));
    buf.add(replaced.length).writeU8(0);
    return true;
}

function intToLeHex(val) {
    var buf = Memory.alloc(4);
    buf.writeU32(val);
    var hex = '';
    for (var i = 0; i < 4; i++) hex += ('0' + buf.add(i).readU8().toString(16)).slice(-2) + ' ';
    return hex.trim();
}

function autoReplaceEbp(ebp, srcCode, dstCode) {
    var count = 0;
    for (var off = -0x300; off <= 0x300; off += 4) {
        try {
            if (ebp.add(off).readU32() === srcCode) {
                ebp.add(off).writeU32(dstCode);
                count++;
            }
        } catch(e){}
    }
    return count;
}

// ===== DWORD 全堆扫描（仅替换属性表条目，避免破坏商城数据）=====
// DWORD → little-endian hex pattern（Memory.scanSync 用）
function dwordToPattern(val) {
    var b0 = ('0' + (val & 0xFF).toString(16)).slice(-2);
    var b1 = ('0' + ((val >> 8) & 0xFF).toString(16)).slice(-2);
    var b2 = ('0' + ((val >> 16) & 0xFF).toString(16)).slice(-2);
    var b3 = ('0' + ((val >> 24) & 0xFF).toString(16)).slice(-2);
    return b0 + ' ' + b1 + ' ' + b2 + ' ' + b3;
}

function dwordScan() {
    // dwordScan 需要扫描所有区域（包括小区域），不用 _cachedRanges 的 64KB 过滤
    var ranges = Process.enumerateRanges('rw-');
    // 过滤掉超大区域
    var scanRanges = [];
    for (var i = 0; i < ranges.length; i++) {
        if (ranges[i].size <= 200*1024*1024) scanRanges.push(ranges[i]);
    }

    var totalReplaced = 0;
    var totalEffects = 0;
    var t0 = Date.now();

    // 诊断：dump EFFECT_MAP 内容
    var effectDump = [];
    for (var k in EFFECT_MAP) effectDump.push(k + '=' + EFFECT_MAP[k]);
    send({t:'dword_scan_debug', effectMap: effectDump.join(', '), ranges: scanRanges.length});

    // ===== 第一步：CModule 快速替换 SRC→DST =====
    // CModule 暴力替换（无 flag 检查），速度快 ~4s
    // 返回逐映射替换计数（counts 数组）
    if (_nativeScanFn) {
        var mapCount = 0;
        for (var src in REPLACE_MAP) mapCount++;
        var srcArr = Memory.alloc(mapCount * 4);
        var dstArr = Memory.alloc(mapCount * 4);
        var countsArr = Memory.alloc(mapCount * 4);  // 逐映射替换计数
        var idx = 0;
        for (var src in REPLACE_MAP) {
            srcArr.add(idx * 4).writeU32(parseInt(src));
            dstArr.add(idx * 4).writeU32(parseInt(REPLACE_MAP[src]));
            countsArr.add(idx * 4).writeU32(0);
            idx++;
        }
        for (var i = 0; i < scanRanges.length; i++) {
            var r = scanRanges[i];
            var dwordCount = (r.size / 4) | 0;
            if (dwordCount < 1) continue;
            try {
                totalReplaced += _nativeScanFn(r.base, dwordCount, srcArr, dstArr, mapCount, countsArr);
            } catch(e) {
                var CHUNK = 16 * 1024 * 1024;
                var remaining = r.size;
                var off = 0;
                while (remaining >= 4) {
                    var chunkDwords = Math.min((remaining / 4) | 0, CHUNK / 4);
                    try { totalReplaced += _nativeScanFn(r.base.add(off), chunkDwords, srcArr, dstArr, mapCount, countsArr); } catch(e2) {}
                    off += chunkDwords * 4;
                    remaining -= chunkDwords * 4;
                }
            }
        }
        // 读取逐映射计数，只发统计摘要（max/min/avg），不发完整列表
        var maxCount = 0, minCount = 0x7FFFFFFF, nonzeroCount = 0;
        var maxSrc = '', maxDst = '';
        var srcIdx = 0;
        for (var src in REPLACE_MAP) {
            var c = countsArr.add(srcIdx * 4).readU32();
            if (c > 0) {
                nonzeroCount++;
                if (c > maxCount) { maxCount = c; maxSrc = src; maxDst = REPLACE_MAP[src]; }
                if (c < minCount) minCount = c;
            }
            srcIdx++;
        }
        if (nonzeroCount === 0) minCount = 0;
        send({t:'dword_scan_per_map', nonzero: nonzeroCount, total_maps: mapCount,
              max: maxCount, max_src: maxSrc, max_dst: maxDst, min: minCount});
    } else {
        // JS 降级：scanSync 逐 SRC 替换
        for (var src in REPLACE_MAP) {
            var srcVal = parseInt(src);
            var dstVal = parseInt(REPLACE_MAP[src]);
            var pattern = dwordToPattern(srcVal);
            for (var i = 0; i < scanRanges.length; i++) {
                var r = scanRanges[i];
                try {
                    var matches = Memory.scanSync(r.base, r.size, pattern);
                    for (var j = 0; j < matches.length; j++) {
                        try { matches[j].address.writeU32(dstVal); totalReplaced++; } catch(e) {}
                    }
                } catch(e) {}
            }
        }
    }

    var t1 = Date.now();

    // ===== 第二步：scanSync 精确写特效 =====
    // 扫描 DST 值，检查 flag，写特效（知识库 8.6.3 两步法）
    // 关键：只有 +0x0C == 0x00010000 时才写（说明下一条是特效条目，可安全覆盖）
    // 如果 +0x0C != 0x00010000，说明下一条是其他属性，覆盖会破坏数据
    for (var src in REPLACE_MAP) {
        var dstVal = parseInt(REPLACE_MAP[src]);
        var effectId = EFFECT_MAP[dstVal] ? parseInt(EFFECT_MAP[dstVal]) : 0;
        if (effectId <= 0) continue;

        var pattern = dwordToPattern(dstVal);
        for (var i = 0; i < scanRanges.length; i++) {
            var r = scanRanges[i];
            try {
                var matches = Memory.scanSync(r.base, r.size, pattern);
                for (var j = 0; j < matches.length; j++) {
                    try {
                        if (matches[j].address.add(4).readU32() === 0x00010000) {
                            // 读取 +0x08 和 +0x0C 的原始值
                            var curVal08 = 0, curVal0C = 0;
                            try { curVal08 = matches[j].address.add(8).readU32(); } catch(e) {}
                            try { curVal0C = matches[j].address.add(12).readU32(); } catch(e) {}

                            if (curVal0C === 0x00010000) {
                                // +0x0C == 0x00010000 → 下一条是特效条目，可安全写
                                matches[j].address.add(8).writeU32(effectId);
                                totalEffects++;
                                // 只发前5条日志
                                if (totalEffects <= 5) {
                                    send({t:'effect_struct', addr: matches[j].address.toString(), dst: dstVal,
                                          val08: curVal08, val0C: curVal0C, hasEffectSlot: true});
                                }
                            }
                            // else: +0x0C != 0x00010000 → 下一条是其他属性，跳过
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }
    }

    var elapsed = Date.now() - t0;
    var step1ms = t1 - t0;
    var step2ms = Date.now() - t1;
    send({t:'dword_scan_done', total: totalReplaced, effects: totalEffects, ms: elapsed, step1ms: step1ms, step2ms: step2ms, method: 'cmodule+scanSync', ranges: scanRanges.length, effectMap: effectDump.join(', ')});
    return totalReplaced;
}

// ===== 练习场暴力 DWORD 扫描（无 flag 检查）=====
// 练习场 ItemCode 在堆对象里，Frida readU32 读 flag 不准 → flag 检查版 0 替换
// 必须用暴力扫描替换所有实例
var _cachedRanges = null;
var _precommitted = false;
var MIN_SCAN_SIZE = 64 * 1024;  // 跳过 <64KB 小区域
var MAX_SCAN_SIZE = 200 * 1024 * 1024;

// VirtualQuery 过滤：只扫描 MEM_PRIVATE 页（堆分配），跳过 MEM_MAPPED/MEM_IMAGE
var _virtualQuery = null;
var _mbiBuf = null;
var MEM_COMMIT = 0x1000;
var MEM_PRIVATE = 0x20000;
try {
    _virtualQuery = new NativeFunction(
        Module.getExportByName('kernel32.dll', 'VirtualQuery'),
        'uint', ['pointer', 'pointer', 'uint']
    );
    _mbiBuf = Memory.alloc(48); // MEMORY_BASIC_INFORMATION (x64)
} catch(e) {
    send({t:'vq_error', msg: e.message});
}

function isPrivateRW(base) {
    if (!_virtualQuery || !_mbiBuf) return true; // 降级：无法判断则保留
    try {
        var ret = _virtualQuery(base, _mbiBuf, 48);
        if (ret === 0) return false;
        // MEMORY_BASIC_INFORMATION x64 layout:
        // +0  BaseAddress (8), +8 AllocationBase (8), +16 AllocationProtect (4)
        // +20 PartitionId (2), +24 RegionSize (8), +32 State (4), +36 Protect (4), +40 Type (4)
        var state = _mbiBuf.add(32).readU32();
        var type = _mbiBuf.add(40).readU32();
        return state === MEM_COMMIT && type === MEM_PRIVATE;
    } catch(e) { return true; }
}

// CModule 原生扫描器：单遍正向替换（src→dst）
var _nativeScanner = null;
var _nativeScanFn = null;
// CModule 特效扫描器：带 flag 检查 + 特效写入
var _nativeEffectScanner = null;
var _nativeEffectScanFn = null;

try {
    _nativeScanner = new CModule(
        'int chunk_scan(unsigned int *base, unsigned int dword_count,' +
        '               unsigned int *srcs, unsigned int *dsts, int map_count, unsigned int *counts) {' +
        '  unsigned int *ptr = base;' +
        '  unsigned int *end = base + dword_count;' +
        '  int total = 0;' +
        '  int i;' +
        '  while (ptr < end) {' +
        '    unsigned int val = *ptr;' +
        '    for (i = 0; i < map_count; i++) {' +
        '      if (val == srcs[i]) { *ptr = dsts[i]; counts[i]++; total++; break; }' +
        '    }' +
        '    ptr++;' +
        '  }' +
        '  return total;' +
        '}'
    );
    _nativeScanFn = new NativeFunction(_nativeScanner.chunk_scan, 'int',
        ['pointer', 'uint', 'pointer', 'pointer', 'int', 'pointer']);

    // 特效扫描器：检查 +0x04 flag，替换 ItemCode + 写特效值
    // 返回值：高16位=替换数，低16位=特效数
    _nativeEffectScanner = new CModule(
        'int effect_scan(unsigned int *base, unsigned int dword_count,' +
        '               unsigned int *srcs, unsigned int *dsts, int *effects, int map_count) {' +
        '  unsigned int *ptr = base;' +
        '  unsigned int *end = base + dword_count;' +
        '  int replaced = 0;' +
        '  int effects_written = 0;' +
        '  int i;' +
        '  while (ptr + 3 < end) {' +
        '    unsigned int val = *ptr;' +
        '    for (i = 0; i < map_count; i++) {' +
        '      if (val == srcs[i]) {' +
        // 检查 +0x04 flag == 0x00010000（属性表条目标志）
        '        if (ptr[1] == 0x00010000) {' +
        '          *ptr = dsts[i];' +
        '          replaced++;' +
        // 写特效：+0x08 = effectId, +0x0C = 0x00010000
        '          if (effects[i] > 0) {' +
        '            ptr[2] = (unsigned int)effects[i];' +
        '            ptr[3] = 0x00010000;' +
        '            effects_written++;' +
        '          }' +
        '        }' +
        '        break;' +
        '      }' +
        '    }' +
        '    ptr++;' +
        '  }' +
        '  return (replaced << 16) | (effects_written & 0xFFFF);' +
        '}'
    );
    _nativeEffectScanFn = new NativeFunction(_nativeEffectScanner.effect_scan, 'int',
        ['pointer', 'uint', 'pointer', 'pointer', 'pointer', 'int']);

    send({t:'cmodule_ok'});
} catch(e) {
    send({t:'cmodule_error', msg: e.message});
}

// 枚举并缓存 MEM_PRIVATE 区域
function buildCachedRanges() {
    if (_cachedRanges) return;
    try {
        var allRanges = Process.enumerateRanges('rw-');
    } catch(e) { return; }
    _cachedRanges = [];
    var totalAll = 0;
    var totalPrivate = 0;
    for (var k = 0; k < allRanges.length; k++) {
        var ar = allRanges[k];
        if (ar.size < MIN_SCAN_SIZE || ar.size > MAX_SCAN_SIZE) continue;
        totalAll += ar.size;
        if (isPrivateRW(ar.base)) {
            _cachedRanges.push(ar);
            totalPrivate += ar.size;
        }
    }
    send({t:'ranges_filtered', total_ranges: allRanges.length, private_ranges: _cachedRanges.length,
          total_bytes: totalAll, private_bytes: totalPrivate});
}

// 预提交页面：提前触发 page fault，后续扫描不再等 OS 调页
// 连接后由 Python 端调用 precommitPages() 触发
function precommitPages() {
    if (_precommitted) return;
    buildCachedRanges();
    if (!_cachedRanges) return;
    var t0 = Date.now();
    var totalBytes = 0;
    var CHUNK = 16 * 1024 * 1024;
    for (var i = 0; i < _cachedRanges.length; i++) {
        try {
            // 完整预提交整个区域，不只是前 16MB
            var remaining = _cachedRanges[i].size;
            var off = 0;
            while (remaining > 0) {
                var len = Math.min(remaining, CHUNK);
                _cachedRanges[i].base.add(off).readByteArray(len);
                off += len;
                remaining -= len;
            }
            totalBytes += _cachedRanges[i].size;
        } catch(e) {}
    }
    _precommitted = true;
    send({t:'precommit_done', ms: Date.now() - t0, bytes: totalBytes, ranges: _cachedRanges.length});
}

function bruteDwordScan() {
    send({t:'brute_scan_start', mapSize: Object.keys(REPLACE_MAP).length});

    // ===== 关键：先反向扫描恢复源值，再正向扫描 =====
    // 原因：第一次扫描后源值被替换成目标值，第二次扫描找不到源值
    // 解决：扫描前先把所有目标值改回源值，确保源值存在

    // 每次都重新枚举区域！游戏会分配新堆内存
    try {
        var allRanges = Process.enumerateRanges('rw-');
    } catch(e) {
        send({t:'brute_scan_error', step: 'enumerateRanges', msg: e.message});
        return 0;
    }
    _cachedRanges = [];
    var skipped = 0;
    var totalAll = 0;
    var totalPrivate = 0;
    for (var k = 0; k < allRanges.length; k++) {
        var ar = allRanges[k];
        if (ar.size < MIN_SCAN_SIZE || ar.size > MAX_SCAN_SIZE) {
            skipped++;
            continue;
        }
        totalAll += ar.size;
        if (isPrivateRW(ar.base)) {
            _cachedRanges.push(ar);
            totalPrivate += ar.size;
        } else {
            skipped++;
        }
    }
    send({t:'brute_scan_cache', total: allRanges.length, kept: _cachedRanges.length, skipped: skipped,
          total_bytes: totalAll, private_bytes: totalPrivate});

    // 立即预提交新区域的页面（游戏可能分配了新堆内存）
    var precommitMs = 0;
    if (!_precommitted) {
        var tPre = Date.now();
        var CHUNK = 16 * 1024 * 1024;
        for (var i = 0; i < _cachedRanges.length; i++) {
            try {
                var remaining = _cachedRanges[i].size;
                var off = 0;
                while (remaining > 0) {
                    var len = Math.min(remaining, CHUNK);
                    _cachedRanges[i].base.add(off).readByteArray(len);
                    off += len;
                    remaining -= len;
                }
            } catch(e) {}
        }
        _precommitted = true;
        precommitMs = Date.now() - tPre;
    }

    // 构建映射数组
    var mapCount = 0;
    for (var src in REPLACE_MAP) mapCount++;
    var srcArr = Memory.alloc(mapCount * 4);
    var dstArr = Memory.alloc(mapCount * 4);
    var countsArr = Memory.alloc(mapCount * 4);  // 逐映射替换计数
    var idx = 0;
    for (var src in REPLACE_MAP) {
        srcArr.add(idx * 4).writeU32(parseInt(src));
        dstArr.add(idx * 4).writeU32(parseInt(REPLACE_MAP[src]));
        countsArr.add(idx * 4).writeU32(0);
        idx++;
    }

    var totalReplaced = 0;
    var t0 = Date.now();

    if (_nativeScanFn) {
        // 单遍正向扫描：只替换 src→dst，不恢复 dst→src
        // 上次替换的 dst 值已经在内存里，不需要动
        for (var i = 0; i < _cachedRanges.length; i++) {
            var r = _cachedRanges[i];
            var dwordCount = (r.size / 4) | 0;
            if (dwordCount < 1) continue;
            try {
                var count = _nativeScanFn(r.base, dwordCount, srcArr, dstArr, mapCount, countsArr);
                totalReplaced += count;
            } catch(e) {
                // 整块失败则分 16MB 重试
                var CHUNK = 16 * 1024 * 1024;
                var remaining = r.size;
                var off = 0;
                while (remaining >= 4) {
                    var chunkDwords = Math.min((remaining / 4) | 0, CHUNK / 4);
                    try {
                        totalReplaced += _nativeScanFn(r.base.add(off), chunkDwords, srcArr, dstArr, mapCount, countsArr);
                    } catch(e2) {}
                    off += chunkDwords * 4;
                    remaining -= chunkDwords * 4;
                }
            }
        }

        var elapsed = Date.now() - t0;
        // 读取逐映射计数摘要
        var maxCount2 = 0, nonzeroCount2 = 0;
        var maxSrc2 = '';
        var srcIdx2 = 0;
        for (var src in REPLACE_MAP) {
            var c = countsArr.add(srcIdx2 * 4).readU32();
            if (c > 0) {
                nonzeroCount2++;
                if (c > maxCount2) { maxCount2 = c; maxSrc2 = src; }
            }
            srcIdx2++;
        }
        send({t:'brute_scan_done', total: totalReplaced, ms: elapsed, ranges: _cachedRanges.length, method: 'cmodule', precommitted: _precommitted, private_mb: (totalPrivate / 1024 / 1024) | 0, total_mb: (totalAll / 1024 / 1024) | 0, precommit_ms: precommitMs, nonzero_maps: nonzeroCount2, max_per_map: maxCount2, max_src: maxSrc2});
    } else {
        // 降级：readByteArray + Uint32Array 双遍扫描
        var _lookup = {};
        var _reverseLookup = {};  // 反向：目标值→源值
        for (var src in REPLACE_MAP) {
            var srcVal = parseInt(src);
            var dstVal = parseInt(REPLACE_MAP[src]);
            if (!isNaN(srcVal) && !isNaN(dstVal)) {
                _lookup[srcVal] = dstVal;
                _reverseLookup[dstVal] = srcVal;  // 反向
            }
        }
        var CHUNK = 4 * 1024 * 1024;
        var totalRestored = 0;

        // 第一步：反向扫描，把目标值改回源值
        for (var i = 0; i < _cachedRanges.length; i++) {
            var r = _cachedRanges[i];
            var remaining = r.size;
            var off = 0;
            while (remaining >= 4) {
                var chunkLen = Math.min(remaining, CHUNK);
                chunkLen = chunkLen & ~3;
                if (chunkLen < 4) break;
                try {
                    var buf = r.base.add(off).readByteArray(chunkLen);
                    var u32 = new Uint32Array(buf);
                    var baseAddr = r.base.add(off);
                    for (var j = 0; j < u32.length; j++) {
                        var val = u32[j];
                        if (_reverseLookup[val] !== undefined) {
                            try {
                                baseAddr.add(j * 4).writeU32(_reverseLookup[val]);
                                totalRestored++;
                            } catch(e){}
                        }
                    }
                } catch(e){}
                off += chunkLen;
                remaining -= chunkLen;
            }
        }

        // 第二步：正向扫描，把源值改成目标值
        for (var i = 0; i < _cachedRanges.length; i++) {
            var r = _cachedRanges[i];
            var remaining = r.size;
            var off = 0;
            while (remaining >= 4) {
                var chunkLen = Math.min(remaining, CHUNK);
                chunkLen = chunkLen & ~3;
                if (chunkLen < 4) break;
                try {
                    var buf = r.base.add(off).readByteArray(chunkLen);
                    var u32 = new Uint32Array(buf);
                    var baseAddr = r.base.add(off);
                    for (var j = 0; j < u32.length; j++) {
                        var val = u32[j];
                        if (_lookup[val] !== undefined) {
                            try {
                                baseAddr.add(j * 4).writeU32(_lookup[val]);
                                totalReplaced++;
                            } catch(e){}
                        }
                    }
                } catch(e){}
                off += chunkLen;
                remaining -= chunkLen;
            }
        }
        var elapsed = Date.now() - t0;
        send({t:'brute_scan_done', total: totalReplaced, restored: totalRestored, ms: elapsed, ranges: _cachedRanges.length, method: 'js_fallback', precommitted: _precommitted});
    }
    return totalReplaced;
}

// ===== sprintf hook — 只做轻量替换 + 收集 =====
// DWORD 全堆扫描由 Python 端 RPC 触发

// 获取 sprintf 和 strcpy 地址
var msvcr = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = null;
var strcpyAddr = null;
var exports = msvcr.enumerateExports();
for (var i = 0; i < exports.length; i++) {
    if (exports[i].name === 'sprintf') sprintfAddr = exports[i].address;
    if (exports[i].name === 'strcpy') strcpyAddr = exports[i].address;
}

var _memDiagDone = false;  // 每个脚本生命周期只做一次内存诊断

// 快速统计某个 DWORD 在内存中出现的次数（只扫前 50 个 MEM_PRIVATE 区域）
function quickCount(targetVal) {
    var pattern = dwordToPattern(targetVal);
    var ranges = Process.enumerateRanges('rw-');
    var count = 0;
    var scanned = 0;
    for (var i = 0; i < ranges.length && scanned < 50; i++) {
        var r = ranges[i];
        if (r.size < 64 * 1024 || r.size > 200 * 1024 * 1024) continue;
        if (!isPrivateRW(r.base)) continue;
        try {
            var hits = Memory.scanSync(r.base, r.size, pattern);
            count += hits.length;
        } catch(e) {}
        scanned++;
    }
    return count;
}

// sprintf hook — 替换 + 收集 + 同步全堆扫描写特效
// 每次场景切换游戏重新加载道具数据，必须每次都扫描
var dwordScanDone = false;
var practiceDirty = false;  // 练习场暴力扫描后标记，回房间时恢复商城
var gameScene = 'unknown';  // 当前游戏场景: lobby/room/practice

function setScene(newScene) {
    if (gameScene === newScene) return;
    var old = gameScene;
    gameScene = newScene;
    // 场景切换时重置所有扫描标记
    _bruteScanDone = false;
    dwordScanDone = false;
    send({t:'scene_change', from: old, to: newScene});
}

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            if (!fastCheckCustomize(args[1])) return;
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            var isCcode = fmt.indexOf('c%d.xml') >= 0;

            // DEBUG: 记录前3个 sprintf 调用的格式串
            if (collectIndex < 3) {
                send({t:'sprintf_fmt', fmt: fmt, code: itemCode, isC: isCcode});
            }

            // 收集角色码 (c%d.xml) + 角色切换检测
            if (isCcode && COLLECT_MODE) {
                // c-code 变化 = 切换了角色 → 自动隔离上一角色的收集数据，避免污染
                if (currentCharCcode !== null && itemCode !== currentCharCcode) {
                    var prevCount = collectIndex;
                    collected = {};
                    collectIndex = 0;
                    seenCodes = {};
                    consecutiveMiss = 0;  // 切角色后重新统计 MISS
                    send({t:'batch_reset', reason: 'char_switch',
                          prev_count: prevCount, prev_char: currentCharCcode, new_char: itemCode});
                }
                currentCharCcode = itemCode;
                if (collectedCCodes.indexOf(itemCode) < 0) {
                    collectedCCodes.push(itemCode);
                    send({t:'collect_ccode', code: itemCode});
                }
            }

            // sprintf 触发 = 房间/大厅场景
            setScene('room');

            if (COLLECT_MODE) {
                // 去重：同一批次内不重复收集
                if (!seenCodes[itemCode]) {
                    seenCodes[itemCode] = true;
                    collected[collectIndex] = itemCode;
                    collectIndex++;
                }
            }

            var srcStr = String(itemCode);
            if (REPLACE_MAP[srcStr]) {
                var dstCode = parseInt(REPLACE_MAP[srcStr]);
                args[2] = ptr(dstCode);
                var ebpCount = autoReplaceEbp(this.context.ebp, itemCode, dstCode);
                patchCount++;
                consecutiveMiss = 0;  // 命中则重置
                send({t:'sprintf_hit', src: itemCode, dst: dstCode, ebp: ebpCount, idx: collectIndex});
                // 内存诊断：只在第一个 HIT 时做一次，检查 SRC/DST 在内存中的分布
                if (!_memDiagDone) {
                    _memDiagDone = true;
                    var srcCount = quickCount(itemCode);
                    var dstCount = quickCount(dstCode);
                    send({t:'mem_diag', src: itemCode, dst: dstCode, src_in_mem: srcCount, dst_in_mem: dstCount});
                }
                // 退出练习场回到房间：恢复商城数据
                if (practiceDirty) {
                    practiceDirty = false;
                    send({t:'need_restore_shop'});
                    // 退出练习场时不跑 dwordScan，暴力扫描已经做了替换
                    dwordScanDone = true;
                }
                // 只在房间场景且未扫过时做特效扫描
                if (!dwordScanDone && ENABLE_EFFECT && gameScene === 'room') {
                    dwordScanDone = true;
                    send({t:'dword_scan_trigger', src: itemCode, dst: dstCode, enable_effect: ENABLE_EFFECT, scene: gameScene});
                    dwordScan();
                }
            } else {
                consecutiveMiss++;
                // 检查 MISS 的 code 是否是某个映射的 DST 值（dwordScan 暴力替换的副作用）
                var isDstValue = false;
                var matchedSrc = '';
                for (var s in REPLACE_MAP) {
                    if (parseInt(REPLACE_MAP[s]) === itemCode) {
                        isDstValue = true;
                        matchedSrc = s;
                        break;
                    }
                }
                // 异常检测：连续 MISS 过多，说明替换映射可能失效（角色换了但映射没更新）
                if (consecutiveMiss === CONSECUTIVE_MISS_THRESHOLD && Object.keys(REPLACE_MAP).length > 0) {
                    send({t:'anomaly', code: 'too_many_miss',
                          msg: '连续' + consecutiveMiss + '次MISS',
                          mapSize: Object.keys(REPLACE_MAP).length});
                }
                send({t:'sprintf_miss', code: itemCode, idx: collectIndex, is_dst: isDstValue, matched_src: matchedSrc});
            }
        } catch(e) { send({t:'sprintf_err', msg: e.message}); }
    }
});

// strcpy hook — 练习场：路径替换 + 暴力 DWORD 扫描（只扫一次）
var _bruteScanDone = false;  // 每次进练习场只扫一次
if (strcpyAddr) {
    Interceptor.attach(strcpyAddr, {
        onEnter: function(args) {
            try {
                if (!fastCheckCustomize(args[1])) return;
                var src = readAscii(args[1], 120);
                if (src.indexOf('customize') < 0) return;

                // strcpy 触发 = 练习场场景
                setScene('practice');

                // 收集 c-code (c%d.xml)
                var cMatch = src.match(/c(\d+)\.xml/);
                if (cMatch && COLLECT_MODE) {
                    var cCode = parseInt(cMatch[1]);
                    if (collectedCCodes.indexOf(cCode) < 0) {
                        collectedCCodes.push(cCode);
                        send({t:'collect_ccode', code: cCode});
                    }
                }

                var matched = false;
                for (var srcCode in REPLACE_MAP) {
                    if (src.indexOf(srcCode) < 0) continue;
                    var dstCode = REPLACE_MAP[srcCode];
                    send({t:'strcpy_hit', path: src, src: srcCode, dst: dstCode});
                    replaceStr(args[1], srcCode, dstCode);
                    this._do = true;
                    this._dst = args[0];
                    this._srcCode = srcCode;
                    this._dstCode = dstCode;
                    patchCount++;
                    // 标记脏数据，不立即恢复！等退出练习场（sprintf触发）时再恢复
                    practiceDirty = true;
                    matched = true;
                    break;
                }
                // 只在第一次匹配时做暴力扫描（后续 strcpy 调用跳过）
                if (matched && !_bruteScanDone) {
                    _bruteScanDone = true;
                    var bruteResult = bruteDwordScan();
                    send({t:'strcpy_brute_result', replaced: bruteResult});
                }
                if (!matched) {
                    send({t:'strcpy_miss', path: src});
                }
            } catch(e) { send({t:'strcpy_err', msg: e.message}); }
        },
        onLeave: function(retval) {
            if (!this._do) return;
            replaceStr(this._dst, this._srcCode, this._dstCode);
        }
    });
}

send({t:'ready', collect: COLLECT_MODE, map: REPLACE_MAP, scene: gameScene, cmodule: _nativeScanFn ? 'ok' : 'failed'});

rpc.exports = {
    count: function() { return patchCount; },
    collected: function() { return JSON.stringify(collected); },
    collected_ccodes: function() { return JSON.stringify(collectedCCodes); },
    resetCollect: function() { collected = {}; collectIndex = 0; seenCodes = {}; },
    dwordScan: function() { return dwordScan(); },
    bruteDwordScan: function() { return bruteDwordScan(); },
    precommitPages: function() { return precommitPages(); },
    getScene: function() { return gameScene; }
};
"""

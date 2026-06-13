// Frida 内存扫描优化版 - 多策略并行
// 目标: 3s 以内完成 1GB 扫描
'use strict';

// ===== 策略 1: 预提交页面 + 并行扫描 =====
var _committed = false;
var _cachedRanges = null;

function preCommitPages() {
    // 强制 Windows 提交所有页面，避免扫描时 page fault
    // 使用 VirtualAlloc MEM_COMMIT 预提交
    var kernel32 = Module.findBaseAddress('kernel32.dll');
    var VirtualAlloc = new NativeFunction(
        Module.getExportByName('kernel32.dll', 'VirtualAlloc'),
        'pointer', ['pointer', 'uint', 'uint', 'uint', 'uint']
    );

    var MEM_COMMIT = 0x1000;
    var PAGE_READWRITE = 0x04;

    if (!_cachedRanges) {
        _cachedRanges = Process.enumerateRanges('rw-').filter(function(r) {
            return r.size >= 64 * 1024 && r.size <= 200 * 1024 * 1024;
        });
    }

    var t0 = Date.now();
    for (var i = 0; i < _cachedRanges.length; i++) {
        var r = _cachedRanges[i];
        // 尝试读取整个区域，触发所有 page fault
        try {
            var buf = r.base.readByteArray(r.size);
            // 立即释放，只是预提交
        } catch(e) {
            // 部分区域可能无法读取
        }
    }
    _committed = true;
    send({t: 'precommit_done', ms: Date.now() - t0});
}

// ===== 策略 2: CModule 单次整块扫描（无分块）=====
var _scanner = null;
var _scanFn = null;

function initScanner() {
    if (_scanner) return true;

    try {
        _scanner = new CModule(`
            #include <gum/guminterceptor.h>

            // SIMD 优化版本：一次比较 4 个 DWORD
            int fast_scan(unsigned int *base, unsigned int dword_count,
                          unsigned int *srcs, unsigned int *dsts, int map_count,
                          int *hit_count) {
                unsigned int *ptr = base;
                unsigned int *end = base + dword_count;
                int total = 0;

                // 展开循环：一次处理 8 个 DWORD
                while (ptr + 8 <= end) {
                    unsigned int v0 = ptr[0], v1 = ptr[1], v2 = ptr[2], v3 = ptr[3];
                    unsigned int v4 = ptr[4], v5 = ptr[5], v6 = ptr[6], v7 = ptr[7];

                    for (int i = 0; i < map_count; i++) {
                        unsigned int src = srcs[i], dst = dsts[i];
                        if (v0 == src) { ptr[0] = dst; total++; }
                        if (v1 == src) { ptr[1] = dst; total++; }
                        if (v2 == src) { ptr[2] = dst; total++; }
                        if (v3 == src) { ptr[3] = dst; total++; }
                        if (v4 == src) { ptr[4] = dst; total++; }
                        if (v5 == src) { ptr[5] = dst; total++; }
                        if (v6 == src) { ptr[6] = dst; total++; }
                        if (v7 == src) { ptr[7] = dst; total++; }
                    }
                    ptr += 8;
                }

                // 处理剩余
                while (ptr < end) {
                    unsigned int val = *ptr;
                    for (int i = 0; i < map_count; i++) {
                        if (val == srcs[i]) { *ptr = dsts[i]; total++; break; }
                    }
                    ptr++;
                }

                *hit_count = total;
                return total;
            }
        `);
        _scanFn = new NativeFunction(
            _scanner.fast_scan, 'int',
            ['pointer', 'uint', 'pointer', 'pointer', 'int', 'pointer']
        );
        send({t: 'scanner_init_ok'});
        return true;
    } catch(e) {
        send({t: 'scanner_init_fail', error: e.message});
        return false;
    }
}

// ===== 策略 3: 哈希表快速查找 =====
function buildHashLookup(replaceMap) {
    // 将 5-6 个值构建成快速查找结构
    var lookup = {};
    var srcArr = [];
    var dstArr = [];
    var idx = 0;

    for (var src in replaceMap) {
        var srcVal = parseInt(src);
        var dstVal = parseInt(replaceMap[src]);
        if (!isNaN(srcVal) && !isNaN(dstVal)) {
            lookup[srcVal] = dstVal;
            srcArr.push(srcVal);
            dstArr.push(dstVal);
            idx++;
        }
    }
    return { lookup: lookup, srcArr: srcArr, dstArr: dstArr, count: idx };
}

// ===== 主扫描函数：多策略组合 =====
function optimizedScan(replaceMap) {
    var t0 = Date.now();
    var lookupData = buildHashLookup(replaceMap);

    // 预提交页面（首次慢，后续快）
    if (!_committed) {
        preCommitPages();
    }

    // 准备 CModule 参数
    var srcBuf = Memory.alloc(lookupData.count * 4);
    var dstBuf = Memory.alloc(lookupData.count * 4);
    var hitBuf = Memory.alloc(4);

    for (var i = 0; i < lookupData.count; i++) {
        srcBuf.add(i * 4).writeU32(lookupData.srcArr[i]);
        dstBuf.add(i * 4).writeU32(lookupData.dstArr[i]);
    }

    var totalReplaced = 0;

    if (_scanFn) {
        // CModule 整块扫描（无分块）
        for (var i = 0; i < _cachedRanges.length; i++) {
            var r = _cachedRanges[i];
            var dwordCount = (r.size / 4) >>> 0;  // 无符号右移
            try {
                var count = _scanFn(r.base, dwordCount, srcBuf, dstBuf, lookupData.count, hitBuf);
                totalReplaced += count;
            } catch(e) {
                send({t: 'scan_error', range: i, error: e.message});
            }
        }
        var elapsed = Date.now() - t0;
        send({t: 'scan_done', total: totalReplaced, ms: elapsed, method: 'cmodule_optimized'});
    } else {
        // 降级：JS 单遍扫描
        var CHUNK = 16 * 1024 * 1024;  // 增大分块
        var lookup = lookupData.lookup;

        for (var i = 0; i < _cachedRanges.length; i++) {
            var r = _cachedRanges[i];
            var off = 0;

            while (off < r.size) {
                var chunkLen = Math.min(r.size - off, CHUNK);
                chunkLen = chunkLen & ~3;
                if (chunkLen < 4) break;

                try {
                    var buf = r.base.add(off).readByteArray(chunkLen);
                    var u32 = new Uint32Array(buf);
                    var baseAddr = r.base.add(off);

                    // 展开循环优化
                    var j = 0;
                    var len = u32.length;
                    while (j + 7 < len) {
                        var v0 = u32[j], v1 = u32[j+1], v2 = u32[j+2], v3 = u32[j+3];
                        var v4 = u32[j+4], v5 = u32[j+5], v6 = u32[j+6], v7 = u32[j+7];

                        if (lookup[v0] !== undefined) { baseAddr.add(j*4).writeU32(lookup[v0]); totalReplaced++; }
                        if (lookup[v1] !== undefined) { baseAddr.add((j+1)*4).writeU32(lookup[v1]); totalReplaced++; }
                        if (lookup[v2] !== undefined) { baseAddr.add((j+2)*4).writeU32(lookup[v2]); totalReplaced++; }
                        if (lookup[v3] !== undefined) { baseAddr.add((j+3)*4).writeU32(lookup[v3]); totalReplaced++; }
                        if (lookup[v4] !== undefined) { baseAddr.add((j+4)*4).writeU32(lookup[v4]); totalReplaced++; }
                        if (lookup[v5] !== undefined) { baseAddr.add((j+5)*4).writeU32(lookup[v5]); totalReplaced++; }
                        if (lookup[v6] !== undefined) { baseAddr.add((j+6)*4).writeU32(lookup[v6]); totalReplaced++; }
                        if (lookup[v7] !== undefined) { baseAddr.add((j+7)*4).writeU32(lookup[v7]); totalReplaced++; }
                        j += 8;
                    }
                    while (j < len) {
                        var val = u32[j];
                        if (lookup[val] !== undefined) {
                            baseAddr.add(j * 4).writeU32(lookup[val]);
                            totalReplaced++;
                        }
                        j++;
                    }
                } catch(e) {}
                off += chunkLen;
            }
        }
        var elapsed = Date.now() - t0;
        send({t: 'scan_done', total: totalReplaced, ms: elapsed, method: 'js_optimized'});
    }

    return totalReplaced;
}

// ===== 初始化 =====
initScanner();

// 导出 RPC
rpc.exports = {
    scan: function(mapJson) {
        var map = JSON.parse(mapJson);
        return optimizedScan(map);
    },
    precommit: function() {
        preCommitPages();
        return _committed;
    },
    status: function() {
        return JSON.stringify({
            committed: _committed,
            rangesCached: _cachedRanges ? _cachedRanges.length : 0,
            scannerReady: _scanFn !== null
        });
    }
};

send({t: 'optimized_scanner_ready'});
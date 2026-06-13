// Frida 内存扫描性能诊断脚本
// 运行方式: frida -p <pid> -l diagnose_scan.js
'use strict';

var results = {
    enumerateRanges: 0,
    filterRanges: 0,
    readByteArray: 0,
    scanLoop: 0,
    writeBack: 0,
    nativeCall: 0,
    cmoduleCompile: 0
};

// ===== 测试 1: enumerateRanges 耗时 =====
function testEnumerateRanges() {
    var t0 = Date.now();
    var ranges = Process.enumerateRanges('rw-');
    results.enumerateRanges = Date.now() - t0;
    return ranges;
}

// ===== 测试 2: readByteArray 纯读速度 =====
function testReadSpeed(ranges) {
    var totalBytes = 0;
    var t0 = Date.now();
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 64 * 1024 || r.size > 200 * 1024 * 1024) continue;
        try {
            var chunk = r.base.readByteArray(Math.min(r.size, 64 * 1024 * 1024));
            totalBytes += chunk.byteLength;
        } catch(e) {}
    }
    results.readByteArray = Date.now() - t0;
    return totalBytes;
}

// ===== 测试 3: NativeFunction 调用开销 =====
function testNativeCallOverhead() {
    // 创建一个空的 C 函数，只测量调用开销
    var emptyFn = new CModule('int empty(void) { return 0; }');
    var callEmpty = new NativeFunction(emptyFn.empty, 'int', []);

    var t0 = Date.now();
    for (var i = 0; i < 10000; i++) {
        callEmpty();
    }
    results.nativeCall = Date.now() - t0;
    return results.nativeCall / 10000;  // 平均每次调用毫秒
}

// ===== 测试 4: CModule 编译时间 =====
function testCModuleCompile() {
    var t0 = Date.now();
    var scanner = new CModule(
        'int chunk_scan(unsigned int *base, unsigned int dword_count,' +
        '               unsigned int *srcs, unsigned int *dsts, int map_count) {' +
        '  unsigned int *ptr = base;' +
        '  unsigned int *end = base + dword_count;' +
        '  int total = 0;' +
        '  while (ptr < end) {' +
        '    unsigned int val = *ptr;' +
        '    for (int i = 0; i < map_count; i++) {' +
        '      if (val == srcs[i]) { *ptr = dsts[i]; total++; break; }' +
        '    }' +
        '    ptr++;' +
        '  }' +
        '  return total;' +
        '}'
    );
    results.cmoduleCompile = Date.now() - t0;
    return scanner;
}

// ===== 测试 5: CModule 单次大块扫描 vs 多次小块 =====
function testChunkSizeImpact(scanner, ranges) {
    var callScan = new NativeFunction(scanner.chunk_scan, 'int',
        ['pointer', 'uint', 'pointer', 'pointer', 'int']);

    // 准备 src/dst 数组
    var srcArr = Memory.alloc(4);
    var dstArr = Memory.alloc(4);
    srcArr.writeU32(0x12345678);
    dstArr.writeU32(0x87654321);

    var testRange = null;
    for (var i = 0; i < ranges.length; i++) {
        if (ranges[i].size >= 100 * 1024 * 1024) {
            testRange = ranges[i];
            break;
        }
    }
    if (!testRange) {
        send({t: 'no_large_range'});
        return;
    }

    // 测试 1: 1MB 分块
    var chunk1MB = 1024 * 1024;
    var t0 = Date.now();
    var off = 0;
    while (off < testRange.size) {
        var dwordCount = Math.min((testRange.size - off) / 4, chunk1MB / 4);
        callScan(testRange.base.add(off), dwordCount, srcArr, dstArr, 1);
        off += dwordCount * 4;
    }
    var time1MB = Date.now() - t0;

    // 测试 2: 16MB 分块
    var chunk16MB = 16 * 1024 * 1024;
    t0 = Date.now();
    off = 0;
    while (off < testRange.size) {
        var dwordCount = Math.min((testRange.size - off) / 4, chunk16MB / 4);
        callScan(testRange.base.add(off), dwordCount, srcArr, dstArr, 1);
        off += dwordCount * 4;
    }
    var time16MB = Date.now() - t0;

    // 测试 3: 整块扫描
    t0 = Date.now();
    callScan(testRange.base, testRange.size / 4, srcArr, dstArr, 1);
    var timeFull = Date.now() - t0;

    send({
        t: 'chunk_size_test',
        rangeSize: testRange.size,
        time1MB: time1MB,
        time16MB: time16MB,
        timeFull: timeFull
    });
}

// ===== 测试 6: readByteArray + Uint32Array 纯 JS 扫描 =====
function testJsScan(ranges) {
    var lookup = {0x12345678: 0x87654321};  // 测试用
    var CHUNK = 4 * 1024 * 1024;

    var t0 = Date.now();
    var totalReplaced = 0;
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 64 * 1024 || r.size > 200 * 1024 * 1024) continue;

        var off = 0;
        while (off < r.size) {
            var chunkLen = Math.min(r.size - off, CHUNK);
            chunkLen = chunkLen & ~3;
            if (chunkLen < 4) break;

            try {
                var buf = r.base.add(off).readByteArray(chunkLen);
                var u32 = new Uint32Array(buf);
                var baseAddr = r.base.add(off);

                for (var j = 0; j < u32.length; j++) {
                    if (lookup[u32[j]] !== undefined) {
                        baseAddr.add(j * 4).writeU32(lookup[u32[j]]);
                        totalReplaced++;
                    }
                }
            } catch(e) {}
            off += chunkLen;
        }
    }
    results.scanLoop = Date.now() - t0;
    return totalReplaced;
}

// ===== 测试 7: 纯内存访问速度（无扫描逻辑）=====
function testRawMemoryAccess(ranges) {
    var t0 = Date.now();
    var sum = 0;
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 64 * 1024 || r.size > 200 * 1024 * 1024) continue;

        // 每 4KB 读一个 DWORD
        var steps = Math.floor(r.size / 4096);
        for (var j = 0; j < steps; j++) {
            try {
                sum += r.base.add(j * 4096).readU32();
            } catch(e) {}
        }
    }
    return { time: Date.now() - t0, sum: sum };
}

// ===== 主测试流程 =====
function runDiagnosis() {
    send({t: 'diagnosis_start'});

    // 1. enumerateRanges
    var ranges = testEnumerateRanges();
    send({t: 'enumerateRanges', ms: results.enumerateRanges, count: ranges.length});

    // 2. 过滤区域
    var t0 = Date.now();
    var filtered = [];
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size >= 64 * 1024 && r.size <= 200 * 1024 * 1024) {
            filtered.push(r);
        }
    }
    results.filterRanges = Date.now() - t0;
    send({t: 'filterRanges', ms: results.filterRanges, kept: filtered.length});

    // 3. readByteArray 速度
    var totalBytes = testReadSpeed(filtered);
    send({t: 'readByteArray', ms: results.readByteArray, totalMB: (totalBytes / 1024 / 1024).toFixed(1)});

    // 4. NativeFunction 调用开销
    var avgCallTime = testNativeCallOverhead();
    send({t: 'nativeCall', ms: results.nativeCall, avgUs: (avgCallTime * 1000).toFixed(2)});

    // 5. CModule 编译
    var scanner = testCModuleCompile();
    send({t: 'cmoduleCompile', ms: results.cmoduleCompile});

    // 6. 分块大小影响
    testChunkSizeImpact(scanner, ranges);

    // 7. JS 扫描速度
    var jsCount = testJsScan(filtered);
    send({t: 'jsScan', ms: results.scanLoop, replaced: jsCount});

    // 8. 纯内存访问
    var rawResult = testRawMemoryAccess(filtered);
    send({t: 'rawMemoryAccess', ms: rawResult.time});

    send({t: 'diagnosis_complete', results: results});
}

// 延迟执行，等待进程稳定
setTimeout(runDiagnosis, 1000);
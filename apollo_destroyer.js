// ============================================================
// apollo_destroyer.js — Apollo 拆除脚本 (Frida 侧)
// Phase 2-4: 挂起保护线程 → 解锁.text → 定位AcquireSMD
// ============================================================

var kernel32 = Process.getModuleByName('kernel32.dll');
var OpenThread = new NativeFunction(
    kernel32.getExportByName('OpenThread'),
    'pointer', ['uint32', 'int', 'uint32']
);
var SuspendThread = new NativeFunction(
    kernel32.getExportByName('SuspendThread'),
    'int', ['pointer']
);
var CloseHandle = new NativeFunction(
    kernel32.getExportByName('CloseHandle'),
    'int', ['pointer']
);
var THREAD_SUSPEND_RESUME = 0x0002;

function suspendThread(tid) {
    try {
        var h = OpenThread(THREAD_SUSPEND_RESUME, 0, tid);
        if (h.isNull()) return false;
        SuspendThread(h);
        CloseHandle(h);
        return true;
    } catch(e) { return false; }
}

function killPhase2() {
    send({t: 'PHASE2', msg: '=== Phase 2: CRC patch + Suspend ApolloCT threads ==='});

    // --- Step 2.0: CRC patch FIRST (before anything else) ---
    // Frida-agent.dll 注入到内存后, CRC 线程可能在枚举线程前就扫描到异常 → 崩溃
    // 必须优先 patch CRC, 消除检测窗口
    send({t: 'PHASE2', msg: 'Step 2.0: Patching CRC...'});
    var apolloMod = Process.getModuleByName('ApolloCT.dll');
    try {
        var crc1 = apolloMod.base.add(0x1A3C54);
        var crc2 = apolloMod.base.add(0x1BE222);
        Memory.protect(crc1.and(ptr(0xFFFFF000)), 4096, 'rwx');
        crc1.writeByteArray([0x33, 0xC0, 0xC3]);  // xor eax,eax; ret
        crc2.writeByteArray([0x33, 0xC0, 0xC3]);
        Memory.protect(crc1.and(ptr(0xFFFFF000)), 4096, 'rx');
        send({t: 'CRC', msg: 'CRC patched at 0x1A3C54 + 0x1BE222'});
    } catch(e) {
        send({t: 'CRC', msg: 'CRC patch FAILED: ' + e});
    }

    // --- Step 2.1: Suspend ApolloCT threads ---
    var apolloBase = apolloMod.base;
    var apolloEnd = apolloBase.add(apolloMod.size);
    var found = 0;
    var suspended = 0;

    Process.enumerateThreads().forEach(function(t) {
        var ctx, eip;
        try {
            ctx = t.context;
            eip = ctx.eip;
        } catch(e) { return; }

        if (eip.compare(apolloBase) >= 0 && eip.compare(apolloEnd) < 0) {
            found++;
            // 获取栈回溯
            var bt;
            try { bt = Thread.backtrace(ctx, Backtracer.ACCURATE); }
            catch(e) { bt = Thread.backtrace(ctx, Backtracer.FUZZY); }

            var inApollo = 0;
            bt.forEach(function(addr) {
                if (addr.compare(apolloBase) >= 0 && addr.compare(apolloEnd) < 0) inApollo++;
            });

            send({t: 'APOLLO_THREAD', id: t.id, eip: eip.sub(apolloBase).toString(16),
                  apolloFrames: inApollo, totalFrames: bt.length});

            // 挂起
            if (suspendThread(t.id)) {
                suspended++;
                send({t: 'SUSPEND', id: t.id});
            } else {
                send({t: 'SUSPEND_FAIL', id: t.id});
            }
        }
    });
    send({t: 'PHASE2', msg: 'Phase 2 done. ApolloCT threads: ' + found + ' found, ' + suspended + ' suspended.'});
}

function killPhase3() {
    send({t: 'PHASE3', msg: '=== Phase 3: Unlock FreeStyle.exe .text ==='});
    var fsMod = Process.getModuleByName('FreeStyle.exe');
    var textSection = null;
    fsMod.enumerateSections().forEach(function(s) {
        if (s.name === '.text') textSection = s;
    });

    if (!textSection) {
        send({t: 'PHASE3', msg: 'ERROR: .text section not found!'});
        return;
    }

    var textBase = textSection.address;
    var textSize = textSection.size;
    send({t: 'PHASE3', msg: '.text at ' + textBase + ' size=' + textSize});

    // 整体尝试
    try {
        Memory.protect(textBase, textSize, 'rwx');
        send({t: 'PHASE3', msg: 'Unlocked full .text section (' + textSize + ' bytes) in one call.'});
    } catch(e) {
        send({t: 'PHASE3', msg: 'Full protect failed: ' + e + '. Falling back to per-page...'});
        var pageCount = 0;
        var totalPages = Math.ceil(textSize / 4096);
        for (var off = 0; off < textSize; off += 4096) {
            try {
                Memory.protect(textBase.add(off), 4096, 'rwx');
                pageCount++;
            } catch(e2) {}
        }
        send({t: 'PHASE3', msg: 'Unlocked ' + pageCount + '/' + totalPages + ' pages.'});
    }
}

function killPhase35() {
    send({t: 'PHASE35', msg: '=== Phase 3.5: Apollo2.dll + L2 embedded Apollo ==='});

    // --- Apollo2.dll ---
    var apollo2Mod = null;
    try { apollo2Mod = Process.getModuleByName('Apollo2.dll'); } catch(e) {}

    if (apollo2Mod) {
        var a2Base = apollo2Mod.base;
        var a2End = a2Base.add(apollo2Mod.size);
        var a2_found = 0, a2_suspended = 0;
        Process.enumerateThreads().forEach(function(t) {
            try {
                var eip = t.context.eip;
                if (eip.compare(a2Base) >= 0 && eip.compare(a2End) < 0) {
                    a2_found++;
                    send({t: 'APOLLO2_THREAD', id: t.id, eip: eip.sub(a2Base).toString(16)});
                    if (suspendThread(t.id)) a2_suspended++;
                }
            } catch(e) {}
        });
        send({t: 'PHASE35', msg: 'Apollo2.dll: ' + a2_found + ' threads, ' + a2_suspended + ' suspended.'});
    } else {
        send({t: 'PHASE35', msg: 'Apollo2.dll not loaded. Skipping.'});
    }

    // --- L2 embedded Apollo ---
    var fsMod = Process.getModuleByName('FreeStyle.exe');
    // Apollo segments in FreeStyle.exe (progress_20260522 §31.2)
    var apolloSegStart = fsMod.base.add(0x0280C000);
    var apolloSegEnd   = fsMod.base.add(0x02814000 + 928 * 1024);
    var l2_found = 0, l2_suspended = 0;

    Process.enumerateThreads().forEach(function(t) {
        try {
            var eip = t.context.eip;
            if (eip.compare(apolloSegStart) >= 0 && eip.compare(apolloSegEnd) < 0) {
                l2_found++;
                send({t: 'L2_THREAD', id: t.id, eip: eip.sub(fsMod.base).toString(16)});
                if (suspendThread(t.id)) l2_suspended++;
            }
        } catch(e) {}
    });
    send({t: 'PHASE35', msg: 'L2 Apollo segment: ' + l2_found + ' threads, ' + l2_suspended + ' suspended.'});
}

function killPhase4() {
    send({t: 'PHASE4', msg: '=== Phase 4: Locate AcquireSMD ==='});
    var fsMod = Process.getModuleByName('FreeStyle.exe');

    // Strategy A: search format string reference
    send({t: 'PHASE4', msg: 'Strategy A: search format string ref...'});
    try {
        var pattern = 'DE B9 84 02';
        var hits = Memory.scanSync(fsMod.base, fsMod.size, pattern);
        send({t: 'SSREF_HITS', count: hits.length, addrs: hits.slice(0, 10).map(function(h){return h.toString();})});
    } catch(e) {
        send({t: 'SSREF_HITS', err: '' + e});
    }

    // Strategy B: search SSKF magic
    send({t: 'PHASE4', msg: 'Strategy B: search SSKF magic...'});
    try {
        var sskf = '53 53 4B 46';
        var sskfHits = Memory.scanSync(fsMod.base, fsMod.size, sskf);
        send({t: 'SSKF_HITS', count: sskfHits.length, addrs: sskfHits.slice(0, 10).map(function(h){return h.toString();})});
    } catch(e) {
        send({t: 'SSKF_HITS', err: '' + e});
    }

    // Strategy C: verify Interceptor.attach on game code works
    send({t: 'PHASE4', msg: 'Strategy C: test Interceptor.attach on game code...'});
    var testAddr = fsMod.base.add(0x21e25b0);
    try {
        Interceptor.attach(testAddr, {
            onEnter: function(args) {
                send({t: 'ATTACH_TEST', msg: 'Interceptor.attach on game code WORKS!'});
            }
        });
        send({t: 'ATTACH_OK', msg: 'Interceptor.attach SUCCESS on 0x21e25b0 (game code).'});
    } catch(e) {
        send({t: 'ATTACH_FAIL', msg: '' + e});
    }
}

// --- RPC exports ---
rpc.exports = {
    killall: function() {
        killPhase2();
        killPhase35();
        killPhase3();
        killPhase4();
        send({t: 'DONE', msg: 'ALL PHASES COMPLETE.'});
    },
    phase2: killPhase2,
    phase3: killPhase3,
    phase35: killPhase35,
    phase4: killPhase4,
    status: function() {
        var fsMod = Process.getModuleByName('FreeStyle.exe');
        send({t: 'STATUS', base: fsMod.base.toString(), size: fsMod.size});
    }
};

send({t: 'READY', msg: 'Apollo destroyer loaded. Commands: killall | phase2 | phase3 | phase35 | phase4 | status'});
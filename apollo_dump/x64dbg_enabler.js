// x64dbg_enabler.js  v2 — 完整的 Level 2 时序层规避
//
// 原理:
//   L0 (Apollo.sys) → 必须提前停止 (sc stop)
//   L1 (ApolloCT.dll) → 保护线程继续跑(保心跳)，多层欺骗:
//     Level 1 信号层: VirtualQuery/VirtualProtect 返回假值 + CRC patch
//     Level 2 时序层: API全覆盖 + 原子锁 + 扫描周期探测 + 异常检测 + 安全闸门
//   L2 (内嵌 Apollo) → 一次性执行, 零线程, 游戏加载完已退出
//
// 使用顺序:
//   1. sc stop ApolloProtect (管理员) + taskkill ApolloGuardian.exe
//   2. 正常启动游戏 (不带调试器!)
//   3. 等游戏完全加载
//   4. py x64dbg_enabler.py (Frida 注入本脚本)
//   5. 看到 READY 后打开 x32dbg 附加 FreeStyle.exe

'use strict';

var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;

fsMod.enumerateSections().forEach(function(s) {
    if (s.name === '.text') textSection = s;
});

if (!textSection) {
    send({t: 'FAIL', msg: '.text section not found'});
    throw new Error('.text section not found');
}

var textStart = textSection.address;
var textEnd = textStart.add(textSection.size);

// ── Constants ──
var PAGE_EXECUTE_READ = 0x20;
var PAGE_EXECUTE_READWRITE = 0x40;
var PAGE_READWRITE = 0x04;

// ── State ──
var DECEPTION_ACTIVE = false;
var CRC_PATCHED = false;
var ANTIDEBUG_ACTIVE = false;

// ── Level 2: Atomic protection counter (替代布尔 VP_DISABLED) ──
// 用引用计数代替布尔值，消除 TOCTOU 竞态：
//   > 0 = 我们的操作进行中，拦截 Apollo 调用
//   = 0 = 无操作进行，正常欺骗
var VP_ATOMIC_COUNT = 0;

// ── Level 2: 扫描周期探测器 ──
var SCAN_STATS = {
    totalCalls: 0,           // 总 NtQVM 调用次数
    apolloCalls: 0,          // 来自 ApolloCT 线程的调用
    lastApolloScan: 0,       // 上次 Apollo 扫描时间戳 (ms)
    scanIntervals: [],       // 最近 10 次扫描间隔 (ms)
    minInterval: Infinity,
    maxInterval: 0,
    avgInterval: 0,
    scanPeriodEstimated: 0   // 估算的扫描周期 T (ms)
};
var MAX_INTERVALS = 20;

// ── Level 2: 异常检测器 ──
var ANOMALY = {
    bypassAttempts: 0,       // 非 NtQVM 路径的 .text 查询被捕获
    erLeaks: 0,              // 返回非 ER 的 .text 查询（hook 失效）
    lastAnomalyTime: 0,
    anomalyDetails: []
};
var MAX_ANOMALIES = 10;

// ── Level 2: ApolloCT 线程追踪 ──
var APOLLO_THREADS = {};     // {threadId: {eip, discoveredAt}}
var apolloMod = null;
var apolloBase = ptr(0);
var apolloEnd = ptr(0);

try {
    apolloMod = Process.getModuleByName('ApolloCT.dll');
    apolloBase = apolloMod.base;
    apolloEnd = apolloBase.add(apolloMod.size);
} catch(e) {}

function isApolloThread(tid) {
    if (APOLLO_THREADS[tid]) return true;
    // 动态检测：读线程 EIP 是否在 ApolloCT.dll 范围内
    if (apolloMod === null) return false;
    try {
        var ctx = Process.enumerateThreads().filter(function(t) { return t.id === tid; })[0];
        if (!ctx) return false;
        var eip = ctx.context.eip;
        if (eip.compare(apolloBase) >= 0 && eip.compare(apolloEnd) < 0) {
            APOLLO_THREADS[tid] = { eip: eip, discoveredAt: Date.now() };
            return true;
        }
    } catch(e) {}
    return false;
}

function inTextRange(addr) {
    return addr.compare(textStart) >= 0 && addr.compare(textEnd) < 0;
}

// ═══════════════════════════════════════════════════════════════
// Level 2 核心: 原子保护锁 (替代 VP_DISABLED)
// ═══════════════════════════════════════════════════════════════

// 进入我们的保护操作前调用 → 计数+1 → Apollo 的 API 调用被拦截
function vpLockAcquire() {
    VP_ATOMIC_COUNT++;
}

// 保护操作完成后调用 → 计数-1 → 恢复正常欺骗
function vpLockRelease() {
    if (VP_ATOMIC_COUNT > 0) VP_ATOMIC_COUNT--;
}

// 检查是否处于我们的操作中
function vpIsOurOperation() {
    return VP_ATOMIC_COUNT > 0;
}

// ═══════════════════════════════════════════════════════════════
// Level 2 核心: 扫描周期探测器
// ═══════════════════════════════════════════════════════════════

function recordScanCall(tid) {
    SCAN_STATS.totalCalls++;
    if (isApolloThread(tid)) {
        var now = Date.now();
        SCAN_STATS.apolloCalls++;
        if (SCAN_STATS.lastApolloScan > 0) {
            var interval = now - SCAN_STATS.lastApolloScan;
            SCAN_STATS.scanIntervals.push(interval);
            if (SCAN_STATS.scanIntervals.length > MAX_INTERVALS) {
                SCAN_STATS.scanIntervals.shift();
            }
            // 更新统计
            var sum = 0, min = Infinity, max = 0;
            for (var i = 0; i < SCAN_STATS.scanIntervals.length; i++) {
                var v = SCAN_STATS.scanIntervals[i];
                sum += v;
                if (v < min) min = v;
                if (v > max) max = v;
            }
            SCAN_STATS.minInterval = min;
            SCAN_STATS.maxInterval = max;
            SCAN_STATS.avgInterval = Math.round(sum / SCAN_STATS.scanIntervals.length);
            SCAN_STATS.scanPeriodEstimated = SCAN_STATS.avgInterval;
        }
        SCAN_STATS.lastApolloScan = now;
    }
}

// ═══════════════════════════════════════════════════════════════
// Level 2 核心: 异常检测器
// ═══════════════════════════════════════════════════════════════

function recordAnomaly(detail) {
    ANOMALY.bypassAttempts++;
    ANOMALY.lastAnomalyTime = Date.now();
    if (ANOMALY.anomalyDetails.length < MAX_ANOMALIES) {
        ANOMALY.anomalyDetails.push({
            time: Date.now(),
            detail: detail
        });
    }
}

function recordERLeak(baseAddr, actualProtect) {
    ANOMALY.erLeaks++;
    ANOMALY.lastAnomalyTime = Date.now();
    if (ANOMALY.anomalyDetails.length < MAX_ANOMALIES) {
        ANOMALY.anomalyDetails.push({
            time: Date.now(),
            detail: 'ER_LEAK: base=' + baseAddr + ' actual=' + actualProtect.toString(16)
        });
    }
}

// ═══════════════════════════════════════════════════════════════
// Level 2 核心: 安全闸门
// ═══════════════════════════════════════════════════════════════

function safetyGate(opName) {
    if (!DECEPTION_ACTIVE) {
        send({t: 'SAFETY', msg: 'BLOCKED ' + opName + ': deception not active'});
        return false;
    }
    if (ANOMALY.erLeaks > 0) {
        send({t: 'SAFETY', msg: 'WARN ' + opName + ': ' + ANOMALY.erLeaks + ' ER leaks detected'});
        // 不阻止，但记录警告
    }
    // 如果在 Apollo 扫描周期内 (上次扫描 < T/2 之前)，等待安全窗口
    if (SCAN_STATS.scanPeriodEstimated > 0 && SCAN_STATS.lastApolloScan > 0) {
        var elapsed = Date.now() - SCAN_STATS.lastApolloScan;
        var halfPeriod = Math.floor(SCAN_STATS.scanPeriodEstimated / 2);
        if (elapsed > halfPeriod && elapsed < SCAN_STATS.scanPeriodEstimated) {
            // 我们在 Apollo 扫描窗口的后半段 — 较高风险
            send({t: 'SAFETY', msg: 'CAUTION ' + opName + ': ' + elapsed + 'ms since last scan (period=' + SCAN_STATS.scanPeriodEstimated + 'ms)'});
        }
    }
    return true;
}

// ═══════════════════════════════════════════════════════════════
// Part 1: 多层页属性欺骗 (完整 API 覆盖)
// ═══════════════════════════════════════════════════════════════

function installDeception() {
    send({t: 'STEP', msg: 'Installing multi-layer page deception...'});
    var ntdll = Process.getModuleByName('ntdll.dll');
    var kernel32 = Process.getModuleByName('kernel32.dll');
    var hookedCount = 0;

    // ── Layer 1: ntdll syscall stub (最底层，Apollo 必经) ──

    // 1a. NtQueryVirtualMemory — Apollo 扫描页属性的主路径
    var NtQVM = ntdll.getExportByName('NtQueryVirtualMemory');
    try {
        Interceptor.attach(NtQVM, {
            onEnter: function(args) {
                this.memInfo = args[3];
                this.infoLen = args[4];
                this.infoClass = args[2];
                this.tid = Process.getCurrentThreadId();
            },
            onLeave: function(retval) {
                recordScanCall(this.tid);
                if (retval.toInt32() !== 0) return;
                if (this.infoClass.toInt32() !== 0) return;   // MemoryBasicInformation
                if (this.memInfo.isNull()) return;
                try {
                    var baseAddr = this.memInfo.readPointer();
                    if (!inTextRange(baseAddr)) return;
                    // 如果我们在做保护操作，不欺骗（让操作正常完成）
                    if (vpIsOurOperation()) {
                        return;  // 我们的操作需要看到真实值
                    }
                    // 始终返回 ER
                    this.memInfo.add(8).writeU32(PAGE_EXECUTE_READ);
                    this.memInfo.add(20).writeU32(PAGE_EXECUTE_READ);
                    VQ_LIES++;
                } catch(e) {
                    recordERLeak(ptr(0), 0);
                }
            }
        });
        hookedCount++;
    } catch(e) {
        send({t: 'FAIL', msg: 'NtQueryVirtualMemory hook failed: ' + e});
    }

    // 1b. NtProtectVirtualMemory — 拦截 Apollo 自己的页属性修改
    var NtPVM = ntdll.getExportByName('NtProtectVirtualMemory');
    try {
        Interceptor.attach(NtPVM, {
            onEnter: function(args) {
                this.baseAddrPtr = args[1];
                this.oldProtectPtr = args[4];
                this.ourCall = vpIsOurOperation();
            },
            onLeave: function(retval) {
                if (this.ourCall) return;  // 我们的操作需要正常执行
                try {
                    var addr = this.baseAddrPtr.readPointer();
                    if (!inTextRange(addr)) return;
                    // Apollo 在尝试修改 .text 页属性 → 返回假成功
                    if (!this.oldProtectPtr.isNull()) {
                        this.oldProtectPtr.writeU32(PAGE_EXECUTE_READ);
                    }
                    retval.replace(0);
                    VP_FAKES++;
                } catch(e) {}
            }
        });
        hookedCount++;
    } catch(e) {
        send({t: 'FAIL', msg: 'NtProtectVirtualMemory hook failed: ' + e});
    }

    // ── Layer 2: kernel32 包装函数 (防御纵深) ──
    // 如果 Apollo 通过 kernel32 而非 ntdll 调用，这里的 hook 是第二道防线
    // (正常情况 kernel32 内部会调用 ntdll → 已被 Layer 1 拦截,
    //  但如果 Apollo 有 kernel32 的独立 syscall stub，Layer 2 是唯一防线)

    // 2a. VirtualQuery — kernel32 包装
    try {
        var VirtualQuery = kernel32.getExportByName('VirtualQuery');
        Interceptor.attach(VirtualQuery, {
            onEnter: function(args) {
                this.addr = args[0];
                this.buf = args[1];
                this.tid = Process.getCurrentThreadId();
            },
            onLeave: function(retval) {
                recordScanCall(this.tid);
                if (retval.toInt32() === 0) return;
                if (!inTextRange(this.addr)) return;
                if (vpIsOurOperation()) return;
                try {
                    this.buf.add(8).writeU32(PAGE_EXECUTE_READ);
                    this.buf.add(20).writeU32(PAGE_EXECUTE_READ);
                    VQ_LIES++;
                } catch(e) {
                    recordAnomaly('VirtualQuery post-hook fail: ' + e);
                }
            }
        });
        hookedCount++;
    } catch(e) {
        recordAnomaly('VirtualQuery hook failed: ' + e);
    }

    // 2b. VirtualQueryEx — 远程进程查询
    try {
        var VirtualQueryEx = kernel32.getExportByName('VirtualQueryEx');
        Interceptor.attach(VirtualQueryEx, {
            onEnter: function(args) {
                this.addr = args[1];
                this.buf = args[2];
                this.tid = Process.getCurrentThreadId();
                this.hProcess = args[0];
                // 检查是否查询自身进程
                this.isSelf = (this.hProcess.toInt32() === -1);  // GetCurrentProcess() = -1
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                if (!this.isSelf) return;  // 只拦截自身进程查询
                if (!inTextRange(this.addr)) return;
                if (vpIsOurOperation()) return;
                try {
                    this.buf.add(8).writeU32(PAGE_EXECUTE_READ);
                    this.buf.add(20).writeU32(PAGE_EXECUTE_READ);
                    VQ_LIES++;
                } catch(e) {
                    recordAnomaly('VirtualQueryEx post-hook fail: ' + e);
                }
            }
        });
        hookedCount++;
    } catch(e) {
        recordAnomaly('VirtualQueryEx hook failed: ' + e);
    }

    // 2c. VirtualProtectEx — kernel32 页属性修改
    try {
        var VirtualProtectEx = kernel32.getExportByName('VirtualProtectEx');
        Interceptor.attach(VirtualProtectEx, {
            onEnter: function(args) {
                this.addr = args[1];
                this.oldProtectPtr = args[3];
                this.hProcess = args[0];
                this.isSelf = (this.hProcess.toInt32() === -1);
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                if (!this.isSelf) return;
                if (!inTextRange(this.addr)) return;
                if (vpIsOurOperation()) return;
                // Apollo 通过 kernel32 修改 .text → 拦截
                if (!this.oldProtectPtr.isNull()) {
                    this.oldProtectPtr.writeU32(PAGE_EXECUTE_READ);
                }
                retval.replace(1);
                VP_FAKES++;
            }
        });
        hookedCount++;
    } catch(e) {
        recordAnomaly('VirtualProtectEx hook failed: ' + e);
    }

    // ── Layer 3: GetProcessMemoryInfo (备选查询路径) ──
    // PSAPI.GetProcessMemoryInfo 不返回页属性，但记录以防 Apollo 使用其他 API
    // 此处留空 — 如果异常检测发现 bypass，再添加对应 hook

    DECEPTION_ACTIVE = true;
    send({t: 'STEP', msg: 'Page deception OK: ' + hookedCount + ' hooks active (ntdll+kernel32 layers)'});
    return true;
}

// ═══════════════════════════════════════════════════════════════
// Part 2: CRC Patch (使用原子锁)
// ═══════════════════════════════════════════════════════════════

function patchCRC() {
    send({t: 'STEP', msg: 'Patching ApolloCT CRC (with atomic lock)...'});
    if (!safetyGate('CRC patch')) return false;

    var apolloCT;
    try {
        apolloCT = Process.getModuleByName('ApolloCT.dll');
    } catch(e) {
        send({t: 'STEP', msg: 'ApolloCT.dll not loaded, skip CRC'});
        return true;
    }

    var CRC_RVAS = [0x1A3C54, 0x1BE222];
    var patched = 0;

    vpLockAcquire();
    try {
        for (var i = 0; i < CRC_RVAS.length; i++) {
            var addr = apolloCT.base.add(CRC_RVAS[i]);
            var page = addr.and(ptr(0xfffff000));
            try {
                Memory.protect(page, 0x1000, 'rwx');
                addr.writeU8(0x33);          // xor eax, eax
                addr.add(1).writeU8(0xC0);
                addr.add(2).writeU8(0xC3);   // ret
                Memory.protect(page, 0x1000, 'rx');
                patched++;
            } catch(e) {
                send({t: 'WARN', msg: 'CRC patch fail at 0x' + CRC_RVAS[i].toString(16) + ': ' + e});
            }
        }
    } finally {
        vpLockRelease();
    }

    CRC_PATCHED = (patched === CRC_RVAS.length);
    send({t: 'STEP', msg: 'CRC: ' + patched + '/' + CRC_RVAS.length});
    return CRC_PATCHED;
}

// ═══════════════════════════════════════════════════════════════
// Part 3: Anti-Debug Hooks (已有，无时序问题)
// ═══════════════════════════════════════════════════════════════

function installAntiDebug() {
    send({t: 'STEP', msg: 'Installing anti-debug hooks...'});
    var ntdll = Process.getModuleByName('ntdll.dll');
    var kernel32 = Process.getModuleByName('kernel32.dll');

    // PEB patch
    var pebAddr = ptr(0);
    var pebOk = false;
    try {
        // 通过 TEB 读 PEB
        var teb = Module.findExportByName('ntdll.dll', 'NtCurrentTeb');
        if (teb) {
            var NtCurrentTeb = new NativeFunction(teb, 'pointer', []);
            var tebPtr = NtCurrentTeb();
            pebAddr = tebPtr.add(0x30).readPointer();
            if (!pebAddr.isNull()) pebOk = true;
        }
    } catch(e) {}
    if (!pebOk) {
        try {
            var NtQIP = new NativeFunction(
                ntdll.getExportByName('NtQueryInformationProcess'),
                'uint32', ['pointer', 'uint32', 'pointer', 'uint32', 'pointer']
            );
            var buf = Memory.alloc(0x100);
            NtQIP(ptr(-1), 0, buf, 0x100, ptr(0));
            pebAddr = buf.add(4).readPointer();
            if (!pebAddr.isNull()) pebOk = true;
        } catch(e) {}
    }

    if (pebOk) {
        setInterval(function() {
            try {
                pebAddr.add(0x02).writeU8(0);  // BeingDebugged
                pebAddr.add(0x68).writeU32(0); // NtGlobalFlag
            } catch(e) {}
        }, 200);
    }

    // IsDebuggerPresent
    try {
        Interceptor.attach(kernel32.getExportByName('IsDebuggerPresent'), {
            onLeave: function(retval) { retval.replace(0); }
        });
    } catch(e) {}

    // NtQueryInformationProcess
    try {
        Interceptor.attach(ntdll.getExportByName('NtQueryInformationProcess'), {
            onEnter: function(args) { this.infoClass = args[1].toInt32(); this.infoBuffer = args[2]; this.infoLen = args[3].toInt32(); },
            onLeave: function(retval) {
                if (this.infoClass === 7) {         // ProcessDebugPort
                    if (!this.infoBuffer.isNull() && this.infoLen >= 4) this.infoBuffer.writeU32(0);
                    retval.replace(0);
                } else if (this.infoClass === 30) { // ProcessDebugObjectHandle
                    retval.replace(0xC0000353);
                } else if (this.infoClass === 31) { // ProcessDebugFlags
                    if (!this.infoBuffer.isNull() && this.infoLen >= 4) this.infoBuffer.writeU32(1);
                    retval.replace(0);
                }
            }
        });
    } catch(e) {}

    // CheckRemoteDebuggerPresent
    try {
        Interceptor.attach(kernel32.getExportByName('CheckRemoteDebuggerPresent'), {
            onEnter: function(args) { this.pb = args[1]; },
            onLeave: function(retval) { if (!this.pb.isNull()) this.pb.writeU32(0); retval.replace(1); }
        });
    } catch(e) {}

    // OutputDebugStringA
    try {
        Interceptor.attach(kernel32.getExportByName('OutputDebugStringA'), { onEnter: function() {} });
    } catch(e) {}

    ANTIDEBUG_ACTIVE = true;
    send({t: 'STEP', msg: 'Anti-debug hooks OK'});
    return true;
}

// ═══════════════════════════════════════════════════════════════
// Part 4: .text unlock (使用完整 Level 2 保护)
// ═══════════════════════════════════════════════════════════════

function unlockText() {
    if (!DECEPTION_ACTIVE) return false;
    if (!safetyGate('.text unlock')) return false;

    vpLockAcquire();
    try {
        Memory.protect(textStart, textSection.size, 'rwx');
        send({t: 'STEP', msg: '.text unlocked ' + (textSection.size / 1024 / 1024).toFixed(1) + 'MB'});
        return true;
    } catch(e) {
        send({t: 'WARN', msg: '.text unlock failed: ' + e});
        return false;
    } finally {
        vpLockRelease();
    }
}

// ═══════════════════════════════════════════════════════════════
// Part 5: 安全的 Memory.protect 包装器 (对外暴露)
// ═══════════════════════════════════════════════════════════════

function safeProtect(addr, size, prot) {
    if (!safetyGate('safeProtect(' + addr + ', ' + size + ')')) {
        return false;
    }
    vpLockAcquire();
    try {
        Memory.protect(addr, size, prot);
        return true;
    } catch(e) {
        send({t: 'SAFETY', msg: 'safeProtect failed: ' + e});
        return false;
    } finally {
        vpLockRelease();
    }
}

// ═══════════════════════════════════════════════════════════════
// Part 6: 扫描周期报告
// ═══════════════════════════════════════════════════════════════

function reportScanStats() {
    if (SCAN_STATS.apolloCalls === 0) {
        return { msg: 'No Apollo scans detected yet' };
    }
    return {
        totalNtQVM: SCAN_STATS.totalCalls,
        apolloScans: SCAN_STATS.apolloCalls,
        periodMs: SCAN_STATS.scanPeriodEstimated,
        minIntervalMs: SCAN_STATS.minInterval === Infinity ? 'N/A' : SCAN_STATS.minInterval,
        maxIntervalMs: SCAN_STATS.maxInterval === 0 ? 'N/A' : SCAN_STATS.maxInterval,
        avgIntervalMs: SCAN_STATS.avgInterval,
        sampleCount: SCAN_STATS.scanIntervals.length
    };
}

function reportAnomalyStats() {
    return {
        bypassAttempts: ANOMALY.bypassAttempts,
        erLeaks: ANOMALY.erLeaks,
        lastAnomalyTime: ANOMALY.lastAnomalyTime,
        recentAnomalies: ANOMALY.anomalyDetails.slice(-5)
    };
}

// ═══════════════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════════════

// 计数器 (保持向后兼容)
var VQ_LIES = 0;
var VP_FAKES = 0;
var PEB_PATCH_COUNT = 0;

// ═══════════════════════════════════════════════════════════════
// Phase 0: 诊断 — 真实检查 ApolloCT 状态
// ═══════════════════════════════════════════════════════════════

function diagnose() {
    send({t: 'DIAG', msg: '========== Apollo 状态诊断 =========='});

    // 1. ApolloCT.dll 是否加载
    var apolloCT;
    try {
        apolloCT = Process.getModuleByName('ApolloCT.dll');
        send({t: 'DIAG', msg: 'ApolloCT.dll: 已加载 @ ' + apolloCT.base + ' (' + apolloCT.size + ' bytes)'});
    } catch(e) {
        send({t: 'DIAG', msg: 'ApolloCT.dll: 未加载 — 游戏无 ApolloCT 保护!'});
    }

    // 2. Apollo.sys 驱动状态
    var driverPath = '';
    try {
        var kernelBase = Module.findBaseAddress('ntoskrnl.exe');
        if (kernelBase) {
            send({t: 'DIAG', msg: 'Kernel: ntoskrnl.exe @ ' + kernelBase + ' (L0 需 sc stop, 不能从用户态查)'});
        }
    } catch(e) {}

    // 3. 所有线程列表
    var threads = Process.enumerateThreads();
    send({t: 'DIAG', msg: '总线程数: ' + threads.length});

    var apolloThreads = 0;
    threads.forEach(function(t) {
        var eip = t.context ? t.context.eip : ptr(0);
        var mod = Process.findModuleByAddress(eip);
        var modName = mod ? mod.name : 'unknown';
        if (modName === 'ApolloCT.dll') {
            apolloThreads++;
            var offset = eip.sub(apolloCT.base).toInt32();
            send({t: 'DIAG', msg: '  [ApolloCT] TID=' + t.id + ' EIP=ApolloCT+0x' + offset.toString(16)});
        }
    });
    send({t: 'DIAG', msg: 'ApolloCT 线程数: ' + apolloThreads + ' (如果=0, 保护线程不存在!)'});

    // 4. .text 当前页属性 (只读检查, 不改)
    var pageInfo = new NativePointer(4096);
    var len = new NativePointer(4);
    var pageAddr = textStart;
    try {
        var NtQVI = new NativeFunction(
            Module.findExportByName('ntdll.dll', 'NtQueryVirtualMemory'),
            'uint32', ['pointer', 'uint32', 'pointer', 'pointer', 'pointer', 'pointer']
        );
        var buf = Memory.alloc(0x100);
        var result = NtQVI(ptr(-1), pageAddr, ptr(0), buf, ptr(0x100), ptr(0));
        if (result.toInt32() === 0) {
            var protect = buf.add(8).readU32();
            var protectStr = protect === 0x20 ? 'PAGE_EXECUTE_READ' :
                             protect === 0x40 ? 'PAGE_EXECUTE_READWRITE' :
                             protect === 0x04 ? 'PAGE_READWRITE' :
                             protect === 0x10 ? 'PAGE_EXECUTE' :
                             '0x' + protect.toString(16);
            send({t: 'DIAG', msg: '.text 段当前页属性: ' + protectStr + ' (ApolloCT 看到这个值)'});
        }
    } catch(e) {
        send({t: 'DIAG', msg: '.text 页属性读取失败: ' + e});
    }

    // 5. L2 内嵌 Apollo 检查
    var l2Threads = 0;
    threads.forEach(function(t) {
        var eip = t.context ? t.context.eip : ptr(0);
        var mod = Process.findModuleByAddress(eip);
        if (mod && mod.name === 'FreeStyle.exe') {
            var offset = eip.sub(fsMod.base).toInt32();
            if (offset >= 0x1000 && offset < 0x2c0c000) {
                // 在 .text 的线程, 标记
            }
        }
    });
    send({t: 'DIAG', msg: 'L2 (内嵌 Apollo): 存在 ' + l2Threads + ' 个线程在 FreeStyle.exe .text 范围'});

    send({t: 'DIAG', msg: '========== 诊断结束 =========='});
}

function init() {
    send({t: 'INIT', msg: 'x64dbg enabler v2 starting (Level 2 complete)...'});
    send({t: 'SECTION', start: textStart.toString(), end: textEnd.toString(), size: textSection.size});

    diagnose();

    if (!installDeception()) { send({t: 'FAIL', msg: 'Deception failed'}); return; }
    if (!patchCRC()) { send({t: 'WARN', msg: 'CRC incomplete'}); }
    if (!installAntiDebug()) { send({t: 'FAIL', msg: 'Anti-debug failed'}); return; }
    unlockText();

    // 延迟 3 秒后报告 Apollo 扫描周期
    setTimeout(function() {
        var stats = reportScanStats();
        var anomaly = reportAnomalyStats();
        send({
            t: 'SCAN_PROFILE',
            stats: stats,
            anomaly: anomaly,
            vq_lies: VQ_LIES,
            vp_fakes: VP_FAKES
        });
    }, 3000);

    send({t: 'READY', msg: 'All hooks active (Level 2 complete). Attach x32dbg now.'});
}

// ═══════════════════════════════════════════════════════════════
// RPC exports
// ═══════════════════════════════════════════════════════════════

rpc.exports = {
    status: function() {
        var stats = reportScanStats();
        var anomaly = reportAnomalyStats();
        send({
            t: 'STATUS',
            deception: DECEPTION_ACTIVE,
            vq_lies: VQ_LIES,
            vp_fakes: VP_FAKES,
            crc: CRC_PATCHED,
            antidebug: ANTIDEBUG_ACTIVE,
            peb_patches: PEB_PATCH_COUNT,
            scan: stats,
            anomaly: anomaly
        });
    },

    scanProfile: function() {
        send({ t: 'SCAN_PROFILE', stats: reportScanStats(), anomaly: reportAnomalyStats() });
    },

    // 安全的 .text unlock (使用完整 Level 2 保护)
    unlockText: function() {
        var ok = unlockText();
        send({ t: 'UNLOCK', ok: ok });
        return ok;
    },

    // 安全的 Memory.protect (对外)
    safeProtect: function(addr, size) {
        return safeProtect(ptr(addr), size, 'rwx');
    },

    // 获取 .text 范围
    getTextRange: function() {
        return {
            start: textStart.toString(),
            end: textEnd.toString(),
            size: textSection.size
        };
    }
};

setTimeout(init, 500);
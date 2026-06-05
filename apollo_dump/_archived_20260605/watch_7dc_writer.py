# watch_7dc_writer.py
# P0: 追踪谁把 [subObj+0x7DC] 清零/覆盖
# 策略：sprintf hook 捕获 subObj 地址 → MemoryAccessMonitor 监控写入 → 记录调用栈
#
# 用法：
#   1. 启动脚本，进房间（触发 sprintf，捕获 subObj 地址）
#   2. 进练习场，观察 write 事件和调用栈
#   3. 查日志定位清零源头
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'watch_7dc_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461   # 美丽梦想(静态, pak767)
DST_IC = 50125711   # 紫色超赛(动态, pak768)

def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_TEMPLATE = r"""
'use strict';

var SRC_IC = __SRC_IC__;
var DST_IC = __DST_IC__;
var base = ptr('0x400000');

var sprintfCount = 0;
var phase = 'INJECTED';

// 目标监控地址（sprintf 捕获后设置）
var subObjPtr = null;       // [outer+0x164]
var watchAddr = null;       // subObj + 0x7DC
var monitoring = false;
var lastVal = null;

// 收集到的写入事件
var writeLog = [];

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
    }
}

function hexAddr(p) {
    return '0x' + p.toString(16);
}

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function getBacktrace(ctx) {
    // Thread.backtrace 可能在某些环境不可用，用 Try catch
    try {
        return Thread.backtrace(ctx, Backtracer.ACCURATE)
            .map(function(addr) {
                var mod = '?';
                try {
                    var m = Process.findModuleByAddress(addr);
                    if (m) mod = m.name + '+0x' + addr.sub(m.base).toString(16);
                } catch(e) {}
                return hexAddr(addr) + '(' + mod + ')';
            });
    } catch(e) {
        // Fallback: 手动遍历栈帧
        try {
            return Thread.backtrace(ctx, Backtracer.FUZZY)
                .map(function(addr) {
                    return hexAddr(addr);
                });
        } catch(e2) {
            return ['backtrace_failed'];
        }
    }
}

// ==========================================
// 1. sprintf hook — 捕获 subObj 地址 + 启动写入监控
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfCount++;

            var marker = '';
            if (ic === SRC_IC) marker = ' <== SRC_IC';
            else if (ic === DST_IC) marker = ' <== DST_IC';

            // 尝试读取 subObj
            var ebp = this.context.ebp;
            try {
                var outerPtr = ebp.sub(0x478c).readPointer();
                subObjPtr = outerPtr.add(0x164).readPointer();
                watchAddr = subObjPtr.add(0x7DC);
                var currentVal = watchAddr.readU32();
                lastVal = currentVal;

                send({
                    t: 'sprintf',
                    n: sprintfCount,
                    ic: ic,
                    marker: marker,
                    phase: phase,
                    subObj: hexAddr(subObjPtr),
                    val7DC: currentVal,
                    match: currentVal === ic
                });

                // 首次捕获到地址后启动写入监控
                if (!monitoring && subObjPtr) {
                    startWriteMonitor();
                }
            } catch(e) {
                send({t: 'sprintf', n: sprintfCount, ic: ic, marker: marker, phase: phase, error: e.toString()});
            }

            if (sprintfCount === 1) setPhase('ROOM_LOAD');
            else if (sprintfCount === 2) setPhase('PRACTICE_LOAD');

        } catch(e) {
            send({t: 'error', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 2. 写入监控 — 用 MemoryAccessMonitor 监控 +0x7DC 所在页面
// ==========================================
function startWriteMonitor() {
    if (monitoring) return;
    monitoring = true;

    // 监控 0x7DC 所在的 4 字节（对齐到4字节边界）
    // MemoryAccessMonitor 要求传入 {base, size} 数组
    try {
        // 监控一个较小的范围：目标地址前后 256 字节
        // 这样既能捕获精确写入，又不会太影响性能
        var monitorBase = watchAddr.and(ptr('0xFFFFFF00'));  // 对齐到256
        var monitorSize = 256;

        MemoryAccessMonitor.enable(
            [{base: monitorBase, size: monitorSize}],
            {
                onStateChanged: function(event) {
                    // event: {address, type:'read'|'write'|'execute', from, to}
                    // 我们关心的是写入 watchAddr 附近
                    try {
                        var addr = event.address;
                        var diff = addr.sub(watchAddr).toInt32();

                        // 只关心 watchAddr 附近的写入
                        if (diff >= -16 && diff <= 16) {
                            var newVal = watchAddr.readU32();
                            var bt = getBacktrace(event.from || this.context);

                            var evt = {
                                t: 'write',
                                phase: phase,
                                writeAddr: hexAddr(addr),
                                target: hexAddr(watchAddr),
                                diff: diff,
                                oldVal: lastVal,
                                newVal: newVal,
                                isZero: newVal === 0,
                                isSRC: newVal === SRC_IC,
                                isDST: newVal === DST_IC,
                                backtrace: bt
                            };

                            writeLog.push(evt);
                            lastVal = newVal;
                            send(evt);
                        }
                    } catch(e) {
                        send({t: 'write_error', msg: e.toString()});
                    }
                }
            }
        );
        send({t: 'step', msg: 'MemoryAccessMonitor enabled @ ' + hexAddr(watchAddr)});
    } catch(e) {
        send({t: 'step', msg: 'MemoryAccessMonitor FAILED: ' + e + ', falling back to polling'});

        // Fallback: 高频轮询 + 调用栈捕获
        startPollingFallback();
    }
}

// ==========================================
// 3. Fallback: 高频轮询 + 立即抓调用栈
// ==========================================
function startPollingFallback() {
    send({t: 'step', msg: 'Using polling fallback (50ms)'});

    var pollCount = 0;
    var pollInterval = setInterval(function() {
        if (!watchAddr) return;

        try {
            var val = watchAddr.readU32();
            pollCount++;

            if (lastVal !== val) {
                // 值变了！立即抓调用栈
                // 注意：这里抓的是轮询线程的栈，不是写入线程的栈
                // 但至少能记录变化时间和值
                var bt = getBacktrace(this.context);

                send({
                    t: 'poll_change',
                    phase: phase,
                    pollN: pollCount,
                    old: lastVal,
                    new: val,
                    isZero: val === 0,
                    isSRC: val === SRC_IC,
                    isDST: val === DST_IC,
                    note: 'polling detected (writer stack NOT captured)',
                    backtrace: bt
                });

                lastVal = val;
            }
        } catch(e) {}
    }, 50);  // 50ms 高频轮询

    send({t: 'step', msg: 'polling started'});
}

// ==========================================
// 4. 额外方案：hook memcpy/memset 捕获批量清零
// ==========================================
var msvcrt = null;
try { msvcrt = Process.getModuleByName('msvcrt.dll'); } catch(e) {}
try { if (!msvcrt) msvcrt = Process.getModuleByName('MSVCR100.dll'); } catch(e) {}

if (msvcrt) {
    var memcpyAddr = msvcrt.getExportByName('memcpy');
    var memsetAddr = msvcrt.getExportByName('memset');

    if (memcpyAddr) {
        Interceptor.attach(memcpyAddr, {
            onEnter: function(args) {
                if (!watchAddr) return;
                try {
                    var dst = args[0];
                    var size = args[2].toInt32();
                    if (size < 4 || size > 0x10000) return;

                    var diff = dst.sub(watchAddr).toInt32();
                    // 检查写入范围是否覆盖 +0x7DC
                    if (diff >= -size && diff <= 16) {
                        var srcVal = args[1].readU32();
                        send({
                            t: 'memcpy',
                            phase: phase,
                            dst: hexAddr(dst),
                            size: size,
                            src_first4: srcVal,
                            covers7DC: (diff <= 0 && diff + size > 0),
                            backtrace: getBacktrace(this.context)
                        });
                    }
                } catch(e) {}
            }
        });
        send({t: 'step', msg: 'memcpy hook ready'});
    }

    if (memsetAddr) {
        Interceptor.attach(memsetAddr, {
            onEnter: function(args) {
                if (!watchAddr) return;
                try {
                    var dst = args[0];
                    var val = args[1].toInt32();
                    var size = args[2].toInt32();
                    if (size < 4 || size > 0x10000) return;

                    var diff = dst.sub(watchAddr).toInt32();
                    // 检查清零范围是否覆盖 +0x7DC
                    if (diff >= -size && diff <= 16) {
                        send({
                            t: 'memset',
                            phase: phase,
                            dst: hexAddr(dst),
                            val: val,
                            size: size,
                            covers7DC: (diff <= 0 && diff + size > 0),
                            isZero: val === 0,
                            backtrace: getBacktrace(this.context)
                        });
                    }
                } catch(e) {}
            }
        });
        send({t: 'step', msg: 'memset hook ready'});
    }
}

// ==========================================
// 5. CreateFileA/W — 监控练习场阶段文件访问
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var cfCount = 0;

var CreateFileA = kernel32.getExportByName('CreateFileA');
Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 512);
            if (path.indexOf('50125') >= 0 || path.indexOf('.bml') >= 0) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, short: short, api: 'A', phase: phase});
            }
        } catch(e) {}
    }
});

var CreateFileW = kernel32.getExportByName('CreateFileW');
Interceptor.attach(CreateFileW, {
    onEnter: function(args) {
        try {
            var pathBuf = args[0];
            var path = '';
            for (var i = 0; i < 256; i++) {
                var ch = pathBuf.add(i * 2).readU16();
                if (ch === 0) break;
                path += String.fromCharCode(ch);
            }
            if (path.indexOf('50125') >= 0 || path.indexOf('.bml') >= 0) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, short: short, api: 'W', phase: phase});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA/W hooks ready'});

// ==========================================
// 6. RPC 接口
// ==========================================
rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            subObj: subObjPtr ? hexAddr(subObjPtr) : null,
            watchAddr: watchAddr ? hexAddr(watchAddr) : null,
            currentVal: lastVal,
            monitoring: monitoring,
            writeEventCount: writeLog.length
        });
    },
    writes: function() {
        var lines = [];
        for (var i = 0; i < writeLog.length; i++) {
            var w = writeLog[i];
            lines.push('#' + i + ' ' + hexAddr(w.writeAddr) + ' -> ' + w.newVal +
                       ' (was ' + w.oldVal + ') bt=' + w.backtrace.join(' <- '));
        }
        return lines.join('\n');
    },
    // 手动设置 subObj 地址（如果 sprintf 还没触发）
    setTarget: function(addrHex) {
        try {
            subObjPtr = ptr(addrHex);
            watchAddr = subObjPtr.add(0x7DC);
            lastVal = watchAddr.readU32();
            if (!monitoring) startWriteMonitor();
            return 'OK: watching ' + hexAddr(watchAddr) + ' val=' + lastVal;
        } catch(e) {
            return 'ERROR: ' + e;
        }
    }
};

send({t: 'ready', src: SRC_IC, dst: DST_IC});
"""

JS_CODE = (
    JS_TEMPLATE
    .replace('__SRC_IC__', str(SRC_IC))
    .replace('__DST_IC__', str(DST_IC))
)

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe not running')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log('=== Watch +0x7DC Writer ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC} 美丽梦想(静态, pak767)')
    log(f'DST: {DST_IC} 紫色超赛(动态, pak768)')
    log(f'Target: [subObj+0x7DC]')
    log(f'Log: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'step':
                log(f'  [setup] {p["msg"]}')

            elif t == 'ready':
                log(f'  [ready] SRC={p["src"]} DST={p["dst"]}')

            elif t == 'phase':
                log(f'')
                log(f'[phase] {p["from"]} -> {p["to"]}')
                log('')

            elif t == 'sprintf':
                ic = p.get('ic', '?')
                marker = p.get('marker', '')
                if 'subObj' in p:
                    match = 'MATCH' if p.get('match') else 'MISMATCH'
                    log(f'[sprintf] #{p["n"]} ic={ic}{marker} val7DC={p["val7DC"]}({match}) subObj={p["subObj"]} phase={p["phase"]}')
                else:
                    log(f'[sprintf] #{p["n"]} ic={ic}{marker} phase={p["phase"]} err={p.get("error","")}')

            elif t == 'write':
                # ★ 核心输出：捕获到写入事件
                marker = ''
                if p.get('isZero'): marker = ' <== ZEROED!'
                elif p.get('isSRC'): marker = ' <== SRC_IC'
                elif p.get('isDST'): marker = ' <== DST_IC'

                log(f'')
                log(f'!!! WRITE DETECTED @ {p["phase"]} !!!')
                log(f'  addr={p["writeAddr"]} target={p["target"]} diff={p["diff"]}')
                log(f'  {p["oldVal"]} -> {p["newVal"]}{marker}')
                log(f'  backtrace:')
                for i, frame in enumerate(p.get('backtrace', [])[:15]):
                    log(f'    [{i}] {frame}')
                log('')

            elif t == 'poll_change':
                marker = ''
                if p.get('isZero'): marker = ' <== ZEROED!'
                elif p.get('isSRC'): marker = ' <== SRC_IC'
                elif p.get('isDST'): marker = ' <== DST_IC'

                log(f'')
                log(f'!!! POLL CHANGE @ {p["phase"]} !!!')
                log(f'  poll#{p["pollN"]}: {p["old"]} -> {p["new"]}{marker}')
                log(f'  NOTE: writer stack NOT captured (polling fallback)')
                log('')

            elif t == 'memcpy':
                log(f'[memcpy] dst={p["dst"]} size={p["size"]} src_val={p["src_first4"]} covers7DC={p["covers7DC"]} phase={p["phase"]}')
                if p.get('backtrace'):
                    for i, frame in enumerate(p['backtrace'][:8]):
                        log(f'    [{i}] {frame}')

            elif t == 'memset':
                marker = ' <== ZERO!' if p.get('isZero') else ''
                log(f'[memset] dst={p["dst"]} val={p["val"]}{marker} size={p["size"]} covers7DC={p["covers7DC"]} phase={p["phase"]}')
                if p.get('backtrace'):
                    for i, frame in enumerate(p['backtrace'][:8]):
                        log(f'    [{i}] {frame}')

            elif t == 'write_error':
                log(f'  [write_error] {p["msg"]}')

            elif t == 'file':
                log(f'[file] {p["short"]} ({p["api"]}) phase={p["phase"]}')

            elif t == 'error':
                log(f'  [error] {p["msg"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")} line={msg.get("lineNumber", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('流程:')
    log('  1. 进房间 -> sprintf 捕获 subObj 地址，自动启动写入监控')
    log('  2. 进练习场 -> 观察 WRITE DETECTED / memset / memcpy 事件')
    log('  3. 关注调用栈，定位清零源头')
    log('')
    log('命令: status | writes | set <addr> | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip()
            if cmd.lower() in ('quit', 'q', 'exit'):
                break
            elif cmd.lower() == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd.lower() == 'writes':
                result = script.exports_sync.writes()
                if result:
                    for line in result.split('\n'):
                        log(f'  {line}')
                else:
                    log('  (no writes captured yet)')
            elif cmd.lower().startswith('set '):
                addr = cmd.split()[1]
                result = script.exports_sync.setTarget(addr)
                log(f'  {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('Done.')

if __name__ == '__main__':
    main()

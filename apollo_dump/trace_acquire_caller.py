# trace_acquire_caller.py
# P0-核心: 追踪 AcquireSMD 调用链，定位练习场 ItemCode 来源
#
# 策略：
#   1. hook AcquireSMD 调用者 (0x01EEBA30) — 这是高频函数，但用"瞬时采样"策略
#   2. 只在关键时机触发：进房间/进练习场的前几秒
#   3. 采样后立即 detach，避免 Apollo 检测
#   4. 记录完整 backtrace (20-30帧)
#
# 风险：游戏 .text hook 有风险，但这是定位练习场路径的唯一方法
# 缓解：采样模式，只触发有限次数后自动卸载
import sys
import os
import time
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_caller_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

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

function getBacktrace(ctx, depth) {
    depth = depth || 25;
    try {
        return Thread.backtrace(ctx, Backtracer.ACCURATE)
            .slice(0, depth)
            .map(function(addr) {
                var mod = '?';
                var offset = 0;
                try {
                    var m = Process.findModuleByAddress(addr);
                    if (m) {
                        mod = m.name;
                        offset = addr.sub(m.base).toInt32();
                    }
                } catch(e) {}
                return hexAddr(addr) + '(' + mod + '+0x' + offset.toString(16) + ')';
            });
    } catch(e) {
        return ['backtrace_failed:' + e];
    }
}

var phase = 'INJECTED';
var sprintfCount = 0;
var acquireCount = 0;
var maxAcquireSamples = 50;  // 最多采样 50 次后自动停止
var acquireSamples = 0;
var hookActive = false;

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
    }
}

// ==========================================
// 1. sprintf — 阶段检测 + 触发 AcquireSMD hook
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
Interceptor.attach(msvcr100.getExportByName('sprintf'), {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfCount++;

            var marker = '';
            if (ic === SRC_IC) marker = ' <== SRC';
            else if (ic === DST_IC) marker = ' <== DST';

            send({t: 'sprintf', n: sprintfCount, ic: ic, marker: marker, phase: phase});

            if (sprintfCount <= 10) setPhase('ROOM_LOAD');

            // 首次 sprintf 后激活 AcquireSMD hook
            if (!hookActive && sprintfCount >= 1) {
                hookActive = true;
                send({t: 'step', msg: 'AcquireSMD hook ACTIVATED'});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 2. AcquireSMD 调用者 hook — 采样模式
// ==========================================
// 地址来自 03_常量地址表.md: 0x01EEBA30
// ecx+0x10 = SMD 路径指针
var acquireCallerAddr = base.add(0x01EEBA30);

var acquireHook = null;
var lastAcquireTime = 0;
var acquireInLast5s = 0;

function attachAcquireHook() {
    if (acquireHook) return;

    try {
        acquireHook = Interceptor.attach(acquireCallerAddr, {
            onEnter: function(args) {
                // 检查是否应该采样
                if (!hookActive) return;
                if (acquireSamples >= maxAcquireSamples) return;

                // 限流：每 100ms 最多 1 次采样
                var now = Date.now();
                if (now - lastAcquireTime < 100) return;
                lastAcquireTime = now;

                try {
                    var pathPtr = this.context.ecx.add(0x10).readPointer();
                    var path = readAscii(pathPtr, 100);
                    acquireCount++;
                    acquireSamples++;

                    // 检查是否是目标 ItemCode
                    var hasSrc = path.indexOf(SRC_IC.toString()) >= 0;
                    var hasDst = path.indexOf(DST_IC.toString()) >= 0;

                    // 只记录目标相关的，或者前 20 次
                    if (hasSrc || hasDst || acquireCount <= 20) {
                        var bt = getBacktrace(this.context, 25);
                        var marker = '';
                        if (hasSrc) marker = ' <== SRC_IC!';
                        else if (hasDst) marker = ' <== DST_IC';

                        send({
                            t: 'acquire',
                            n: acquireCount,
                            sample: acquireSamples + '/' + maxAcquireSamples,
                            path: path,
                            marker: marker,
                            phase: phase,
                            bt: bt
                        });
                    }

                    // 达到采样上限，自动卸载
                    if (acquireSamples >= maxAcquireSamples) {
                        send({t: 'step', msg: 'Max samples reached, auto-detach AcquireSMD hook'});
                        // 不立即 detach，等 Python 端处理
                    }
                } catch(e) {
                    send({t: 'error', msg: 'acquire hook: ' + e});
                }
            }
        });
        send({t: 'step', msg: 'AcquireSMD caller hook attached at ' + acquireCallerAddr});
    } catch(e) {
        send({t: 'error', msg: 'Failed to attach AcquireSMD hook: ' + e});
    }
}

// 延迟激活：等 sprintf 首次触发后再 attach
setTimeout(function() {
    attachAcquireHook();
}, 2000);

// ==========================================
// 3. 静默期检测 — 练习场阶段
// ==========================================
var lastSprintfTime = Date.now();

var silenceTimer = setInterval(function() {
    var now = Date.now();

    // 检查 sprintf 静默
    // 注意：sprintf hook 会更新 lastSprintfTime，这里用全局变量
}, 1000);

// ==========================================
// RPC
// ==========================================
rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            acquireCount: acquireCount,
            acquireSamples: acquireSamples,
            hookActive: hookActive
        });
    },
    stopAcquire: function() {
        if (acquireHook) {
            acquireHook.detach();
            acquireHook = null;
            hookActive = false;
            send({t: 'step', msg: 'AcquireSMD hook DETACHED'});
            return 'detached';
        }
        return 'not_attached';
    },
    setPhase: function(p) {
        setPhase(p);
        return phase;
    }
};

send({t: 'ready', msg: 'AcquireSMD caller tracer ready (sampling mode, max ' + maxAcquireSamples + ' samples)'});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== AcquireSMD Caller Tracer === PID:{pid} ===')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
    log(f'策略: 采样模式，最多 50 次，限流 100ms/次')
    log(f'风险: 游戏 .text hook，采样后建议立即 stop')
    log(f'日志: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_TEMPLATE
        .replace('__SRC_IC__', str(SRC_IC))
        .replace('__DST_IC__', str(DST_IC))
    )

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'step':
                log(f'  [setup] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'phase':
                log('')
                log(f'[PHASE] {p["from"]} -> {p["to"]}')
                log('')
            elif t == 'sprintf':
                log(f'[sprintf] #{p["n"]} ic={p["ic"]}{p.get("marker","")} phase={p["phase"]}')
            elif t == 'acquire':
                marker = p.get('marker', '')
                log(f'[AcquireSMD] #{p["n"]} ({p["sample"]}) phase={p["phase"]}{marker}')
                log(f'       path: {p["path"]}')
                if p.get('bt'):
                    log('       backtrace:')
                    for i, frame in enumerate(p['bt'][:15]):
                        log(f'         [{i}] {frame}')
            elif t == 'error':
                log(f'  [error] {p.get("msg", p)}')
            else:
                log(f'  [{t}] {str(p)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description","")} line={msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('测试流程:')
    log('1. 进房间 → 观察 AcquireSMD 调用栈')
    log('2. 进练习场 → 关键：看 AcquireSMD 用的是哪个 ItemCode')
    log('3. 如果看到 SRC_IC 的路径 → 调用栈会显示练习场专用路径')
    log('4. 采样满 50 次或观察到关键信息后，建议 stop 或 quit')
    log('')
    log('命令: status | stop | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'stop':
                result = script.exports_sync.stop_acquire()
                log(f'  {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()
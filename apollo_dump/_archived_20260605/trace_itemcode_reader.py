# trace_itemcode_reader.py
# P1: 找装备数据缓存位置 — 追踪谁在读 ItemCode
#
# 核心思路：
#   1. 已知 12 个地址含 SRC_IC (50125461)
#   2. 练习场阶段这些地址值不变，但发型恢复
#   3. 说明练习场从其他地方读取 ItemCode
#   4. 用硬件断点追踪这些地址的读取操作
#
# 问题：Frida 没有 HW breakpoint API，需要替代方案
# 替代：监控 CreateFileA/W 的路径参数，看练习场阶段谁在构造原始 ItemCode 的路径
#
# 安全：只 hook 系统 DLL
import sys
import os
import time
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'itemcode_reader_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var SRC_IC_STR = SRC_IC.toString();  // "50125461"

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

function readUnicode(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i * 2).readU16();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function getBacktrace(ctx, depth) {
    depth = depth || 15;
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
var lastSprintfTime = 0;

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
    }
}

// ==========================================
// 1. sprintf — 阶段检测
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
Interceptor.attach(msvcr100.getExportByName('sprintf'), {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfCount++;
            lastSprintfTime = Date.now();

            var marker = '';
            if (ic === SRC_IC) marker = ' <== SRC';
            else if (ic === DST_IC) marker = ' <== DST';

            send({t: 'sprintf', n: sprintfCount, ic: ic, marker: marker, phase: phase});

            if (sprintfCount <= 10) setPhase('ROOM_LOAD');
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 2. CreateFileA — 捕获包含 ItemCode 的路径
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var cfCount = 0;

Interceptor.attach(kernel32.getExportByName('CreateFileA'), {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 512);

            // 检查是否包含目标 ItemCode
            var hasSrc = path.indexOf(SRC_IC_STR) >= 0;
            var hasDst = path.indexOf(DST_IC.toString()) >= 0;
            var hasBml = path.indexOf('.bml') >= 0 || path.indexOf('.BML') >= 0;
            var hasSmd = path.indexOf('.smd') >= 0 || path.indexOf('.SMD') >= 0;
            var hasCustomize = path.indexOf('customize') >= 0;

            if (hasSrc || hasDst || hasBml || hasSmd || hasCustomize) {
                cfCount++;
                var bt = getBacktrace(this.context, 20);

                send({
                    t: 'file',
                    n: cfCount,
                    api: 'A',
                    path: path,
                    hasSrc: hasSrc,
                    hasDst: hasDst,
                    phase: phase,
                    bt: bt.slice(0, 10)  // 前10帧
                });
            }
        } catch(e) {}
    }
});

Interceptor.attach(kernel32.getExportByName('CreateFileW'), {
    onEnter: function(args) {
        try {
            var path = readUnicode(args[0], 256);

            var hasSrc = path.indexOf(SRC_IC_STR) >= 0;
            var hasDst = path.indexOf(DST_IC.toString()) >= 0;
            var hasBml = path.indexOf('.bml') >= 0 || path.indexOf('.BML') >= 0;
            var hasSmd = path.indexOf('.smd') >= 0 || path.indexOf('.SMD') >= 0;
            var hasCustomize = path.indexOf('customize') >= 0;

            if (hasSrc || hasDst || hasBml || hasSmd || hasCustomize) {
                cfCount++;
                var bt = getBacktrace(this.context, 20);

                send({
                    t: 'file',
                    n: cfCount,
                    api: 'W',
                    path: path,
                    hasSrc: hasSrc,
                    hasDst: hasDst,
                    phase: phase,
                    bt: bt.slice(0, 10)
                });
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA/W hooks ready (with backtrace)'});

// ==========================================
// 3. 静默期检测
// ==========================================
var silenceTimer = setInterval(function() {
    var now = Date.now();
    var silenceMs = now - lastSprintfTime;

    if (silenceMs > 5000 && sprintfCount > 0 && phase !== 'PRACTICE') {
        setPhase('PRACTICE');
    }
}, 1000);
send({t: 'step', msg: 'silence detector started'});

// ==========================================
// 4. 内存扫描 — 练习场阶段重新扫描
// ==========================================
function scanForItemCode(target) {
    var pattern = target.toString(16);
    while (pattern.length < 8) pattern = '0' + pattern;
    var bytes = [];
    for (var b = 0; b < 4; b++) {
        var byteStr = pattern.substr(6 - b * 2, 2);
        bytes.push(byteStr);
    }
    var searchPattern = bytes.join(' ');

    var results = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 0x100 || r.size > 0x2000000) continue;
        try {
            var matches = Memory.scanSync(r.base, r.size, searchPattern);
            for (var j = 0; j < matches.length; j++) {
                results.push(hexAddr(matches[j].address));
            }
        } catch(e) {}
    }
    return results;
}

// ==========================================
// RPC
// ==========================================
rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            fileCount: cfCount
        });
    },
    scanSrc: function() {
        return JSON.stringify(scanForItemCode(SRC_IC));
    },
    scanDst: function() {
        return JSON.stringify(scanForItemCode(DST_IC));
    },
    setPhase: function(p) {
        setPhase(p);
        return phase;
    }
};

send({t: 'ready', msg: 'ItemCode reader tracer ready'});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== ItemCode Reader Tracer === PID:{pid} ===')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
    log(f'目标: 追踪练习场阶段谁在读取原始 ItemCode')
    log(f'方法: 监控 CreateFileA/W 路径参数 + 20帧调用栈')
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
            elif t == 'file':
                marker = ''
                if p['hasSrc']: marker = ' <== SRC_IC in path!'
                elif p['hasDst']: marker = ' <== DST_IC in path'
                log(f'[file] #{p["n"]} ({p["api"]}) phase={p["phase"]}{marker}')
                log(f'       path: {p["path"]}')
                if p.get('bt'):
                    for i, frame in enumerate(p['bt'][:5]):
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
    log('1. 进房间 → 观察文件路径和调用栈')
    log('2. 进练习场 → 关键：看有没有含 SRC_IC 的路径')
    log('3. 如果有 → 调用栈会显示谁在构造这个路径')
    log('')
    log('命令: status | scansrc | scandst | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'scansrc':
                result = script.exports_sync.scan_src()
                log(f'  SRC_IC addresses: {result[:100]}...' if len(result) > 10 else f'  {result}')
            elif cmd == 'scandst':
                result = script.exports_sync.scan_dst()
                log(f'  DST_IC addresses: {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()
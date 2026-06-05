# hook_sprintf_context.py
# 监控 sprintf 调用的完整上下文，尝试找出练习场阶段的数据来源
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'sprintf_context_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var sprintfCount = 0;
var phase = 'INJECTED';

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
    }
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

function hexAddr(p) {
    return '0x' + p.toString(16);
}

// ==========================================
// sprintf hook — 记录完整上下文
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            sprintfCount++;

            // 记录调用栈
            var stackTrace = [];
            try {
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                for (var i = 0; i < Math.min(bt.length, 8); i++) {
                    var addr = bt[i];
                    var m = Process.findModuleByAddress(addr);
                    var modName = m ? m.name : '?';
                    var rva = m ? hexAddr(addr.sub(m.base)) : hexAddr(addr);
                    stackTrace.push(modName + '+' + rva);
                }
            } catch(e) {}

            // 记录寄存器状态
            var regs = {
                eax: hexAddr(this.context.eax),
                ecx: hexAddr(this.context.ecx),
                edx: hexAddr(this.context.edx),
                ebx: hexAddr(this.context.ebx),
                esp: hexAddr(this.context.esp),
                ebp: hexAddr(this.context.ebp)
            };

            // 尝试读取栈上附近的值
            var stackNearby = [];
            try {
                var esp = this.context.esp;
                for (var i = 0; i < 16; i++) {
                    var val = esp.add(i * 4).readU32();
                    stackNearby.push(hexAddr(val));
                }
            } catch(e) {}

            var marker = '';
            if (itemCode === SRC_IC) marker = ' <== SRC_IC';
            else if (itemCode === DST_IC) marker = ' <== DST_IC';

            send({
                t: 'sprintf',
                n: sprintfCount,
                ic: itemCode,
                marker: marker,
                fmt: fmt,
                phase: phase,
                stackTrace: stackTrace,
                regs: regs,
                stackNearby: stackNearby
            });

            // 阶段推断
            if (sprintfCount === 1) setPhase('ROOM_LOAD');
            else if (sprintfCount === 2) setPhase('PRACTICE_LOAD');

        } catch(e) {
            send({t: 'error', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'sprintf context hook ready'});

// ==========================================
// CreateFileA/W — 监控文件访问
// ==========================================
var cfCount = 0;
var kernel32 = Process.getModuleByName('kernel32.dll');

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

send({t: 'ready', src: SRC_IC, dst: DST_IC});

rpc.exports = {
    status: function() {
        return JSON.stringify({phase: phase, count: sprintfCount});
    }
};
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
    log('=== Sprintf Context Monitor ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
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
                log(f'')

            elif t == 'sprintf':
                log(f'')
                log(f'[sprintf] #{p["n"]} ic={p["ic"]}{p["marker"]} fmt="{p["fmt"]}" phase={p["phase"]}')
                log(f'  backtrace:')
                for i, bt in enumerate(p.get('stackTrace', [])):
                    log(f'    [{i}] {bt}')
                log(f'  regs: eax={p["regs"]["eax"]} ecx={p["regs"]["ecx"]} ebx={p["regs"]["ebx"]}')
                log(f'  stack: {", ".join(p.get("stackNearby", [])[:8])}')

            elif t == 'file':
                log(f'[file] {p["short"]} ({p["api"]}) phase={p["phase"]}')

            elif t == 'error':
                log(f'  [error] {p["msg"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Instructions:')
    log('  1. Enter room')
    log('  2. Enter practice')
    log('  3. Observe backtrace differences between room and practice')
    log('')
    log('Commands: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('Done.')

if __name__ == '__main__':
    main()
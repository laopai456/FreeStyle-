# monitor_itemcode_fields.py
# 监控对象字段中的 ItemCode 变化，观察练习场阶段是否被覆盖
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'itemcode_monitor_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var monitoredObjects = [];
var lastValues = {};

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

// ==========================================
// sprintf hook — 记录对象地址
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

            var ebp = this.context.ebp;

            // 扫描栈上的对象指针
            var foundObjs = [];
            for (var off = -0x200; off <= 0x20; off += 4) {
                try {
                    var ptrVal = ebp.add(off).readU32();
                    if (ptrVal > 0x10000 && ptrVal < 0x70000000) {
                        var p = ptr(ptrVal);
                        for (var o2 = 0; o2 < 0x300; o2 += 4) {
                            try {
                                var v2 = p.add(o2).readU32();
                                if (v2 === SRC_IC || v2 === DST_IC) {
                                    foundObjs.push({
                                        addr: hexAddr(p),
                                        offset: '0x' + o2.toString(16),
                                        value: v2
                                    });
                                    // 加入监控列表
                                    var key = hexAddr(p) + '_' + o2;
                                    if (!monitoredObjects.find(function(o) { return o.key === key; })) {
                                        monitoredObjects.push({
                                            key: key,
                                            addr: p,
                                            offset: o2,
                                            src: 'sprintf#' + sprintfCount
                                        });
                                    }
                                }
                            } catch(e) {}
                        }
                    }
                } catch(e) {}
            }

            send({
                t: 'sprintf',
                n: sprintfCount,
                ic: ic,
                marker: marker,
                phase: phase,
                objects: foundObjs
            });

            // 阶段推断
            if (sprintfCount === 1) setPhase('ROOM_LOAD');
            else if (sprintfCount === 2) setPhase('PRACTICE_LOAD');

        } catch(e) {
            send({t: 'error', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 定时监控对象字段
// ==========================================
var monitorInterval = setInterval(function() {
    if (monitoredObjects.length === 0) return;

    var changes = [];
    for (var i = 0; i < monitoredObjects.length; i++) {
        var obj = monitoredObjects[i];
        try {
            var val = obj.addr.add(obj.offset).readU32();
            var key = obj.key;
            if (lastValues[key] !== val) {
                var oldVal = lastValues[key] || 'N/A';
                changes.push({
                    addr: hexAddr(obj.addr),
                    offset: '0x' + obj.offset.toString(16),
                    old: oldVal,
                    new: val,
                    src: obj.src
                });
                lastValues[key] = val;
            }
        } catch(e) {}
    }

    if (changes.length > 0) {
        send({t: 'change', phase: phase, changes: changes});
    }
}, 500);  // 每 500ms 检查一次

send({t: 'step', msg: 'object monitor started (500ms interval)'});

// ==========================================
// CreateFileA/W — 监控 BML 访问
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
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            monitoredCount: monitoredObjects.length
        });
    },
    listObjects: function() {
        var list = [];
        for (var i = 0; i < monitoredObjects.length; i++) {
            var obj = monitoredObjects[i];
            try {
                var val = obj.addr.add(obj.offset).readU32();
                list.push(hexAddr(obj.addr) + '+0x' + obj.offset.toString(16) + ' = ' + val);
            } catch(e) {
                list.push(hexAddr(obj.addr) + '+0x' + obj.offset.toString(16) + ' = ERROR');
            }
        }
        return list.join('\n');
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
    log('=== ItemCode Field Monitor ===')
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
                objs = p.get('objects', [])
                objInfo = ''
                if objs:
                    objInfo = ' objects=' + str(len(objs))
                log(f'[sprintf] #{p["n"]} ic={p["ic"]}{p["marker"]} phase={p["phase"]}{objInfo}')
                for obj in objs[:3]:  # 只显示前3个
                    log(f'    {obj["addr"]}+{obj["offset"]} = {obj["value"]}')

            elif t == 'change':
                log(f'')
                log(f'=== FIELD CHANGE @ {p["phase"]} ===')
                for c in p['changes']:
                    marker = ''
                    if c['new'] == SRC_IC:
                        marker = ' <== SRC_IC'
                    elif c['new'] == DST_IC:
                        marker = ' <== DST_IC'
                    log(f'  {c["addr"]}+{c["offset"]}: {c["old"]} -> {c["new"]}{marker} (from {c["src"]})')
                log('')

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
    log('  1. Enter room -> observe sprintf and objects')
    log('  2. Enter practice -> watch for FIELD CHANGE')
    log('  3. Exit practice -> watch for FIELD CHANGE')
    log('')
    log('Commands: status | list | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'list':
                objs = script.exports_sync.list_objects()
                log(f'  Monitored objects:')
                for line in objs.split('\n'):
                    log(f'    {line}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('Done.')

if __name__ == '__main__':
    main()
"""
trace_chain.py — Hook sprintf/strcpy 抓装备切换调用链 (v2, flush fix)
"""
import sys, time, frida, os
sys.stdout.reconfigure(encoding='utf-8')

# 强制 flush
os.environ['PYTHONUNBUFFERED'] = '1'

PID = 3752
TARGET_IC = "50125461"

JS_CODE = """
'use strict';

var sprintf_addr = Module.findExportByName('MSVCR100', 'sprintf');
var strcpy_addr = Module.findExportByName('MSVCR100', 'strcpy');
var TARGET_IC = '""" + TARGET_IC + """';

var hitCount = 0;

function dumpBacktrace(ctx, depth) {
    depth = depth || 15;
    var bt = Thread.backtrace(ctx, Backtracer.ACCURATE);
    var lines = [];
    for (var i = 0; i < bt.length && i < depth; i++) {
        var sym = DebugSymbol.fromAddress(bt[i]);
        var mod = Process.findModuleByAddress(bt[i]);
        var offset = mod ? '0x' + bt[i].sub(mod.base).toString(16) : '?';
        var modName = mod ? mod.name : '?';
        lines.push('#' + i + ' ' + bt[i] + ' ' + modName + '+' + offset + ' ' + sym);
    }
    return lines;
}

if (sprintf_addr) {
    Interceptor.attach(sprintf_addr, {
        onEnter: function(args) {
            this.buf = args[0];
            this.fmt = args[1].readUtf8String();
        },
        onLeave: function(retval) {
            try {
                var result = this.buf.readUtf8String();
                if (result && result.indexOf(TARGET_IC) !== -1) {
                    hitCount++;
                    send({
                        type: 'sprintf',
                        hit: hitCount,
                        result: result.substring(0, 200),
                        fmt: (this.fmt || '').substring(0, 100),
                        backtrace: dumpBacktrace(this.context, 15)
                    });
                }
            } catch(e) {}
        }
    });
}

if (strcpy_addr) {
    Interceptor.attach(strcpy_addr, {
        onEnter: function(args) {
            this.dst = args[0];
            this.src = args[1].readUtf8String();
        },
        onLeave: function(retval) {
            try {
                var result = this.dst.readUtf8String();
                if (result && result.indexOf(TARGET_IC) !== -1) {
                    hitCount++;
                    send({
                        type: 'strcpy',
                        hit: hitCount,
                        result: result.substring(0, 200),
                        backtrace: dumpBacktrace(this.context, 15)
                    });
                }
            } catch(e) {}
        }
    });
}

send({type: 'ready', sprintf: sprintf_addr ? sprintf_addr.toString() : 'null', strcpy: strcpy_addr ? strcpy_addr.toString() : 'null'});
""";

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('type', '')
        if t == 'ready':
            print(f"[*] HOOKS READY  sprintf={p.get('sprintf')}  strcpy={p.get('strcpy')}", flush=True)
            print(f"[*] 监控 ItemCode={TARGET_IC}  去背包操作!", flush=True)
        elif t in ('sprintf', 'strcpy'):
            print(f"\n{'='*70}", flush=True)
            print(f"#{p['hit']} {t.upper()} 命中!", flush=True)
            print(f"  输出: {p.get('result','')}", flush=True)
            if p.get('fmt'):
                print(f"  格式: {p['fmt']}", flush=True)
            print(f"  调用链:", flush=True)
            for line in p.get('backtrace', []):
                print(f"    {line}", flush=True)
            print(f"{'='*70}", flush=True)
    elif msg['type'] == 'error':
        print(f"[ERROR] {msg.get('description','')}", flush=True)

session = frida.attach(PID)
script = session.create_script(JS_CODE)
script.on('message', on_message)
script.load()
print("[*] script loaded, waiting for ready...", flush=True)

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    session.detach()

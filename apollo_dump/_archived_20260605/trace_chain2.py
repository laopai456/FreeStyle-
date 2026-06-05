"""
trace_chain2.py — Hook sprintf/strcpy 抓装备切换调用链 (API 修复版)
"""
import sys, time, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752
TARGET_IC = "50125461"

JS_CODE = """
'use strict';

var TARGET_IC = '""" + TARGET_IC + """';

// Frida 17.9 没有 Module.findExportByName, 用 Process.getModuleByName 代替
var mod = Process.getModuleByName('MSVCR100.dll');
var exps = mod.enumerateExports();
var sprintf_addr = null;
var strcpy_addr = null;

for (var i = 0; i < exps.length; i++) {
    if (exps[i].name === 'sprintf') sprintf_addr = exps[i].address;
    if (exps[i].name === 'strcpy') strcpy_addr = exps[i].address;
}

send('sprintf=' + (sprintf_addr ? sprintf_addr.toString() : 'null'));
send('strcpy=' + (strcpy_addr ? strcpy_addr.toString() : 'null'));

var hitCount = 0;

function dumpBacktrace(ctx, depth) {
    depth = depth || 15;
    var bt = Thread.backtrace(ctx, Backtracer.ACCURATE);
    var lines = [];
    for (var i = 0; i < bt.length && i < depth; i++) {
        var sym = DebugSymbol.fromAddress(bt[i]);
        var m = Process.findModuleByAddress(bt[i]);
        var offset = m ? '0x' + bt[i].sub(m.base).toString(16) : '?';
        var modName = m ? m.name : '?';
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
                    send(JSON.stringify({
                        type: 'sprintf',
                        hit: hitCount,
                        result: result.substring(0, 200),
                        fmt: (this.fmt || '').substring(0, 100),
                        backtrace: dumpBacktrace(this.context, 15)
                    }));
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
                    send(JSON.stringify({
                        type: 'strcpy',
                        hit: hitCount,
                        result: result.substring(0, 200),
                        backtrace: dumpBacktrace(this.context, 15)
                    }));
                }
            } catch(e) {}
        }
    });
}

send('HOOKS_READY');
""";

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if isinstance(p, str):
            if p.startswith('{'):
                import json
                p = json.loads(p)
                t = p.get('type', '')
                print(flush=True)
                print(f"{'='*70}", flush=True)
                print(f"#{p['hit']} {t.upper()} 命中!", flush=True)
                print(f"  输出: {p.get('result','')}", flush=True)
                if p.get('fmt'):
                    print(f"  格式: {p['fmt']}", flush=True)
                print(f"  调用链:", flush=True)
                for line in p.get('backtrace', []):
                    print(f"    {line}", flush=True)
                print(f"{'='*70}", flush=True)
            elif p == 'HOOKS_READY':
                print("[*] HOOKS READY — 去背包操作!", flush=True)
            else:
                print(f"[*] {p}", flush=True)
    elif msg['type'] == 'error':
        print(f"[ERROR] {msg.get('description','')}", flush=True)

print(f"[*] Attaching to PID {PID} ...", flush=True)
session = frida.attach(PID)
script = session.create_script(JS_CODE)
script.on('message', on_message)
script.load()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    session.detach()

"""
trace_equipment_chain.py — 方案C: Hook sprintf 抓装备切换的完整调用链
当 sprintf 输出包含 ItemCode 时, 抓 15 层 backtrace
"""
import sys, time, frida
sys.stdout.reconfigure(encoding='utf-8')

PID = 3752
TARGET_IC = "50125461"  # 美丽梦想发型

JS_CODE = r"""
'use strict';

var sprintf_addr = Module.findExportByName('MSVCR100', 'sprintf');
var strcpy_addr = Module.findExportByName('MSVCR100', 'strcpy');
var TARGET_IC = '""" + TARGET_IC + """';

var hitCount = 0;

// 抓 backtrace 并格式化
function dumpBacktrace(ctx, depth) {
    depth = depth || 15;
    var bt = Thread.backtrace(ctx, Backtracer.ACCURATE);
    var lines = [];
    for (var i = 0; i < bt.length && i < depth; i++) {
        var sym = DebugSymbol.fromAddress(bt[i]);
        var mod = Process.findModuleByAddress(bt[i]);
        var offset = mod ? '0x' + bt[i].sub(mod.base).toString(16) : '?';
        var modName = mod ? mod.name : '?';
        lines.push('  #' + i + ' ' + bt[i] + ' ' + modName + '+' + offset + ' ' + sym);
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
                    var ts = new Date().toTimeString().split(' ')[0];
                    send({
                        type: 'sprintf',
                        hit: hitCount,
                        time: ts,
                        result: result.substring(0, 200),
                        fmt: (this.fmt || '').substring(0, 100),
                        backtrace: dumpBacktrace(this.context, 15)
                    });
                }
            } catch(e) {}
        }
    });
    send({type: 'info', msg: 'sprintf hooked @ ' + sprintf_addr});
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
                    var ts = new Date().toTimeString().split(' ')[0];
                    send({
                        type: 'strcpy',
                        hit: hitCount,
                        time: ts,
                        result: result.substring(0, 200),
                        backtrace: dumpBacktrace(this.context, 15)
                    });
                }
            } catch(e) {}
        }
    });
    send({type: 'info', msg: 'strcpy hooked @ ' + strcpy_addr});
}

// 也 hook memcpy / memmove — 可能直接搬 ItemCode 的 4 字节
var memcpy_addr = Module.findExportByName('MSVCR100', 'memcpy');
if (memcpy_addr) {
    Interceptor.attach(memcpy_addr, {
        onEnter: function(args) {
            var size = args[2].toInt32();
            // 只关注小 size (可能是 ItemCode 的 4 字节或字符串的 8 字节)
            if (size > 0 && size <= 32) {
                try {
                    var src = args[1].readUtf8String(size);
                    if (src && src.indexOf(TARGET_IC) !== -1) {
                        hitCount++;
                        var ts = new Date().toTimeString().split(' ')[0];
                        send({
                            type: 'memcpy',
                            hit: hitCount,
                            time: ts,
                            size: size,
                            data: src.substring(0, 100),
                            backtrace: dumpBacktrace(this.context, 15)
                        });
                    }
                } catch(e) {}
            }
        }
    });
    send({type: 'info', msg: 'memcpy hooked @ ' + memcpy_addr});
}
""";

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if p.get('type') == 'info':
            print(f"[*] {p['msg']}")
        elif p.get('type') in ('sprintf', 'strcpy', 'memcpy'):
            print(f"\n{'='*70}")
            print(f"[{p['time']}] #{p['hit']} {p['type'].upper()} 命中!")
            print(f"  输出: {p.get('result', p.get('data', ''))}")
            if p.get('fmt'):
                print(f"  格式: {p['fmt']}")
            if p.get('size'):
                print(f"  大小: {p['size']}")
            print(f"  调用链:")
            for line in p.get('backtrace', []):
                print(f"    {line}")
            print(f"{'='*70}")
    elif msg['type'] == 'error':
        print(f"[ERROR] {msg.get('description','')}")


def main():
    print(f"[*] Attaching to PID {PID} ...")
    session = frida.attach(PID)
    script = session.create_script(JS_CODE)
    script.on('message', on_message)
    script.load()
    print(f"[*] Hook 就绪, 监控 ItemCode={TARGET_IC}")
    print(f"[*] 去背包里切换发型吧! Ctrl+C 退出\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 停止")
        session.detach()

if __name__ == '__main__':
    main()

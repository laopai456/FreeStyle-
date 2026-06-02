"""
trace_shop_resource.py — Hook 文件 API, 追踪商城试用时的资源加载路径

hook CreateFileW / fopen, 过滤 .ppi/.pak 相关调用, 抓调用栈。
这样能找到游戏从 ItemCode 到加载 .ppi 模型的完整路径。

用法:
  1. 先运行 patch_itemcode.py patch 一个商城物品
  2. 再运行本脚本
  3. 点击"试用"那个物品
  4. 看输出中的 .ppi 路径和调用栈
"""
import frida, json, sys, time

JS = r"""
'use strict';

var g_capturing = false;
var g_results = [];

// Hook CreateFileW
var CreateFileW = Module.getExportByName('kernel32.dll', 'CreateFileW');
Interceptor.attach(CreateFileW, {
    onEnter: function(args) {
        if (!g_capturing) return;
        var path = args[0].readUtf16String();
        if (!path) return;
        var lower = path.toLowerCase();
        if (lower.indexOf('.ppi') >= 0 || lower.indexOf('.pak') >= 0 ||
            lower.indexOf('item_2404') >= 0 || lower.indexOf('item_2405') >= 0 ||
            lower.indexOf('fleece') >= 0 || lower.indexOf('hair') >= 0) {
            var bt = Thread.backtrace(this.context, Backtracer.FUZZY).map(DebugSymbol.fromAddress);
            var entry = {
                type: 'FILE',
                api: 'CreateFileW',
                path: path,
                backtrace: bt.map(function(s) { return s.toString(); }).slice(0, 10)
            };
            g_results.push(entry);
            send(JSON.stringify(entry));
        }
    }
});

// Hook fopen (CRT)
try {
    var fopen_addr = Module.getExportByName('msvcrt.dll', 'fopen');
    if (!fopen_addr) fopen_addr = Module.getExportByName(null, 'fopen');
    if (fopen_addr) {
        Interceptor.attach(fopen_addr, {
            onEnter: function(args) {
                if (!g_capturing) return;
                var path = args[0].readUtf8String();
                if (!path) return;
                var lower = path.toLowerCase();
                if (lower.indexOf('.ppi') >= 0 || lower.indexOf('.pak') >= 0 ||
                    lower.indexOf('item_') >= 0) {
                    var bt = Thread.backtrace(this.context, Backtracer.FUZZY).map(DebugSymbol.fromAddress);
                    var entry = {
                        type: 'FILE',
                        api: 'fopen',
                        path: path,
                        backtrace: bt.map(function(s) { return s.toString(); }).slice(0, 10)
                    };
                    g_results.push(entry);
                    send(JSON.stringify(entry));
                }
            }
        });
    }
} catch(e) {}

// Hook fread for .ppi content reading
try {
    var fread_addr = Module.getExportByName('msvcrt.dll', 'fread');
    if (!fread_addr) fread_addr = Module.getExportByName(null, 'fread');
    if (fread_addr) {
        var g_lastFopenPath = null;
        // Track last opened file
        Interceptor.attach(fopen_addr, {
            onEnter: function(args) {
                g_lastFopenPath = args[0].readUtf8String();
            }
        });
    }
} catch(e) {}

// RPC
rpc.exports = {
    start: function() {
        g_capturing = true;
        g_results = [];
        return 'capturing';
    },
    stop: function() {
        g_capturing = false;
        return 'stopped, ' + g_results.length + ' results';
    },
    getresults: function() {
        return JSON.stringify(g_results);
    }
};

send(JSON.stringify({type:'info', msg:'Ready. Call start() to begin capturing, then try on item in shop'}));
""";

def main():
    pid = None
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            pid = int(parts[1])
            break
    if not pid:
        print("FreeStyle.exe not found"); return

    print(f"PID={pid}")
    print("Hooking file APIs. Will capture .ppi/.pak access during shop try-on.\n")

    outpath = r"D:\py\反编译\FreeStyle\trace_shop_result.txt"

    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}"); return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except: print(f"  {p}"); return
        t = p.get('type', '')
        if t == 'FILE':
            print(f"  [{p['api']}] {p['path']}")
            for f in p.get('backtrace', [])[:6]:
                print(f"    {f}")
            print()
            with open(outpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(p, indent=2) + '\n\n')
        elif t == 'info':
            print(f"  [*] {p['msg']}")

    script.on('message', on_message)
    script.load()

    # Start capturing
    script.exports_sync.start()
    print("  Capturing started. Now try on item in shop.")
    print("  Ctrl+C to stop.\n")

    # Clear output file
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('')

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

    results = script.exports_sync.stop()
    print(f"\n  Stopped. {results}")
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print(f"  Results in {outpath}")

if __name__ == '__main__':
    main()

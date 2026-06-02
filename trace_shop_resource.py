"""
trace_shop_resource.py — 追踪商城试用时的资源加载
用 Process.getModuleByName 替代 Module.getExportByName
"""
import frida, json, sys, time

JS = r"""
'use strict';

var kernel32 = Process.getModuleByName('kernel32.dll');
var createFileW = kernel32.getExportByName('CreateFileW');
Interceptor.attach(createFileW, {
    onEnter: function(args) {
        try {
            var path = args[0].readUtf16String();
            if (!path) return;
            var lower = path.toLowerCase();
            if (lower.indexOf('.ppi') >= 0 || lower.indexOf('.pak') >= 0 ||
                lower.indexOf('item_') >= 0) {
                var bt = Thread.backtrace(this.context, Backtracer.FUZZY).map(DebugSymbol.fromAddress);
                send(JSON.stringify({
                    type: 'FILE',
                    path: path,
                    bt: bt.map(function(s) { return s.toString(); }).slice(0, 12)
                }));
            }
        } catch(e) {}
    }
});

// 也 hook ReadFile 看大文件读取
var readFile = kernel32.getExportByName('ReadFile');
var g_lastPath = '';
Interceptor.attach(createFileW, {
    onLeave: function(retval) {}
});

send('ready');
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
    outpath = r"D:\py\反编译\FreeStyle\trace_shop_result.txt"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('')

    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            if isinstance(p, str):
                try: p = json.loads(p)
                except:
                    print(f"  [*] {p}")
                    return
            if isinstance(p, dict) and p.get('type') == 'FILE':
                print(f"  {p['path']}")
                for f in p.get('bt', [])[:8]:
                    print(f"    {f}")
                print()
                with open(outpath, 'a', encoding='utf-8') as fout:
                    fout.write(json.dumps(p, indent=2, ensure_ascii=False) + '\n\n')

    script.on('message', on_message)
    script.load()

    print("  进商城点试用, Ctrl+C 停止\n")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print(f"\nResults in {outpath}")

if __name__ == '__main__':
    main()

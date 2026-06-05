"""
test_hook_safety.py — 测试 hook 0x1922720 本身是否导致崩溃
不做任何读写，只 hook

用法: py test_hook_safety.py
"""
import frida, json, sys, time

JS = r"""
'use strict';
var g_count = 0;
var pktBuilder = ptr(0x1922720);

Interceptor.attach(pktBuilder, {
    onEnter: function(args) {
        g_count++;
        if (g_count <= 5) {
            send(JSON.stringify({type:'ping', n: g_count, ecx: this.context.ecx.toString()}));
        }
    }
});
send(JSON.stringify({type:'info', msg:'Hooked 0x1922720 (NO modification)'}));
""";

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
    print("FreeStyle.exe not found")
    sys.exit(1)

print(f"PID={pid} — hook only, no modification. Play normally. Ctrl+C to stop.\n")
session = frida.attach(pid)
script = session.create_script(JS)

def on_message(msg, data):
    if msg['type'] != 'send':
        print(f"  [FRIDA] {msg}")
        return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except:
            print(f"  {p}")
            return
    t = p.get('type', '')
    if t == 'ping':
        print(f"  [{p['n']}] called, ecx={p['ecx']}")
    elif t == 'info':
        print(f"  [*] {p['msg']}")
    else:
        print(f"  [{t}] {p}")

script.on('message', on_message)
script.load()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

try: script.unload()
except: pass
try: session.detach()
except: pass
print("\nDone.")

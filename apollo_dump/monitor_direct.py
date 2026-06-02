"""monitor_direct.py — 直接附加到指定 PID"""
import frida, time, sys
print = lambda *a, **kw: __builtins__.print(*a, **kw, flush=True)

pid = int(sys.argv[1]) if len(sys.argv) > 1 else None
if not pid:
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and 'freestyle' in p.info['name'].lower():
            pid = p.info['pid']
            break

if not pid:
    print('Waiting for FreeStyle.exe...')
    import time as _t
    while not pid:
        for p in __import__('psutil').process_iter(['pid','name']):
            if p.info['name'] and 'freestyle' in p.info['name'].lower():
                pid = p.info['pid']
                break
        _t.sleep(1)
    print(f'Found PID {pid}')

print(f'Attaching to PID {pid}...')
session = frida.attach(pid)

with open(__file__.replace('_direct.py', '_v2.js'), encoding='utf-8') as f:
    js = f.read()

script = session.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('type', '')
        if t == 'file_open':
            print(f'[OPEN] {p["path"]}')
        elif t == 'bml':
            print(f'[BML] ic={p["itemcode"]} sz={p["size"]} mesh={p.get("mesh_paths",[])}')
        elif t == 'info':
            print(f'[INFO] {p.get("msg","")}')
        elif t == 'err':
            print(f'[ERR] {p.get("msg","")}')

script.on('message', on_msg)
script.load()
print('Monitor ready. Trigger character load.')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
script.unload()
session.detach()

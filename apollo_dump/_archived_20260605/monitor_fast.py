"""
monitor_fast.py — 快速附加到 FreeStyle.exe + 监控 PAK/BML
"""
import frida, time, os, sys

def try_attach():
    # Try frida's device enumeration to find FreeStyle
    dev = frida.get_local_device()
    for p in dev.enumerate_processes():
        if p.name and 'freestyle' in p.name.lower():
            print(f'Found: {p.name} PID={p.pid}')
            return frida.attach(p.pid)
    return None

# Wait loop
for attempt in range(60):
    session = try_attach()
    if session:
        print(f'Attached!')
        break
    time.sleep(1)
else:
    print('FreeStyle.exe not found after 60s')
    sys.exit(1)

js = open(os.path.join(os.path.dirname(__file__), 'monitor_v2.js'), encoding='utf-8').read()
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
        else:
            print(f'[{t}] {p}')

script.on('message', on_msg)
script.load()
print('Monitor ready.')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
script.unload()
session.detach()

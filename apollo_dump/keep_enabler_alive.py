"""Keep x64dbg_enabler.js Frida session alive for x32dbg attachment"""
import frida, sys, time, os

pid = 25108
print(f'Attaching to PID {pid}...')
sys.stdout.flush()
session = frida.attach(pid)
print('Attached')
sys.stdout.flush()

with open(os.path.join(os.path.dirname(__file__), 'x64dbg_enabler.js'), 'r', encoding='utf-8') as f:
    js = f.read()

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if isinstance(p, dict) and p.get('t') == 'PEB':
            pass  # quiet PEB refresh
        else:
            print(f'  {p}')
    elif msg['type'] == 'error':
        print(f'  [ERR] {msg.get("description","")[:200]}')
    sys.stdout.flush()

script = session.create_script(js)
script.on('message', on_msg)
script.load()
print('[READY] Enabler active. Attach x32dbg now.')
print('Press Ctrl+C to detach.')
sys.stdout.flush()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print('Detached.')

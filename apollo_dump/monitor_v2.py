"""
monitor_v2.py — 监控 PAK 文件加载 + BML 读取
"""
import frida, sys, os, time

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

pid = find_pid()
if not pid:
    print("FreeStyle.exe not running")
    sys.exit(1)

print(f"PID: {pid}")
session = frida.attach(pid)

js = open(os.path.join(os.path.dirname(__file__), 'monitor_v2.js'), encoding='utf-8').read()
script = session.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('type', '')
        if t == 'file_open':
            print(f"  [OPEN] {p['path']}")
        elif t == 'bml':
            print(f"  [BML] ic={p['itemcode']} sz={p['size']} mesh={p.get('mesh_paths',[])}")
        elif t in ('info', 'err'):
            print(f"  [{t.upper()}] {p.get('msg','')}")
        else:
            print(f"  [{t}] {p}")
    elif msg['type'] == 'error':
        print(f"  [ERR] {msg.get('description','')}")

script.on('message', on_msg)
script.load()

print("Monitoring... Trigger character load in game")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
script.unload()
session.detach()

"""
monitor_wait.py — 等待 FreeStyle.exe 启动后自动附加监控
"""
import frida, time, os, sys, psutil

def wait_freestyle():
    while True:
        for p in psutil.process_iter(['pid','name']):
            if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
                return p.info['pid']
        time.sleep(1)

print("Waiting for FreeStyle.exe...")
pid = wait_freestyle()
print(f"Found PID: {pid}, attaching in 3s...")
time.sleep(3)

try:
    session = frida.attach(pid)
except Exception as e:
    print(f"Attach failed: {e}")
    # Try again after 5s
    time.sleep(5)
    session = frida.attach(pid)

js_path = os.path.join(os.path.dirname(__file__), 'monitor_v2.js')
js = open(js_path, encoding='utf-8').read()
script = session.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('type', '')
        if t == 'file_open':
            print(f"[OPEN] {p['path']}")
        elif t == 'bml':
            print(f"[BML] ic={p['itemcode']} sz={p['size']} mesh={p.get('mesh_paths',[])}")
        elif t == 'info':
            print(f"[INFO] {p.get('msg','')}")
        elif t == 'err':
            print(f"[ERR] {p.get('msg','')}")
        else:
            print(f"[{t}] {p}")
    elif msg['type'] == 'error':
        print(f"[JSERR] {msg.get('description','')}")

script.on('message', on_msg)
script.load()
print("Monitor ready. Log in and trigger character load.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
script.unload()
session.detach()

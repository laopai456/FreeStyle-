"""smd_redirect_v12 — SString 替换, 让游戏自己加载目标 SMD"""
import frida
import sys
import os
from datetime import datetime

PID = frida.get_local_device().get_process('FreeStyle.exe').pid
now = datetime.now().strftime('%Y%m%d_%H%M%S')
log_path = os.path.join(os.path.dirname(__file__), 'apollo_dump', f'smd_v12_{now}.txt')

def log(msg):
    print(msg)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

log(f'Log: {log_path}')
log(f'Attaching PID {PID}...')

session = frida.attach(PID)

js_path = os.path.join(os.path.dirname(__file__), 'smd_redirect_v12.js')
with open(js_path, 'r', encoding='utf-8') as f:
    js_code = f.read()

script = session.create_script(js_code)

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'ready':
            log(f'\n=== SMD Redirect v12 ===')
            log(f'  Source: i50123971 (当前发型)')
            log(f'  Target: i50125711 (紫色超赛)')
            log(f'  {p.get("msg","")}')
            log(f'\n步骤:')
            log(f'  1. try → 安装 SString hook')
            log(f'  2. 等角色完全加载 (SSKF 消息停)')
            log(f'  3. enable → 激活替换')
            log(f'  4. 进商城/切频道 → 触发新角色模型加载')
            log(f'  5. 看 SSKF 是否出现 i50125711_ms.smd')
            log(f'  6. disable → 停用')
        elif t == 'SSKF':
            log(f'  SSKF: {p.get("name","")}  sz={p.get("sz",0)}')
        elif t == 'step':
            log(f'  [step] {p.get("msg","")}')
        elif t == 'err':
            log(f'  [ERROR] {p.get("msg","")}')
        elif t == 'REPLACE':
            log(f'  [REPLACE #{p.get("n",0)}] "{p.get("from","")}" → "{p.get("to","")}"')
        else:
            log(f'  [{t}] {p}')
    elif msg['type'] == 'error':
        log(f'  [JS ERROR] {msg.get("description","")}')

script.on('message', on_message)
script.load()

def cmd_loop():
    import threading
    import queue
    q = queue.Queue()
    
    def reader():
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    q.put(None)
                    break
                q.put(line.strip())
            except:
                break
    
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    
    api = script.exports_sync
    
    while True:
        try:
            cmd = q.get(timeout=0.5)
        except queue.Empty:
            continue
        
        if cmd is None:
            break
        
        if cmd == 'try':
            log(f'\n>>> try')
            result = api.try_hook()
            log(f'result: {result}')
        
        elif cmd == 'enable':
            log(f'\n>>> enable')
            result = api.enable()
            log(f'result: {result}')
        
        elif cmd == 'disable':
            log(f'\n>>> disable')
            result = api.disable()
            log(f'result: {result}')
        
        elif cmd in ('s', 'status'):
            result = api.status()
            log(f'\nstatus: {result}')
        
        elif cmd in ('q', 'quit', 'exit'):
            break
        
        elif cmd:
            log(f'unknown: {cmd}')

session.on('detached', lambda reason, crash: 
    log(f'\n!!! PROCESS EXIT: reason={reason}, crash={crash} !!!'))

try:
    cmd_loop()
except KeyboardInterrupt:
    pass
finally:
    log('Detaching...')
    try: session.detach()
    except: pass
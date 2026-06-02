"""
smd_redirect_v13b.py — 全自动版, 无需手动命令
加载后自动等 8s → hook 0x21e25b0 → 自动替换 SString 中的 item code
用法:
  py smd_redirect_v13b.py [source] [target]
"""
import frida
import subprocess
import os
import time
import sys
from datetime import datetime

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smd_redirect_v13b.js')

SOURCE = sys.argv[1] if len(sys.argv) > 1 else '50123971'
TARGET = sys.argv[2] if len(sys.argv) > 2 else '50125711'

def find_pid():
    r = subprocess.run(['tasklist','/FI','IMAGENAME eq FreeStyle.exe','/FO','CSV','/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if 'freestyle' in line.lower():
            parts = line.split(',')
            if len(parts) >= 2:
                return int(parts[1].strip('"'))
    return None

def main():
    pid = find_pid()
    if not pid:
        print('[ERROR] FreeStyle.exe not running')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(DUMP_DIR, f'smd_v13b_{ts}.txt')
    os.makedirs(DUMP_DIR, exist_ok=True)
    log = open(log_path, 'w', encoding='utf-8')

    def log_msg(msg):
        print(msg)
        log.write(msg + '\n')
        log.flush()

    session = frida.attach(pid)
    log_msg(f'Log: {log_path}')
    log_msg(f'Attaching PID {pid}...')

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()

    src_code = 'i' + SOURCE
    tgt_code = 'i' + TARGET
    js_code = js_code.replace("var SOURCE = 'i50123971';", f"var SOURCE = '{src_code}';")
    js_code = js_code.replace("var TARGET = 'i50125711';", f"var TARGET = '{tgt_code}';")

    script = session.create_script(js_code)

    def on_msg(msg, data):
        if msg['type'] == 'error':
            log_msg(f'  [JS ERROR] {msg.get("description", msg)}')
            return
        p = msg.get('payload', {})
        t = p.get('t', '')
        if t == 'REPLACE':
            log_msg(f'  [REPLACE #{p["n"]}] {p["from"]} -> {p["to"]}')
        elif t == 'STATUS':
            log_msg(f'  [{t}] {p["msg"]}')
        elif t == 'ERR':
            log_msg(f'  [ERROR] {p["msg"]}')
        else:
            log_msg(f'  {p}')

    script.on('message', on_msg)
    script.load()

    session.on('detached', lambda reason, crash:
        log_msg(f'\n!!! PROCESS EXIT: reason={reason}, crash={crash} !!!'))

    log_msg(f'\n=== SMD Redirect v13b (AUTO) ===')
    log_msg(f'  Source: i{SOURCE} -> Target: i{TARGET}')
    log_msg('  Auto-hook in 8 seconds...')
    log_msg('  Then go to shop / switch channel to trigger model reload.')
    log_msg('  Ctrl+C to exit.\n')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_msg('\nDetaching...')
    finally:
        session.detach()
        log.close()
        print(f'\nDone. Log: {log_path}')

if __name__ == '__main__':
    main()
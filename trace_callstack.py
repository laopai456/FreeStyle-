"""
trace_callstack.py — 路线 Alpha
ReadFile SSKF 触发 → 读 Thread.backtrace → 定位 AcquireSMD 调用者
"""
import frida
import subprocess
import sys
import os
import time
from datetime import datetime

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')

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
        print("[ERROR] FreeStyle.exe not found. Start the game first.")
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(DUMP_DIR, f'callstack_{ts}.txt')
    os.makedirs(DUMP_DIR, exist_ok=True)
    log = open(log_path, 'w', encoding='utf-8')
    print(f"Log: {log_path}")

    def log_msg(msg):
        print(msg)
        log.write(msg + '\n')
        log.flush()

    session = frida.attach(pid)
    log_msg(f"Attaching PID {pid}...")

    with open(os.path.join(os.path.dirname(__file__), 'trace_callstack.js'), 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)

    def on_msg(msg, data):
        if msg['type'] == 'error':
            log_msg(f"  [JS ERROR] {msg.get('description', msg)}")
            return
        payload = msg.get('payload', {})
        t = payload.get('t', '')
        if t == 'SSKF':
            name = payload.get('name', '?')
            sz = payload.get('sz', 0)
            stack = payload.get('stack', [])
            log_msg(f"\n=== SSKF: {name} ({sz} bytes) ===")
            for i, frame in enumerate(stack):
                marker = ' <--' if 'FreeStyle.exe' in frame else ''
                log_msg(f"  #{i}: {frame}{marker}")
        elif t == 'diag':
            log_msg(f"  [diag] {payload.get('msg', '')}")
        elif t == 'ready':
            log_msg(f"  {payload.get('msg', '')}")
        else:
            log_msg(f"  {payload}")

    script.on('message', on_msg)
    script.load()

    session.on('detached', lambda reason, crash:
        log_msg(f"\n!!! PROCESS EXIT: reason={reason}, crash={crash} !!!"))

    log_msg("\n=== SSKF + Call Stack Tracer ===")
    log_msg("操作: 在游戏里动一下, 触发 SMD 加载")
    log_msg("Ctrl+C 退出")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_msg("\nDetaching...")
    finally:
        session.detach()
        log.close()
        print(f"\nDone. Log: {log_path}")

if __name__ == '__main__':
    main()
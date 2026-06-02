# locate_acquiresmd.py — Frida 定位 AcquireSMD 入口 + 日志导出
# 用法: py locate_acquiresmd.py
# 输出: locate_acquiresmd_YYYYMMDD_HHMMSS.txt

import frida
import sys
import os
import time
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(SCRIPT_DIR, 'locate_acquiresmd.js')
LOG_FILE = os.path.join(SCRIPT_DIR, 'locate_acquiresmd_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt')

log_handle = None

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:12]
    line = f'[{ts}] {msg}'
    print(line)
    if log_handle:
        log_handle.write(line + '\n')
        log_handle.flush()

def find_pid():
    try:
        result = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except Exception as e:
        log(f'[!] tasklist failed: {e}')
    return None

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '?')

        if t == 'INIT':
            log(f'[INIT] {p["msg"]}')
        elif t == 'INFO':
            log(f'[INFO] base={p["base"]} .text={p["textStart"]}-{p["textEnd"]} ({p["textSize"]} bytes)')
        elif t == 'PHASE':
            log(f'[PHASE] {p["msg"]}')
        elif t == 'SSKF_HIT':
            log(f'[SSKF] #{p["offset"]} @ {p["addr"]}')
        elif t == 'CANDIDATE':
            log(f'[CAND]  {p["msg"]}')
        elif t == 'SELECT':
            log(f'[SELECT] {p["msg"]}')
        elif t == 'HOOK_HIT':
            log(f'[HOOK] {p["msg"]}')
            log(f'[HOOK]   args[0]={p.get("args", "?")}')
            log(f'[HOOK]   stack={p.get("stack", "?")}')
        elif t == 'HOOK_LEAVE':
            log(f'[LEAVE] FreeStyle+{p["offset"]} retval={p["retval"]}')
        elif t == 'SUCCESS':
            log(f'[SUCCESS] {p["msg"]}')
        elif t == 'WARN':
            log(f'[WARN] {p["msg"]}')
        elif t == 'ERROR':
            log(f'[ERROR] {p["msg"]}')
        elif t == 'FATAL':
            log(f'[FATAL] {p["msg"]}')
        elif t == 'DONE':
            log(f'[DONE] {p["msg"]}')
        else:
            log(f'[{t}] {p.get("msg", str(p))}')
    elif msg['type'] == 'error':
        log(f'[JS ERROR] {msg.get("description", msg)}')

def main():
    global log_handle

    log_handle = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'locate_acquiresmd.py started')
    log(f'Log file: {LOG_FILE}')
    log(f'')

    pid = find_pid()
    if pid is None:
        log('[!] FreeStyle.exe not found. Start game first.')
        log_handle.close()
        sys.exit(1)
    log(f'[+] FreeStyle.exe PID: {pid}')

    log(f'[*] Attaching via Frida...')
    try:
        session = frida.attach(pid)
    except Exception as e:
        log(f'[!] Attach failed: {e}')
        log_handle.close()
        sys.exit(1)

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)
    script.on('message', on_message)
    script.load()
    log(f'[*] Script loaded. Waiting for SSKF scan results...')
    log(f'')

    log(f'[TIP] Go into a game scene (not lobby) so AcquireSMD is called.')
    log(f'[TIP] Press Ctrl+C to stop.')
    log(f'')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log(f'\n[EXIT] User interrupt')
    finally:
        try:
            session.detach()
        except:
            pass
        log(f'[DONE] Log saved to: {LOG_FILE}')
        log_handle.close()

if __name__ == '__main__':
    main()
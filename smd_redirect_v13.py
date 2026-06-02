"""
smd_redirect_v13.py — SString 替换方案 (基于调用栈确认)
hook FreeStyle.exe+0x21e25b0 → args[0] SString 替换 item code
用法:
  py smd_redirect_v13.py [source] [target]
  py smd_redirect_v13.py                          # 默认 50123971->50125711
"""
import frida
import subprocess
import os
import time
import sys
from datetime import datetime

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smd_redirect_v13.js')

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
        print('[ERROR] FreeStyle.exe 未运行，请先启动游戏')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(DUMP_DIR, f'smd_v13_{ts}.txt')
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

    # 替换 JS 中的 source/target
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
        elif t == 'STATE':
            log_msg(f'  [STATE] {p["msg"]}')
        elif t == 'HOOK':
            log_msg(f'  [HOOK] {p["msg"]}')
        elif t == 'READY':
            log_msg(f'  [READY] {p["msg"]}')
        elif t == 'ERR':
            log_msg(f'  [ERR] {p["msg"]}')
        else:
            log_msg(f'  {p}')

    script.on('message', on_msg)
    script.load()

    session.on('detached', lambda reason, crash:
        log_msg(f'\n!!! PROCESS EXIT: reason={reason}, crash={crash} !!!'))

    rpc = script.exports_sync
    log_msg(f'\n=== SMD Redirect v13 ===')
    log_msg(f'  Source: i{SOURCE} (当前发型)')
    log_msg(f'  Target: i{TARGET} (目标发型)')
    log_msg(f'  Commands: try | enable | disable | status')

    def cmd_try():
        log_msg('\n>>> try')
        try:
            r = rpc.tryHook()
            log_msg(f'  result: {r}')
        except Exception as e:
            log_msg(f'  [ERROR] try failed: {e}')

    def cmd_enable():
        log_msg('\n>>> enable')
        try:
            r = rpc.enable()
            log_msg(f'  result: {r}')
        except Exception as e:
            log_msg(f'  [ERROR] enable failed: {e}')

    def cmd_disable():
        log_msg('\n>>> disable')
        try:
            r = rpc.disable()
            log_msg(f'  result: {r}')
        except Exception as e:
            log_msg(f'  [ERROR] disable failed: {e}')

    def cmd_status():
        try:
            s = rpc.status()
            log_msg(f'  status: {s}')
        except Exception as e:
            log_msg(f'  [ERROR] status failed: {e}')

    log_msg('\n步骤:')
    log_msg('  1. try  → 安装 hook')
    log_msg('  2. 等角色加载完')
    log_msg('  3. enable → 激活替换')
    log_msg('  4. 进商城/切频道 → 触发模型重载')
    log_msg('  5. 看是否有 [REPLACE] 消息')

    try:
        import threading
        lock = threading.Lock()
        pending = [None]

        def reader():
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    line = line.strip().lower()
                    with lock:
                        pending[0] = line
                except Exception:
                    break

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        while True:
            time.sleep(0.3)
            with lock:
                cmd = pending[0]
                pending[0] = None
            if cmd is None:
                continue
            if cmd == 'try':
                cmd_try()
            elif cmd == 'enable':
                cmd_enable()
            elif cmd == 'disable':
                cmd_disable()
            elif cmd == 'status':
                cmd_status()
            elif cmd == 'exit' or cmd == 'quit':
                break
            else:
                log_msg(f'  未知命令: {cmd}')
    except KeyboardInterrupt:
        log_msg('\nDetaching...')
    finally:
        session.detach()
        log.close()
        print(f'\nDone. Log: {log_path}')

if __name__ == '__main__':
    main()
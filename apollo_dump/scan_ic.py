"""
scan_ic.py — 扫描内存中 ItemCode 50125461 的所有位置
用法: python scan_ic.py
"""
import sys, os, time, subprocess
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'scan_ic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
log_lines = []

def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line)
    log_lines.append(line)

def save_log():
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    print(f'\n日志已保存: {LOG_FILE}')

def find_pid():
    try:
        r = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except Exception as e:
        log(f'查找进程失败: {e}')
    return None

def main():
    pid = find_pid()
    if not pid:
        log('FreeStyle.exe 未运行，请先启动游戏')
        return 1
    log(f'PID={pid}')

    import frida
    session = frida.attach(pid)
    log('Frida 已附加')

    js_path = os.path.join(SCRIPT_DIR, 'scan_ic.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        js_code = f.read()

    def on_msg(msg, data):
        if msg['type'] == 'error':
            log(f'[JS错误] {msg.get("description","")} @ line {msg.get("lineNumber","?")}')
            return
        if msg['type'] != 'send':
            return

        p = msg['payload']
        t = p.get('t', '')

        if t == 'info':
            log(f'  {p["msg"]}')
        elif t == 'scan_result':
            log(f'  游戏模块内命中: {p["count"]} 处')
        elif t == 'hit':
            log(f'  [{p["n"]:2d}] {p["addr"]}  ({p["mod"]} +{p["modOffset"]})')
            log(f'       上下文: {p["ctx"]}')
        elif t == 'heap_hit':
            log(f'  [堆{p["n"]:2d}] {p["addr"]}  (size={p["size"]} prot={p["prot"]})')
            log(f'       上下文: {p["ctx"]}')
        elif t == 'done':
            log(f'  {p["msg"]}')
        elif t == 'heap_done':
            log(f'  堆内存命中: {p["count"]} 处')

    script = session.create_script(js_code)
    script.on('message', on_msg)
    script.load()

    log('扫描中，等待完成... (Ctrl+C 退出)\n')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    script.unload()
    session.detach()
    log('已断开')
    save_log()
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log(f'异常: {e}')
        save_log()

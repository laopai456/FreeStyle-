"""
scan_ic_diff.py — 练习场前后对比扫描 ItemCode
流程: scan1 → 进练习场 → scan2 → diff
"""
import sys, os, time, subprocess
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'scan_diff_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
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
        log('FreeStyle.exe 未运行')
        return 1
    log(f'PID={pid}')

    import frida
    session = frida.attach(pid)
    log('Frida 已附加')

    js_path = os.path.join(SCRIPT_DIR, 'scan_ic_diff.js')
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

        if t == 'ready':
            log(f'  {p["msg"]}')
        elif t == 'scan':
            log(f'  [{p["label"]}] 命中 {p["count"]} 处')
        elif t == 'diff':
            log(f'  对比: 只第一轮={p["only1"]} 只练习场={p["only2"]} 共有={p["both"]}')
        elif t == 'new':
            log(f'  [练习场新增 {p["n"]}] {p["addr"]}  当前值=0x{p["val"]:x} ({p["val"]})')
            ctx = p.get('ctx', '')
            if ctx:
                log(f'       上下文: {ctx}')
        elif t == 'changed':
            log(f'  [值变更 {p["n"]}] {p["addr"]}  {p["oldVal"]}→{p["newVal"]} (0x{p["newVal"]:x})')

    script = session.create_script(js_code)
    script.on('message', on_msg)
    script.load()

    log('')
    log('操作流程:')
    log('  1. 输入 scan1  → 第一轮扫描(大厅状态)')
    log('  2. 进练习场')
    log('  3. 输入 scan2  → 第二轮扫描(练习场状态)')
    log('  4. 输入 diff   → 对比差异')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'scan1':
                n = script.exports_sync.scan1()
                log(f'第一轮: {n} 处')
            elif cmd == 'scan2':
                n = script.exports_sync.scan2()
                log(f'第二轮: {n} 处')
            elif cmd == 'diff':
                result = script.exports_sync.diff()
                log(f'结果: {result}')
            elif cmd.startswith('read '):
                addr = cmd.split()[1]
                ctx = script.exports_sync.read(addr)
                log(f'{addr}: {ctx}')
            else:
                log('命令: scan1 / scan2 / diff / read <addr> / quit')
    except (KeyboardInterrupt, EOFError):
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

"""
patch_practice_ic.py — 定位练习场 ItemCode 地址并覆写为 50125711
流程:
  scan1    → 大厅扫描
  进练习场
  scan2    → 练习场扫描
  diff     → 找新增地址
  patch    → 写入 50125711
  restore  → 恢复 50125461
"""
import sys, os, time, subprocess
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'patch_ic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
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

    js_path = os.path.join(SCRIPT_DIR, 'patch_practice_ic.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)
    script.on('message', lambda msg, data: None)
    script.load()

    log('就绪\n')
    log('流程:')
    log('  1. scan1    (大厅状态)')
    log('  2. 进练习场')
    log('  3. scan2    (练习场状态)')
    log('  4. diff     (找新增)')
    log('  5. patch    (写入 50125711)')
    log('  6. restore  (恢复 50125461)')
    log('')

    patch_addr = None

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
                r = script.exports_sync.diff()
                if 'error' in r:
                    log(f'错误: {r["error"]}')
                else:
                    log(f'新增: {r["newCount"]} 处')
                    for a in r['addrs']:
                        log(f'  地址: {a}')
                    if r['newCount'] == 1:
                        patch_addr = r['addrs'][0]
                        log(f'自动选中: {patch_addr}')
                    elif r['newCount'] > 1:
                        log('多个新增地址，用 patch <addr> 手动指定')
            elif cmd == 'patch':
                addr = patch_addr
                if ' ' in cmd:
                    # handle "patch 0x..." if typed
                    pass
                if not addr:
                    log('没有目标地址，先 diff')
                    continue
                r = script.exports_sync.patch(addr)
                log(f'PATCH: {r["addr"]}  {r["old"]} → {r["new"]}')
            elif cmd.startswith('patch '):
                addr = cmd.split()[1]
                r = script.exports_sync.patch(addr)
                log(f'PATCH: {r["addr"]}  {r["old"]} → {r["new"]}')
            elif cmd == 'restore':
                if not patch_addr:
                    log('没有目标地址')
                    continue
                r = script.exports_sync.restore(patch_addr)
                log(f'RESTORE: {r["addr"]}  → {r["restored"]}')
            elif cmd.startswith('restore '):
                addr = cmd.split()[1]
                r = script.exports_sync.restore(addr)
                log(f'RESTORE: {r["addr"]}  → {r["restored"]}')
            else:
                log('命令: scan1 / scan2 / diff / patch / restore / quit')
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

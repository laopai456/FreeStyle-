"""
apollo_killer.py — 堵死Apollo杀进程通路 + 发型替换
v4: 完整反检测版（Interceptor + 调试端口隐藏 + Frida隐藏）

用法:
  1. 启动游戏登录到大厅
  2. python apollo_dump\apollo_killer.py
  3. 进房间 → 穿美丽梦想发型 → 等15秒看崩不崩
  4. status 查看计数 | quit 退出
"""
import sys, os, time, subprocess
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}')

def find_pid():
    try:
        r = subprocess.run(['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line: return int(line.split(',')[1].strip('"'))
    except: pass
    return None

def load_js():
    with open(os.path.join(SCRIPT_DIR, 'apollo_killer_v2.js'), 'r', encoding='utf-8') as f:
        return f.read()

def on_msg(msg, data):
    if msg['type'] != 'send': return
    p = msg['payload']
    t = p.get('t', '')
    tag = {'init': '[INIT]', 'step': '  ', 'ready': '', 'block_kill': '★ [堵杀]',
           'block_exit': '★ [堵退出]', 'block_err': '  [堵错误]',
           'apollo_nop': '  [Apollo检测]',
           'swallow_exception': '⊘ [吞系统异常]',
           'hair_patch': '  [发型替换]', 'lif_patch': '  [LoadItemFile替换]',
           'report': '[报告]', 'warn': '[警告]', 'ok': '[OK]',
           'fail': '[失败]', 'info': '[信息]'}.get(t, f'[{t}]')
    msg_text = p.get('msg', p.get('func', p.get('type', '')))
    extra = p.get('n', ''); extra_str = f' #{extra}' if extra else ''
    addr = p.get('addr', ''); addr_str = f' @ {addr}' if addr else ''
    status = p.get('status', ''); status_str = f' status={status}' if status else ''

    if t == 'ready':
        log('=' * 55)
        log(f'  {p["msg"]}')
        log('=' * 55)
        log('  进房间 → 穿美丽梦想发型 → 等待超过15秒')
        log('  命令: status | quit')
        log('')
    elif t == 'report':
        log(f'{tag} 堵杀={p.get("kills",0)} 退出={p.get("exits",0)} 吞异常={p.get("swallow",0)} 发型={p.get("hair",0)}')
    elif t == 'block_kill':
        log(f'{tag}{extra_str} {msg_text}{status_str}')
    elif t == 'swallow_exception':
        inNtdll = p.get('inNtdll', False)
        log(f'{tag} {msg_text}{addr_str}' + (' [ntdll]' if inNtdll else ''))
    elif t in ('apollo_nop',):
        log(f'{tag}{extra_str} {msg_text}{addr_str}')
    else:
        log(f'{tag}{extra_str} {msg_text}')

def main():
    import frida
    pid = find_pid()
    if not pid:
        log('FreeStyle.exe 未运行，请先启动游戏并登录')
        return 1
    log(f'Attached PID={pid}')

    session = frida.attach(pid)
    js_code = load_js()
    script = session.create_script(js_code)
    script.on('message', on_msg)
    script.load()

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'): break
            elif cmd == 'status':
                try: log(f'  {script.exports_sync.status()}')
                except: log('  (无法获取状态)')
    except (KeyboardInterrupt, EOFError): pass

    script.unload()
    session.detach()
    log('已断开')
    return 0

if __name__ == '__main__':
    sys.exit(main())
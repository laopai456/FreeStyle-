"""
hook_acquire_test.py — 实验: Memory.protect + Interceptor.attach AcquireSMD

用法:
  py hook_acquire_test.py

  启动后:
  1. 观察 SSKF 日志确认 hook 正常
  2. 在游戏大厅里输入 try  →  执行 protect + attach
  3. 如果游戏不崩 →  进商城点发型触发 AcquireSMD
  4. 看到 "HOOKED" 消息 = 成功!
"""
import sys, time, subprocess, frida
from datetime import datetime

def get_pid():
    try:
        r = subprocess.run(
            ['powershell', '-Command',
             "(Get-Process -Name FreeStyle* -ErrorAction SilentlyContinue | Select -First 1).Id"],
            capture_output=True, text=True)
        out = r.stdout.strip()
        return int(out) if (out and out.isdigit()) else None
    except:
        return None

def main():
    pid = get_pid()
    if not pid:
        print('FreeStyle.exe not running.')
        return

    out_path = datetime.now().strftime(r'D:\py\反编译\FreeStyle\apollo_dump\acquire_test_%Y%m%d_%H%M%S.txt')
    out = open(out_path, 'w', encoding='utf-8')

    def log(*args):
        line = ' '.join(str(x) for x in args)
        print(line)
        out.write(line + '\n')
        out.flush()

    log(f'Log: {out_path}')
    log(f'Attaching PID {pid}...')

    crashed = [False]  # mutable flag for nested scope

    def on_detached(reason, _crash):
        crashed[0] = True
        log(f'\n!!! PROCESS EXIT: reason={reason}, crash={_crash} !!!\n')
        if _crash:
            log('>>> Apollo.killprocess / crash detected <<<')

    session = frida.attach(pid)
    session.on('detached', on_detached)

    js = open(r'D:\py\反编译\FreeStyle\hook_acquire_test.js', encoding='utf-8').read()

    def on_msg(msg, _):
        if crashed[0]: return  # 崩后不再处理
        if msg['type'] == 'send':
            p = msg['payload']
            if not isinstance(p, dict):
                log(f'  {p}'); return
            t = p.get('t', '')

            if t == 'sskf':
                log(f'  SSKF #{p.get("n",0)}: {p.get("name","?")}  sz={p.get("sz",0)}')
                frames = p.get('frames', [])
                for f in frames:
                    marker = '>>>' if f['mod'] == 'FreeStyle.exe' else '   '
                    log(f'    {marker} {f["mod"]}+{f["off"]}  (ebp={f["ebp"]})')

            elif t in ('step1', 'step2', 'step3', 'step4'):
                log(f'  [{t}] {p.get("msg","")}')

            elif t == 'protect':
                log(f'  [PROTECT] {p.get("msg","")}')

            elif t == 'HOOKED':
                log(f'\n!!! {p.get("msg","")} !!!\n')

            elif t == 'ACQUIRE':
                log(f'  [ACQUIRE] ret=0x{p.get("off","?")}  name="{p.get("name","")}"')

            elif t == 'DIAG':
                log(f'  [DIAG #{p.get("n",0)}] ret=0x{p.get("ret","?")}  name="{p.get("name","")}"')

            elif t == 'SSTRING':
                names = p.get('names', [])
                if names:
                    log(f'  [SSTRING] names: {names}')
                else:
                    log(f'  [SSTRING] hex: {p.get("hex","")} NO_FILENAME')

            elif t in ('err', 'warn'):
                log(f'  [{t.upper()}] {p.get("msg","")}')

            elif t == 'ready':
                log(f'[*] {p.get("msg","")}')

            else:
                log(f'  [{t}] {p}')
        elif msg['type'] == 'error':
            log(f'[JS ERROR] {msg.get("description","")}')

    script = session.create_script(js)
    script.on('message', on_msg)
    script.load()
    time.sleep(0.3)

    log('\n=== Memory.protect + Interceptor.attach AcquireSMD ===')
    log('Commands: try  |  s (status)  |  Ctrl+C (exit)\n')
    log('步骤:')
    log('  1. 先在游戏里操作一下确认 SSKF 日志正常')
    log('  2. 输入 try → 保护代码页 + hook AcquireSMD')
    log('  3. 如果游戏没崩 → 进商城点发型')
    log('  4. 看到 "HOOKED" = 实验成功!\n')

    try:
        while True:
            try:
                cmd = input().strip().lower()
                if not cmd: continue

                if cmd == 'try':
                    try:
                        r = script.exports_sync.try_hook()
                        log(f'  → {r}')
                    except Exception as e:
                        log(f'  try failed: {e}')

                elif cmd in ('s', 'status'):
                    try:
                        r = script.exports_sync.status()
                        log(f'  n={r["n"]} hookTried={r["hookTried"]}')
                    except Exception as e:
                        log(f'  status: {e}')

                else:
                    log(f'  Unknown: {cmd}')

            except EOFError:
                break

    except KeyboardInterrupt:
        pass
    finally:
        log('\nDetaching...')
        try: script.unload()
        except: pass
        session.detach()
        out.close()
        log(f'Saved to {out_path}')

if __name__ == '__main__':
    main()
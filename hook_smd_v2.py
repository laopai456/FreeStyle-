"""
hook_smd_v2.py — 安全版: 只 hook ReadFile, 输出保存到 txt
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
    pid = None
    for a in sys.argv[1:]:
        if a.startswith('--pid='):
            pid = int(a.split('=', 1)[1])
        elif a == '--pid':
            continue

    if not pid:
        pid = get_pid()
    if not pid:
        print('FreeStyle.exe not found. Use --pid=NNNN.')
        return

    out_path = datetime.now().strftime(r'D:\py\反编译\FreeStyle\apollo_dump\smd_hook_%Y%m%d_%H%M%S.txt')
    out = open(out_path, 'w', encoding='utf-8')

    def log(*args):
        line = ' '.join(str(x) for x in args)
        print(line)
        out.write(line + '\n')
        out.flush()

    log(f'Output: {out_path}')
    log(f'Attaching to PID {pid}...')

    try:
        session = frida.attach(pid)
    except Exception as e:
        log(f'Attach failed: {e}')
        out.close()
        return

    js_path = r'D:\py\反编译\FreeStyle\hook_acquire_smd_v2.js'
    js = open(js_path, encoding='utf-8').read()

    def on_msg(msg, _):
        if msg['type'] == 'send':
            p = msg['payload']
            if not isinstance(p, dict):
                log(f'  {p}'); return
            t = p.get('t', '')

            if t == 'path':
                info = p.get('info', {})
                n = p.get('n', 0)
                sz = p.get('sz', 0)
                tag = '(hdr)' if sz == 512 else f'({sz//1024}KB)'
                log(f'\n[#{n}] sz={sz} {tag}  [{info.get("label","?")}]')
                log(f'  arg={info.get("arg","?")}')
                found = info.get('found', [])
                if found:
                    for f in found:
                        log(f'    {f}')
                else:
                    log(f'    (no strings found)')

            elif t == 'sskf':
                n = p.get('n', 0)
                sz = p.get('sz', 0)
                stack = p.get('stack', [])
                tag = '(hdr)' if sz == 512 else f'({sz//1024}KB)'
                log(f'\n[#{n}] SSKF sz={sz} {tag}')
                log(f'  Stack ({len(stack)} frames):')
                for f in stack:
                    if 'FreeStyle' in f:
                        log(f'    >>> {f} <<<')
                    else:
                        log(f'       {f}')

            elif t == 'ready':
                log(f'[*] {p.get("msg", "")}')

            else:
                log(f'[{t}] {p}')
        elif msg['type'] == 'error':
            log(f'[JS Error] {msg.get("description", "")}')

    script = session.create_script(js)
    script.on('message', on_msg)
    script.load()

    log('\nHook active. Trigger SMD loading (e.g. click hair in shop).')
    log('Press Ctrl+C to stop.\n')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log('\n\nDetaching...')
        try:
            script.unload()
        except:
            pass
        session.detach()
        out.close()
        log(f'Saved to {out_path}')


if __name__ == '__main__':
    main()
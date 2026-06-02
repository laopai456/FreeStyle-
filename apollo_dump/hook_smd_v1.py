"""
Hook DGraphicAcquireSMD — 诊断/重定向 SMD 模型加载

用法:
  py hook_smd.py                    诊断模式，记录所有 SMD 加载调用
  py hook_smd.py --pid <pid>        指定 PID
  py hook_smd.py --redirect <src> <dst>  重定向模式 (src→dst SMD路径)

示例:
  py hook_smd.py                              # 先跑诊断，看 SMD 路径
  py hook_smd.py --redirect i50122721 i50125721  # 把网红主播发型超赛替换
"""
import sys, time, subprocess, frida


def get_pid():
    try:
        r = subprocess.run(
            ['powershell', '-Command',
             "(Get-Process -Name FreeStyle* -ErrorAction SilentlyContinue | Select -First 1).Id"],
            capture_output=True, text=True)
        out = r.stdout.strip()
        if out and out.isdigit():
            return int(out)
    except Exception:
        pass
    return None


def main():
    pid = None
    redir = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--pid' and i + 1 < len(args):
            pid = int(args[i + 1]); i += 2
        elif args[i] == '--redirect' and i + 2 < len(args):
            redir = (args[i + 1], args[i + 2]); i += 3
        else:
            i += 1

    if not pid:
        pid = get_pid()
    if not pid:
        print('FreeStyle.exe not found. Use --pid.')
        return

    print(f'Attaching to PID {pid}...')
    session = frida.attach(pid)

    js = open('hook_acquire_smd.js', encoding='utf-8').read()

    def on_msg(msg, _):
        if msg['type'] == 'send':
            p = msg['payload']
            if not isinstance(p, dict):
                print(f'  {p}'); return
            t = p.get('t', '')
            if t == 'smd':
                strs = p.get('str', [])
                print(f'\n[SMD #{p["n"]}] at {p["at"]}')
                if isinstance(strs, list):
                    for s in strs:
                        if isinstance(s, dict):
                            print(f'  {s["where"]} d={s["d"]}: {s["s"]}')
                        else:
                            print(f'  {s}')
                else:
                    print(f'  {strs}')
            elif t == 'redirect':
                print(f'  >> REDIRECT: {p["from"]} -> {p["to"]} ({p.get("note","")})')
            elif t in ('info', 'loaded', 'warn'):
                print(f'[*] {p.get("msg", "")}')
            elif t == 'error':
                print(f'[!] {p.get("msg", "")}')
            else:
                print(f'[{t}] {p}')
        elif msg['type'] == 'error':
            print(f'[JS Error] {msg.get("description", "")}')

    script = session.create_script(js)
    script.on('message', on_msg)
    script.load()

    if redir:
        r = script.exports_sync.redirect(redir[0], redir[1])
        print(f'[*] {r}')

    print('Hook active. Ctrl+C to stop.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        st = script.exports_sync.status()
        print(f'\nTotal SMD calls: {st["calls"]}')
        print('Detaching...')
        script.unload()
        session.detach()


if __name__ == '__main__':
    main()

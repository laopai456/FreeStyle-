"""
smd_redirect.py — SMD 模型替换引擎 v3 (交互模式)

用法:
  py smd_redirect.py                        启动 hook + 交互命令模式

  启动后在提示符输入:
    r src dst    — 添加替换规则
    l            — 列出所有规则
    s            — 查看统计
    del src      — 删除规则
    clear        — 清除所有规则

  Ctrl+C 退出
"""
import sys, time, subprocess, frida, threading
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
        print('FreeStyle.exe not running. Start the game first.')
        return

    out_path = datetime.now().strftime(r'D:\py\反编译\FreeStyle\apollo_dump\smd_redirect_%Y%m%d_%H%M%S.txt')
    out = open(out_path, 'w', encoding='utf-8')

    def log(*args):
        line = ' '.join(str(x) for x in args)
        print(line)
        out.write(line + '\n')
        out.flush()

    log(f'Log: {out_path}')
    log(f'Attaching to PID {pid}...')

    session = frida.attach(pid)
    js = open(r'D:\py\反编译\FreeStyle\smd_redirect.js', encoding='utf-8').read()

    def on_msg(msg, _):
        if msg['type'] == 'send':
            p = msg['payload']
            if not isinstance(p, dict):
                print(f'  {p}'); return
            t = p.get('t', '')
            if t == 'diag':
                log(f'  DIAG SFullName* {p.get("sfn","?")}:')
                for k, v in p.get('info', {}).items():
                    log(f'    {k}: {v}')
            elif t == 'capture_start':
                log(f'  [CAP] capturing: {p["name"]}')
            elif t == 'captured':
                log(f'  [CAP] saved: {p["name"]} = {p["size"]} bytes ({p["chunks"]} chunks)')
            elif t == 'replaced':
                log(f'  [REPLACED] data written')
            elif t == 'file':
                log(f'  FILE: {p["name"]}  ({p.get("src","?")})')
            elif t == 'redir':
                log(f'[REDIRECT] {p["from"]} -> {p["to"]}')
                diag = p.get('diag', {})
                if diag:
                    for k, v in diag.items():
                        log(f'         {k}: "{v}"')
            elif t == 'rule':
                log(f'  RULE {p["from"]} -> {p["to"]}')
            elif t == 'map_add':
                log(f'  + {p["from"]} -> {p["to"]} ({p.get("count",0)} rules)')
            elif t in ('map_del', 'map_clear', 'reset'):
                log(f'  {t}: {p}')
            elif t == 'map_list':
                rules = p.get('rules', [])
                if rules:
                    for r in rules:
                        log(f'    {r}')
                else:
                    log('    (no rules)')
            elif t == 'status':
                log(f'  hits={p["hits"]} miss={p["misses"]} '
                    f'redir={p["redirected"]} rules={p["rules"]}')
            elif t == 'cmd_err':
                log(f'  [ERR] {p.get("line","")}: {p.get("err","")}')
            elif t == 'ready':
                log(f'[*] {p.get("msg","")}')
            else:
                log(f'  [{t}] {p}')
        elif msg['type'] == 'error':
            log(f'[ERROR] {msg.get("description","")}')

    script = session.create_script(js)
    script.on('message', on_msg)
    script.load()
    time.sleep(0.2)

    log('\nSMD redirect v8 (hFile-tracked byte stream). Commands:')
    log('  cap <name>      — capture next load of this file')
    log('  stop            — stop & save capture')
    log('  caps            — list captured')
    log('  r <src> <dst>   — redirect src body -> dst body')
    log('  info <name>     — show captured size')
    log('  l | s | clear   — list / stats / clear')
    log('  Ctrl+C          — exit\n')

    try:
        while True:
            try:
                cmd = input().strip()
                if not cmd:
                    continue

                parts = cmd.split(maxsplit=2)
                action = parts[0].lower()

                if action in ('r', 'redirect') and len(parts) >= 3:
                    try:
                        r = script.exports_sync.redirect(parts[1], parts[2])
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  redirect failed: {e}')

                elif action == 'l':
                    try:
                        r = script.exports_sync.list()
                        if isinstance(r, list):
                            for line in r:
                                print(f'    {line}')
                        else:
                            print(f'  {r}')
                    except Exception as e:
                        print(f'  list failed: {e}')

                elif action == 's':
                    try:
                        r = script.exports_sync.status()
                        print(f'  hits={r["hits"]} captured={r["captured"]} '
                              f'caps={r["caps"]} rules={r["rules"]}')
                    except Exception as e:
                        print(f'  status failed: {e}')

                elif action == 'cap':
                    try:
                        target = parts[1] if len(parts) >= 2 else ''
                        r = script.exports_sync.capture(target)
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  capture failed: {e}')

                elif action == 'stop':
                    try:
                        r = script.exports_sync.stopcap()
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  stop failed: {e}')

                elif action == 'caps':
                    try:
                        r = script.exports_sync.capts()
                        if isinstance(r, list):
                            for line in r:
                                print(f'  {line}')
                        else:
                            print(f'  {r}')
                    except Exception as e:
                        print(f'  capts failed: {e}')

                elif action == 'info' and len(parts) >= 2:
                    try:
                        r = script.exports_sync.info(parts[1])
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  info failed: {e}')

                elif action in ('del', 'remove') and len(parts) >= 2:
                    try:
                        r = script.exports_sync.remove(parts[1])
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  remove failed: {e}')

                elif action == 'reset':
                    try:
                        r = script.exports_sync.reset()
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  reset failed: {e}')

                elif action == 'clear':
                    try:
                        r = script.exports_sync.clear()
                        print(f'  {r}')
                    except Exception as e:
                        print(f'  clear failed: {e}')

                else:
                    print('  Unknown. Use: r src dst | cap | stop | caps | l | s | clear')

            except EOFError:
                break

    except KeyboardInterrupt:
        pass
    finally:
        log('\nDetaching...')
        try:
            s = script.exports_sync.status()
            log(f'Final: hits={s["hits"]} captured={s["captured"]} '
                f'redirected={s["redirected"]} replaced={s["replaced"]} '
                f'caps={s["caps"]} rules={s["rules"]}')
        except:
            pass
        try:
            script.unload()
        except:
            pass
        session.detach()
        out.close()
        log(f'Saved to {out_path}')


if __name__ == '__main__':
    main()
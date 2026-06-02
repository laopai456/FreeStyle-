# acquire_hook.py
# Python driver for acquire_hook.js
#
# Flow:
#   1. Auto-detect FreeStyle.exe PID
#   2. Inject acquire_hook.js via Frida
#   3. JS installs deception hooks, CRC patch, then ReadFile hook
#   4. When SSKF detected → scan stack for filename → cache target / replace source
#
# Usage:
#   py acquire_hook.py                     # auto PID + interactive
#   py acquire_hook.py <src> <dst>         # auto PID + set rule + wait
#   py acquire_hook.py --pid <PID>         # manual PID

import frida
import sys
import os
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(SCRIPT_DIR, 'acquire_hook.js')
LOG_FILE = os.path.join(SCRIPT_DIR, 'acquire_hook_log.txt')
_log_fh = None


def log_init():
    global _log_fh
    _log_fh = open(LOG_FILE, 'w', encoding='utf-8')
    _log_fh.write(f'=== acquire_hook log {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n')
    _log_fh.flush()


def log_write(text):
    if _log_fh:
        _log_fh.write(text + '\n')
        _log_fh.flush()


def out(text):
    print(text)
    log_write(text)


def find_pid():
    try:
        result = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                pid_str = line.split(',')[1].strip('"')
                return int(pid_str)
    except Exception as e:
        print(f'[!] tasklist failed: {e}')
    return None


def on_message(msg, data):
    if msg['type'] == 'send':
        payload = msg['payload']
        t = payload.get('t', '')

        if t == 'INIT':
            out(f'[*] {payload["msg"]}')
        elif t == 'SECTION':
            out(f'[*] .text: {payload["start"]} — {payload["end"]} ({payload["size"] / 1024 / 1024:.1f} MB)')
        elif t == 'DECEPTION':
            out(f'[STEP 0] {payload["msg"]}')
        elif t == 'DECEPTION_ERR':
            out(f'[!] DECEPTION ERROR: {payload["msg"]}')
        elif t == 'CRC':
            out(f'[STEP 0.5] {payload["msg"]}')
        elif t == 'CRC_ERR':
            out(f'[!] CRC ERROR: {payload["msg"]}')
        elif t == 'CRC_WARN':
            out(f'[*] CRC WARNING: {payload["msg"]}')
        elif t == 'READFILE':
            out(f'[STEP 1] {payload["msg"]}')
        elif t == 'READFILE_ERR':
            out(f'[!] READFILE ERROR: {payload["msg"]}')
        elif t == 'READY':
            out(f'\n{"="*60}')
            out(f'[READY] {payload["msg"]}')
            out(f'{"="*60}\n')
        elif t == 'SSKF':
            out(f'[SSKF #{payload["n"]}] {payload["size"]}B fname="{payload["fname"]}" (ESP+{payload["off"]:#x} {payload["type"]})')
        elif t == 'CACHE':
            out(f'[CACHE] {payload["item"]} → {payload["size"]}B cached from "{payload["fname"]}"')
        elif t == 'CACHE_ERR':
            out(f'[!] CACHE ERROR: {payload["err"]}')
        elif t == 'REPLACE':
            out(f'[REPLACE #{payload["count"]}] {payload["old"]} → {payload["new"]} ({payload["size"]}B)')
        elif t == 'REPLACE_SKIP':
            out(f'[SKIP] {payload["reason"]}: target={payload["targetSize"]}B buffer={payload["bufferSize"]}B')
        elif t == 'REPLACE_ERR':
            out(f'[!] REPLACE ERROR: {payload["err"]}')
        elif t == 'WAIT_TARGET':
            out(f'[*] {payload["msg"]}')
        elif t == 'CONFIG':
            out(f'[config] source="{payload["source"]}" target="{payload["target"]}"')
        elif t == 'STATUS':
            out(f'\n--- Status ---')
            out(f'  Source:     "{payload["source"]}"')
            out(f'  Target:     "{payload["target"]}"')
            out(f'  Replaces:   {payload["replaces"]}')
            out(f'  SSKF det:   {payload["sskf_detects"]}')
            out(f'  Cached:     {payload["cached"]}')
            out(f'  Deception:  active={payload.get("deception_active", False)}, VQ lies={payload.get("vq_lies", 0)}, VP fakes={payload.get("vp_fakes", 0)}')
            out(f'--------------\n')
        elif t == 'RESET':
            out(f'[reset] {payload["msg"]}')
        elif t == 'FAIL':
            out(f'\n[FAIL] {payload["msg"]}')
        else:
            out(f'[msg] {t}: {payload}')

    elif msg['type'] == 'error':
        out(f'[JS ERROR] {msg.get("description", msg)}')
        if 'stack' in msg:
            out(f'  Stack: {msg["stack"]}')


def interactive_loop(script):
    print('Commands:')
    print('  src <itemcode>       — Set source item code (e.g. src i50123971)')
    print('  dst <itemcode>       — Set target item code (e.g. dst i50125711)')
    print('  rule <src> <dst>     — Set both at once')
    print('  s / status           — Show status')
    print('  r / reset            — Reset counters')
    print('  q / quit             — Exit')
    print()

    while True:
        try:
            cmd = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n[exit]')
            break

        if not cmd:
            continue

        parts = cmd.split()
        op = parts[0].lower()

        if op in ('q', 'quit', 'exit'):
            break
        elif op == 'src' and len(parts) >= 2:
            script.exports.set_source(parts[1])
        elif op == 'dst' and len(parts) >= 2:
            script.exports.set_target(parts[1])
        elif op == 'rule' and len(parts) >= 3:
            script.exports.set_rule(parts[1], parts[2])
        elif op in ('s', 'status'):
            script.exports.status()
        elif op in ('r', 'reset'):
            script.exports.reset_counters()
        else:
            print(f'[?] Unknown command: {cmd}')
            print('    src <code> | dst <code> | rule <src> <dst> | s[tatus] | r[eset] | q[uit]')


def main():
    pid = None
    src_item = None
    dst_item = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--pid' and i + 1 < len(args):
            pid = int(args[i + 1])
            i += 2
        elif not src_item and not args[i].startswith('--'):
            src_item = args[i]
            i += 1
        elif not dst_item and not args[i].startswith('--'):
            dst_item = args[i]
            i += 1
        elif args[i].startswith('--'):
            print(f'[!] Unknown flag: {args[i]}')
            i += 1
        else:
            i += 1

    if pid is None:
        print('[*] Finding FreeStyle.exe PID...')
        pid = find_pid()
        if pid is None:
            print('[!] FreeStyle.exe not found. Start the game first.')
            print('    Or specify --pid <PID>')
            sys.exit(1)
    print(f'[+] PID: {pid}')

    log_init()
    log_write(f'PID: {pid}')

    print(f'[*] Attaching to PID {pid}...')
    try:
        session = frida.attach(pid)
    except frida.ProcessNotFoundError:
        print(f'[!] Process {pid} not found')
        sys.exit(1)
    except Exception as e:
        print(f'[!] Attach failed: {e}')
        sys.exit(1)

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)
    script.on('message', on_message)
    script.load()
    print(f'[+] Script loaded. Waiting for init...\n')

    time.sleep(2)

    if src_item and dst_item:
        time.sleep(1)
        try:
            script.exports.set_rule(src_item, dst_item)
        except Exception as e:
            print(f'[!] set_rule failed: {e}')

        print(f'[*] Rule set: {src_item} → {dst_item}')
        print(f'[*] Load TARGET item first (to cache), then load SOURCE item (to replace).')
        print(f'[*] Press Ctrl+C to exit.\n')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print('\n[exit]')
    else:
        interactive_loop(script)

    try:
        session.detach()
    except Exception:
        pass
    if _log_fh:
        _log_fh.close()
    print('[done]')


if __name__ == '__main__':
    main()
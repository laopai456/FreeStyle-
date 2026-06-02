"""
apollo_destroyer.py — Apollo 拆除工具 (Python 驱动)
用法: py apollo_destroyer.py
"""
import frida
import subprocess
import os
import time
import sys
from datetime import datetime

DUMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_dump')
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apollo_destroyer.js')

def find_pid():
    r = subprocess.run(['tasklist','/FI','IMAGENAME eq FreeStyle.exe','/FO','CSV','/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if 'freestyle' in line.lower():
            parts = line.split(',')
            if len(parts) >= 2:
                return int(parts[1].strip('"'))
    return None

def do_phase1():
    """Stop Apollo.sys + kill ApolloGuardian (runs locally, not in JS)"""
    # Kill watchdog ONLY (NOT FreeStyle.exe — game may be running)
    subprocess.run(['taskkill','/f','/im','ApolloGuardian.exe'],
                   capture_output=True)

    # Stop service
    r = subprocess.run(['sc.exe','stop','ApolloProtect'],
                       capture_output=True, text=True)
    print('sc stop ApolloProtect:')
    print(r.stdout)

    # Verify
    r = subprocess.run(['sc.exe','query','ApolloProtect'],
                       capture_output=True, text=True)
    print('sc query ApolloProtect:')
    print(r.stdout)

    if 'STOPPED' in r.stdout:
        print('[Phase 1 OK] ApolloProtect STOPPED.')
        return True
    else:
        print('[Phase 1 FAIL] ApolloProtect still RUNNING! Run as admin?')
        return False

def main():
    skip_phase1 = '--skip-phase1' in sys.argv

    print('=== Apollo Destroyer ===')
    if not skip_phase1:
        print('Phase 1: Stopping Apollo.sys ...')
        if not do_phase1():
            return
        print('Phase 1 OK. Now launch FreeStyle.exe DIRECTLY (skip launcher):')
        print(r'  "C:\Program Files (x86)\T2CN\街头篮球\FreeStyle.exe"')
        input('Press Enter after game reaches lobby (character visible)...')
    else:
        print('Phase 1 skipped (already done)')

    pid = find_pid()
    if not pid:
        print('[ERROR] FreeStyle.exe not running. Start the game first.')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(DUMP_DIR, f'destroyer_{ts}.txt')
    os.makedirs(DUMP_DIR, exist_ok=True)
    log = open(log_path, 'w', encoding='utf-8')

    def log_msg(msg):
        print(msg)
        log.write(msg + '\n')
        log.flush()

    log_msg(f'Log: {log_path}')
    log_msg(f'Attaching PID {pid}...')

    session = frida.attach(pid)

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)

    def on_msg(msg, data):
        if msg['type'] == 'error':
            log_msg(f'  [JS ERROR] {msg.get("description", msg)}')
            return
        p = msg.get('payload', {})
        t = p.get('t', '')
        msg_str = p.get('msg', '')
        if t in ('PHASE2', 'PHASE3', 'PHASE35', 'PHASE4'):
            log_msg(f'  {msg_str}')
        elif t == 'APOLLO_THREAD':
            log_msg(f'  [APOLLO] TID={p["id"]} EIP={p["eip"]} apolloFrames={p["apolloFrames"]}/{p["totalFrames"]}')
        elif t == 'SUSPEND':
            log_msg(f'  [SUSPEND] TID={p["id"]} OK')
        elif t == 'SUSPEND_FAIL':
            log_msg(f'  [SUSPEND] TID={p["id"]} FAILED')
        elif t == 'APOLLO2_THREAD':
            log_msg(f'  [APOLLO2] TID={p["id"]} EIP={p["eip"]}')
        elif t == 'L2_THREAD':
            log_msg(f'  [L2] TID={p["id"]} EIP={p["eip"]}')
        elif t == 'SSREF_HITS':
            if 'err' in p:
                log_msg(f'  [SSREF] Error: {p["err"]}')
            else:
                log_msg(f'  [SSREF] {p["count"]} hits: {p.get("addrs", [])}')
        elif t == 'SSKF_HITS':
            if 'err' in p:
                log_msg(f'  [SSKF] Error: {p["err"]}')
            else:
                log_msg(f'  [SSKF] {p["count"]} hits: {p.get("addrs", [])}')
        elif t == 'ATTACH_OK':
            log_msg(f'  [ATTACH] {msg_str}')
        elif t == 'ATTACH_FAIL':
            log_msg(f'  [ATTACH] FAIL: {msg_str}')
        elif t == 'DONE':
            log_msg(f'  === {msg_str} ===')
        elif t == 'READY':
            log_msg(f'  [READY] {msg_str}')
        elif t == 'STATUS':
            log_msg(f'  [STATUS] base={p["base"]} size={p["size"]}')
        else:
            log_msg(f'  [{t}] {p}')

    script.on('message', on_msg)
    script.load()

    session.on('detached', lambda reason, crash:
        log_msg(f'\n!!! PROCESS EXIT: reason={reason}, crash={crash} !!!'))

    print('\nCommands: killAll | phase2 | phase3 | phase35 | phase4 | status | Ctrl+C')
    print('  killAll  = Run all phases (2 → 3.5 → 3 → 4)')
    print('  phase2   = Suspend ApolloCT threads')
    print('  phase35  = Suspend Apollo2.dll + L2 threads')
    print('  phase3   = Unlock .text RWX')
    print('  phase4   = Search AcquireSMD + verify Interceptor\n')

    rpc = script.exports_sync

    try:
        while True:
            cmd = input('>>> ').strip()
            if not cmd:
                continue
            if cmd == 'killAll':
                rpc.killall()
            elif cmd == 'phase2':
                rpc.phase2()
            elif cmd == 'phase3':
                rpc.phase3()
            elif cmd == 'phase35':
                rpc.phase35()
            elif cmd == 'phase4':
                rpc.phase4()
            elif cmd == 'status':
                rpc.status()
            elif cmd in ('q', 'quit', 'exit'):
                break
            else:
                print(f'  Unknown: {cmd}')
    except KeyboardInterrupt:
        print('\nDetaching...')
    finally:
        session.detach()
        log.close()
        print(f'\nDone. Log: {log_path}')

if __name__ == '__main__':
    main()
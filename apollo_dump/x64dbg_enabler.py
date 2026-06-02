# x64dbg_enabler.py
# 让 x32dbg 安全附加 FreeStyle.exe (32-bit 游戏, 必须用 x32dbg)
#
# 步骤:
#   1. 管理员: sc stop ApolloProtect + taskkill ApolloGuardian.exe
#   2. 正常启动游戏 (不走启动器, 直接 FreeStyle.exe)
#   3. 等游戏完全加载 (进到登录/大厅界面)
#   4. py x64dbg_enabler.py
#   5. 看到 READY 后打开 x32dbg 附加 FreeStyle.exe
#   6. 不要关闭本窗口 (Frida 需要保持运行维持 hook)

import frida
import sys
import os
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(SCRIPT_DIR, 'x64dbg_enabler.js')


def find_pid():
    try:
        result = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except Exception as e:
        print(f'[!] tasklist failed: {e}')
    return None


def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')

        if t == 'INIT':
            print(f'[*] {p["msg"]}')
        elif t == 'SECTION':
            print(f'[*] .text: {p["size"]/1024/1024:.1f} MB ({p["start"]} - {p["end"]})')
        elif t == 'STEP':
            print(f'  {p["msg"]}')
        elif t == 'READY':
            print(f'\n{"="*60}')
            print(f'[READY] {p["msg"]}')
            print(f'{"="*60}')
            print(f'\n  >>> 打开 x32dbg (32-bit!), 附加 FreeStyle.exe <<<')
            print(f'  >>> 不要关闭本窗口 <<<\n')
        elif t == 'SCAN_PROFILE':
            print(f'\n--- Apollo Scan Profile ---')
            stats = p.get('stats', {})
            anomaly = p.get('anomaly', {})
            if 'msg' in stats:
                print(f'  {stats["msg"]}')
            else:
                print(f'  Apollo scans:   {stats.get("apolloScans", 0)}')
                print(f'  Total NtQVM:    {stats.get("totalNtQVM", 0)}')
                print(f'  Scan period:    {stats.get("periodMs", "N/A")} ms (avg over {stats.get("sampleCount", 0)} samples)')
                print(f'  Min/Max/Avg:    {stats.get("minIntervalMs", "N/A")} / {stats.get("maxIntervalMs", "N/A")} / {stats.get("avgIntervalMs", "N/A")} ms')
            print(f'  VQ lies:        {p.get("vq_lies", 0)}')
            print(f'  VP fakes:        {p.get("vp_fakes", 0)}')
            print(f'  Anomalies:       bypass={anomaly.get("bypassAttempts", 0)} ER_leaks={anomaly.get("erLeaks", 0)}')
            print(f'---------------------------\n')
        elif t == 'SAFETY':
            print(f'[SAFETY] {p["msg"]}')
        elif t == 'UNLOCK':
            print(f'[UNLOCK] {"OK" if p.get("ok") else "FAIL"}')
        elif t == 'FAIL':
            print(f'[FAIL] {p["msg"]}')
        elif t == 'WARN':
            print(f'[WARN] {p["msg"]}')
        elif t == 'STATUS':
            print(f'\n--- Status ---')
            print(f'  Deception:  {"ON" if p["deception"] else "OFF"} (VQ lies:{p["vq_lies"]} VP fakes:{p["vp_fakes"]})')
            print(f'  CRC:        {"OK" if p["crc"] else "FAIL"}')
            print(f'  Anti-debug: {"ON" if p["antidebug"] else "OFF"} (PEB patches:{p["peb_patches"]})')
            scan = p.get('scan', {})
            anomaly = p.get('anomaly', {})
            if 'periodMs' in scan:
                print(f'  Scan cycle: {scan["periodMs"]}ms (Apollo calls:{scan.get("apolloScans", "?")})')
            if anomaly.get('erLeaks', 0) > 0:
                print(f'  [!] Anomalies: {anomaly["erLeaks"]} ER leaks!')
            print(f'--------------\n')
        elif t == 'DIAG':
            print(f'[DIAG] {p["msg"]}')
        elif t == 'APOLLO_THREAD':
            print(f'  [ApolloCT] {p["msg"]}')
        else:
            print(f'[{t}] {p.get("msg", p)}')
    elif msg['type'] == 'error':
        print(f'[JS ERROR] {msg.get("description", msg)}')


def main():
    pid = None
    args = sys.argv[1:]
    if '--pid' in args:
        idx = args.index('--pid')
        if idx + 1 < len(args):
            pid = int(args[idx + 1])

    if pid is None:
        print('[*] Finding FreeStyle.exe...')
        pid = find_pid()
        if pid is None:
            print('[!] FreeStyle.exe not found. Start game first.')
            sys.exit(1)
    print(f'[+] PID: {pid}')

    print('[*] Attaching...')
    try:
        session = frida.attach(pid)
    except Exception as e:
        print(f'[!] Attach failed: {e}')
        sys.exit(1)

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()

    script = session.create_script(js_code)
    script.on('message', on_message)
    script.load()
    print('[*] Script loaded, waiting for init...\n')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[exit]')
    try:
        session.detach()
    except:
        pass
    print('[done]')


if __name__ == '__main__':
    main()

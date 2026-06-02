"""
inject_test.py — TCP 包注入测试

用法:
  1. 用 apollo_launcher.py 启动游戏并手动登录
  2. 另开终端运行: py inject_test.py <pid>
  3. 等待 "socket captured" 后输入命令

命令:
  status          — 查看状态 (socket, 包计数, 最后包)
  last            — 重放最后一个包
  raw <hex>       — 注入自定义 hex 包
  hex             — 显示最后包的完整 hex
  loop            — 每 2 秒重放最后一个包 (心跳模拟)
  stop            — 停止循环
  quit            — 退出
"""
import frida
import json
import sys
import time
import threading

JS_FILE = "frida_inject.js"

g_script = None
g_running = True
g_looping = False
g_loop_thread = None

def on_message(msg, data):
    if msg['type'] != 'send':
        print(f"  [FRIDA] {msg}")
        return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except:
            print(f"  [JS] {p}")
            return
    t = p.get('type', '')
    if t == 'PKT':
        print(f"  [PKT #{p['idx']}] len={p['len']} head={p['head']}")
    elif t == 'info':
        print(f"  [*] {p['msg']}")
    elif t == 'warn':
        print(f"  [!] {p['msg']}")
    elif t == 'hcopy_patch':
        print(f"  [HCOPY] Patched desc={p.get('desc','')} {p.get('old','')}->{p.get('new','')}")
    elif t == 'TRACE':
        print(f"  [TRACE] seq={p.get('seq','')} call stack:")
        for i, f in enumerate(p.get('frames', [])):
            print(f"    #{i} {f}")
    elif t == 'err':
        print(f"  [ERR] {p['msg']}")
    else:
        print(f"  [{t}] {p}")

def rpc(fn, *args):
    if not g_script:
        print("  Not attached yet")
        return None
    try:
        result = getattr(g_script.exports_sync, fn)(*args)
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception as e:
        print(f"  RPC error: {e}")
        return None

def do_status():
    r = rpc('status')
    if r:
        print(f"  Socket: {r['socket']}")
        print(f"  Sent:   {r['sentCount']} packets")
        print(f"  Last:   {r['lastLen']} bytes, head={r['lastHead']}")

def do_last():
    r = rpc('injectlast')
    if r:
        if r.get('ok'):
            print(f"  SENT OK! {r.get('sent', '?')}/{r.get('size', '?')} bytes")
        else:
            print(f"  INJECT FAILED: {r.get('msg', '')} err={r.get('err', 0)}")

def do_next():
    r = rpc('injectnext')
    if r:
        if r.get('ok'):
            f12 = r.get('f12', '?')
            f12_str = f"0x{f12:08X}" if isinstance(f12, int) and f12 >= 0 else 'N/A'
            print(f"  SENT OK! seq={r.get('seq','?')} f12={f12_str} {r.get('sent','?')}/{r.get('size','?')} bytes")
        else:
            print(f"  INJECT FAILED: {r.get('msg','')} err={r.get('err',0)}")

def do_heartbeat():
    r = rpc('injectheartbeat')
    if r:
        if r.get('ok'):
            print(f"  HEARTBEAT OK! seq={r.get('seq')} f12=0x{r.get('f12',0):08X} len={r.get('pktlen')} sent={r.get('sent')}/{r.get('size')}")
        else:
            print(f"  HEARTBEAT FAILED: {r.get('msg','')}")

def do_info():
    r = rpc('getlastinfo')
    if r and r.get('ok'):
        match = "MATCH" if r.get('f12_match') else "MISMATCH!"
        seed_info = f"  seed=0x{r['seed']:08X} ({'auto' if r.get('seedDetected') else 'default'})" if 'seed' in r else ""
        print(f"  seq={r['seq']}  f12_actual=0x{r['f12_actual']:08X}  f12_expected=0x{r['f12_expected']:08X}  [{match}]")
        print(f"  len={r['len']}  session={r['session']}  enc_head={r['enc_head']}{seed_info}")
    else:
        print(f"  No packet captured")

def do_f12(seq_str):
    r = rpc('getf12', seq_str)
    if r:
        if r.get('ok'):
            print(f"  f12({r['seq']}) = 0x{r['f12']:08X}")
        else:
            print(f"  f12({r['seq']}) not in table")

def do_decrypt():
    r = rpc('decryptlast')
    if r and r.get('ok'):
        print(f"  seq={r['seq']}  f12=0x{r['f12']:08X}  total={r['totalLen']}B  payload={r['payloadLen']}B")
        print(f"  b0=0x{r['b0']:02X}  b1=0x{r['b1']:02X}  session={r['session']}")
        print(f"  header:     {r['header']}")
        print(f"  enc_pay:    {r['encPayload']}")
        dp = r['decPayload']
        print(f"  dec_pay:    {dp}")
        if r.get('decFull') and len(r['decFull']) > len(dp):
            print(f"  dec_full:   {r['decFull']}")
    else:
        print(f"  No packet captured")

def do_raw(hexdata):
    hexdata = hexdata.replace(' ', '')
    r = rpc('injectraw', hexdata)
    if r:
        if r['ok']:
            print(f"  INJECTED OK! sent={r['sent']}/{r['size']} bytes")
        else:
            print(f"  INJECT FAILED: {r.get('msg', '')} err={r.get('err', 0)}")

def do_get_last():
    r = rpc('getlastraw')
    if r and r.get('hex'):
        h = r['hex']
        print(f"  Last packet ({r['len']} bytes):")
        for i in range(0, len(h), 64):
            print(f"    {h[i:i+64]}")

def do_loop():
    global g_looping, g_loop_thread
    if g_looping:
        print("  Already looping")
        return
    g_looping = True
    def _loop():
        while g_looping:
            r = rpc('injectlast')
            if r:
                ts = time.strftime("%H:%M:%S")
                ok = "OK" if r.get('ok') else f"FAIL(err={r.get('err', '?')})"
                print(f"  [{ts}] inject: {ok} sent={r.get('sent', '?')}/{r.get('size', '?')}")
            time.sleep(2)
    g_loop_thread = threading.Thread(target=_loop, daemon=True)
    g_loop_thread.start()
    print("  Loop started (every 2s). Type 'stop' to stop.")

def do_stop():
    global g_looping
    g_looping = False
    print("  Loop stopped")

def do_toggle_pkt():
    r = rpc('toggleqt')
    if r:
        state = "OFF (quiet)" if r.get('quiet') else "ON (verbose)"
        print(f"  PKT logging: {state}")

def do_patch_start(src, dst):
    r = rpc('patchic', 'start', src, dst)
    if r:
        print(f"  ItemCode patch: {r.get('srcIC')} -> {r.get('dstIC')} ({r.get('msg')})")

def do_patch_stop():
    r = rpc('patchic', 'stop', 0, 0)
    if r:
        print(f"  ItemCode patch: {r.get('msg')} src={r.get('srcIC')}")

def do_hcopy_start(src, dst):
    # 直接调用 frida_inject.js 里的 hcopy RPC
    r = rpc('hcopy', src, dst)
    if r:
        print(f"  Copy ctor hook: {r.get('srcIC')} -> {r.get('dstIC')} ({r.get('msg')})")

def do_hcopy_stop():
    r = rpc('unhcopy')
    if r:
        print(f"  Copy ctor hook: {r.get('msg')}")

def main():
    global g_script, g_running

    # 自动获取 PID
    if len(sys.argv) >= 2:
        pid = int(sys.argv[1])
    else:
        import subprocess
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                                capture_output=True, text=True)
        lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
        pids = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                pids.append(int(parts[1]))
        if not pids:
            print("[ERROR] FreeStyle.exe not found")
            return
        pid = pids[0]
        if len(pids) > 1:
            print(f"Multiple processes found: {pids}, using PID {pid}")

    print(f"Attaching to PID {pid}...")

    try:
        session = frida.attach(pid)
    except Exception as e:
        print(f"Attach failed: {e}")
        return

    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js = f.read()

    g_script = session.create_script(js)
    g_script.on('message', on_message)
    g_script.load()
    print("Script loaded. Commands: status/last/next/heartbeat/hex/info/decrypt/f12/loop/stop/patch/quit")
    print("")

    try:
        while g_running:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue
            parts = cmd.split(None, 1)
            op = parts[0].lower()

            if op == 'quit' or op == 'q':
                break
            elif op == 'status' or op == 's':
                do_status()
            elif op == 'last' or op == 'l':
                do_last()
            elif op == 'next' or op == 'n':
                do_next()
            elif op == 'raw' or op == 'r':
                if len(parts) < 2:
                    print("  Usage: raw <hex>")
                else:
                    do_raw(parts[1])
            elif op == 'hex' or op == 'h':
                do_get_last()
            elif op == 'heartbeat' or op == 'hb':
                do_heartbeat()
            elif op == 'info' or op == 'i':
                do_info()
            elif op == 'decrypt' or op == 'd':
                do_decrypt()
            elif op == 'f12':
                if len(parts) < 2:
                    print("  Usage: f12 <seq>")
                else:
                    do_f12(parts[1])
            elif op == 'loop':
                do_loop()
            elif op == 'stop':
                do_stop()
            elif op == 'pkton' or op == 'p':
                do_toggle_pkt()
            elif op == 'patch':
                patch_parts = cmd.split()
                if len(patch_parts) < 3 or patch_parts[1] == 'stop':
                    if len(patch_parts) >= 2 and patch_parts[1] == 'stop':
                        do_patch_stop()
                    else:
                        print("  Usage: patch <src_itemcode> <dst_itemcode>")
                        print("         patch stop")
                else:
                    try:
                        do_patch_start(int(patch_parts[1]), int(patch_parts[2]))
                    except ValueError:
                        print("  Invalid itemcode (must be integer)")
            elif op == 'hcopy':
                hcopy_parts = cmd.split()
                if len(hcopy_parts) < 3 or hcopy_parts[1] == 'stop':
                    if len(hcopy_parts) >= 2 and hcopy_parts[1] == 'stop':
                        do_hcopy_stop()
                    else:
                        print("  Usage: hcopy <src_itemcode> <dst_itemcode>")
                        print("         hcopy stop")
                else:
                    try:
                        do_hcopy_start(int(hcopy_parts[1]), int(hcopy_parts[2]))
                    except ValueError:
                        print("  Invalid itemcode")
            elif op == 'trace':
                r = rpc('trace', True)
                if r:
                    state = "ON" if r.get('trace') else "OFF"
                    print(f"  Call trace: {state} (auto on equip packets)")
            elif op == 'notrace':
                r = rpc('trace', False)
                if r:
                    print(f"  Call trace: OFF")
            else:
                print(f"  Unknown: {op}")

    finally:
        g_looping = False
        try: g_script.unload()
        except: pass
        try: session.detach()
        except: pass
        print("Done.")

if __name__ == '__main__':
    main()

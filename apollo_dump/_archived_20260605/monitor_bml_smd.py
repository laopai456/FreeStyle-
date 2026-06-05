"""
monitor_bml_smd.py — 监控游戏读取BML和加载SMD的全过程
用途: 确认BML路径替换后游戏是否正确读到新mesh路径，BML大小变化是否影响读取
用法: py monitor_bml_smd.py [itemcode]
  不带itemcode: 监控所有BML读取
  带itemcode: 只监控该物品
示例:
  py monitor_bml_smd.py 50125461       # 50125461=美丽梦想发型(pak767)
  py monitor_bml_smd.py 50125711       # 50125711=紫色超赛发型(pak768)
"""
import sys, os, time
import frida

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def main():
    target_ic = sys.argv[1] if len(sys.argv) > 1 else None

    pid = find_pid()
    if not pid:
        print("FreeStyle.exe 未运行")
        sys.exit(1)

    print(f"PID: {pid}" + (f" | 监控物品: {target_ic}" if target_ic else " | 监控全部"))
    session = frida.attach(pid)

    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor_bml_smd.js")
    with open(js_path, encoding='utf-8') as f:
        js = f.read()
    if target_ic:
        js = js.replace('__TARGET_IC__', target_ic)
    else:
        js = js.replace('__TARGET_IC__', '')

    script = session.create_script(js)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('type', '')
            if t == 'bml_read':
                print(f"  [BML] {p['itemcode']} ({p['size']}B)")
                if p.get('mesh_paths'):
                    for m in p['mesh_paths']:
                        print(f"    mesh: {m}")
            elif t == 'smd_load':
                print(f"  [SMD加载] {p['path']}")
            elif t == 'info':
                print(f"  [INFO] {p['msg']}")
            elif t == 'error':
                print(f"  [ERR] {p['msg']}")
            else:
                print(f"  [{t}] {p}")
        elif msg['type'] == 'error':
            print(f"  [JS错误] {msg.get('description','')}")

    script.on('message', on_msg)
    script.load()

    print("监控已启动，触发角色加载...\n")
    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd in ('quit','q','exit'):
                break
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()

if __name__ == '__main__':
    main()

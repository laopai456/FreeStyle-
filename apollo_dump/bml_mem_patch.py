"""
bml_mem_patch.py — 内存里拦截BML替换mesh路径，不改pak文件
用途: 验证BML路径替换本身是否能让游戏加载新mesh
用法: py bml_mem_patch.py  # 美丽梦想发型(50125461,pak767) → 紫色超赛(50125711,pak768)
"""
import sys, os
import frida

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def main():
    pid = find_pid()
    if not pid:
        print("FreeStyle.exe 未运行")
        sys.exit(1)

    print(f"PID: {pid} | 美丽梦想(50125461) → 紫色超赛(50125711)")
    session = frida.attach(pid)

    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bml_mem_patch.js")
    with open(js_path, encoding='utf-8') as f:
        js = f.read()

    script = session.create_script(js)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('type', '')
            if t == 'file_open':
                print(f"  [FILE] CreateFileW → {p['path']}")
            elif t == 'file_open_a':
                print(f"  [FILE] CreateFileA → {p['path']}")
            elif t == 'bml_read':
                meshes = ', '.join(p.get('meshes', []))
                print(f"  [BML] i{p['itemcode']} ({p['size']}B) meshes: {meshes}")
            elif t == 'patched':
                after = ', '.join(p.get('after_meshes', []))
                print(f"  [PATCHED] i{p['item']} — {p['patches']}处替换 → meshes: {after}")
            elif t == 'info':
                print(f"  [INFO] {p['msg']}")
            elif t == 'error':
                print(f"  [ERR] {p['msg']}")
        elif msg['type'] == 'error':
            print(f"  [JS错误] {msg.get('description','')}")

    script.on('message', on_msg)
    script.load()

    print("内存补丁已激活，触发角色加载...\n")
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

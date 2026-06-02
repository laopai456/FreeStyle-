# hook_factory.py - hook对象工厂，捕获发型Actor创建
import sys, os, frida
sys.stdout.reconfigure(encoding='utf-8')

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    session = frida.attach(pid)

    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hook_factory.js')
    with open(js_path, encoding='utf-8') as f:
        js = f.read()

    script = session.create_script(js)

    statics = []
    dynamics = []

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('type', '')
            if t == 'static_created':
                statics.append(p['obj'])
                print(f"  [STATIC创建] {p['obj']} vtable={p['vtable']} +8={p['field_8']}")
            elif t == 'dynamic_created':
                dynamics.append(p['obj'])
                print(f"  [DYNAMIC创建] {p['obj']} vtable={p['vtable']} +8={p['field_8']}")
            elif t == 'set_motion':
                print(f"  [SetMotion] {p['obj']} motion={p['motion']} actor={p['actor_type']} +8={p['field_8']}")
            elif t == 'info':
                print(f"  [INFO] {p['msg']}")
            elif t == 'error':
                print(f"  [ERR] {p['msg']}")
        elif msg['type'] == 'error':
            print(f"  [JS错误] {msg.get('description','')}")

    script.on('message', on_msg)
    script.load()

    print('Hook已激活，进房间触发角色加载...\n')
    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'list':
                print(f'  Static: {len(statics)} 个')
                for s in statics: print(f'    {s}')
                print(f'  Dynamic: {len(dynamics)} 个')
                for d in dynamics: print(f'    {d}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()

if __name__ == '__main__':
    main()

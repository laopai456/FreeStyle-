r"""
hook_bml.py — BML 拦截: 在 ReadFile 层面替换 BML 中的 mesh/texture 路径

原理:
  游戏加载道具时 ReadItemFile 从 pak 读取 BML (小 XML 文件)，
  BML 中包含 mesh="res764\i50122721_MT.smd" 这样的路径。
  本脚本 hook ReadFile，检测到 BML 内容后把源 ItemCode 替换为目标 ItemCode。
  由于是等长替换，不影响 XML 结构。

用法:
  1. 启动 FreeStyle，登录进大厅
  2. py hook_bml.py <source_itemcode> <target_itemcode>
     例: py hook_bml.py 50122721 50125711
  3. 触发角色加载 (进房间 / 查看角色 / 商城试用)
  4. 脚本自动拦截 BML 并替换 mesh 路径

命令: start | stop | stats | quit
"""
import sys, os, time
import frida

def find_pid():
    """查找 FreeStyle.exe 进程"""
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def main():
    if len(sys.argv) < 3:
        print(f"用法: py {sys.argv[0]} <source_itemcode> <target_itemcode>")
        print(f"例:   py {sys.argv[0]} 50122721 50125711")
        print(f"注意: source 和 target 必须等长")
        sys.exit(1)

    source = sys.argv[1]
    target = sys.argv[2]
    if len(source) != len(target):
        print(f"错误: source({len(source)}) 和 target({len(target)}) 长度不同")
        sys.exit(1)

    pid = find_pid()
    if not pid:
        print("错误: FreeStyle.exe 未运行")
        sys.exit(1)

    print(f"FreeStyle.exe PID: {pid}")
    session = frida.attach(pid)

    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_bml.js")
    with open(js_path, encoding='utf-8') as f:
        js = f.read()
    js = js.replace('var SOURCE = "__SOURCE__";', f'var SOURCE = "{source}";')
    js = js.replace('var TARGET = "__TARGET__";', f'var TARGET = "{target}";')

    script = session.create_script(js)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('type', '')
            if t == 'ready':
                print(f"Hook 就绪: {p['source']} -> {p['target']}")
            elif t == 'bml_detected':
                enc = "XOR" if p.get('encrypted') else "raw"
                pv = p.get('preview', '')[:150].replace('\n', ' ')
                print(f"  [BML] {p['size']}B ({enc}): {pv}")
            elif t == 'bml_patched':
                print(f"  [PATCH] 替换 {p['count']} 处, offset={p['offset']}, enc={p.get('encrypted')}")
            elif t == 'stats':
                print(f"  Total:{p['total']}  Small:{p['small']}  BML:{p['bml']}  Patched:{p['patched']}")
            elif t == 'status':
                if 'diag' in p:
                    print(f"  诊断模式: {'关闭' if not p.get('diag', True) else '开启'}")
                else:
                    print(f"  {'已启用' if p['enabled'] else '已停止'}")
            elif t == 'diag_read':
                line = f"[READ] {p['size']}B | {p.get('ascii','')[:200]}"
                diag_f.write(line + '\n')
                diag_f.flush()
            elif t == 'diag_read_xor':
                line = f"[READ^] {p['size']}B (XOR) | {p.get('ascii','')[:200]}"
                diag_f.write(line + '\n')
                diag_f.flush()
            else:
                print(f"  {p}")
        elif msg['type'] == 'error':
            desc = msg.get('description', '')
            stack = msg.get('stack', '')
            print(f"  [JS错误] {desc}")
            if stack:
                for line in stack.split('\n')[:5]:
                    print(f"    {line}")

    script.on('message', on_msg)
    script.load()

    diag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              f"bml_diag_{time.strftime('%H%M%S')}.txt")
    diag_f = open(diag_file, 'w', encoding='utf-8')

    print(f"\nBML hook 已激活: {source} -> {target}")
    print(f"诊断输出: {diag_file}")
    print("现在触发角色加载 (进房间 / 查看角色 / 商城试用)")
    print("命令: start | stop | stats | diag_off | quit\n")

    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd in ('start', 'stop', 'stats'):
                script.post({'type': 'cmd', 'cmd': cmd})
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    print("已断开。")

if __name__ == '__main__':
    main()

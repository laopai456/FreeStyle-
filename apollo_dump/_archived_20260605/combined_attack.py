"""
combined_attack.py — 组合攻击启动器
1. 部署 res767_combined.pak (含50125711 SMD文件) 到游戏目录
2. Frida附加 + 注入BML hook (同pak itemcode替换)
3. 等待用户触发物品加载

用法:
  1. 启动游戏，登录到大厅
  2. py combined_attack.py --deploy    # 首次需要部署pak
  3. py combined_attack.py             # 启动hook
  4. 在游戏中装备美丽梦想发型(50125461) → 应加载紫色超赛(50125711)的模型

命令: status | quit
"""
import sys, os, time, shutil, argparse

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
DESKTOP = r'C:\Users\w\Desktop'

JS_FILE = os.path.join(SCRIPT_DIR, 'combined_attack.js')
PAK_COMBINED = os.path.join(DESKTOP, 'res767_combined.pak')
PAK_GAME = os.path.join(GAME_DIR, 'res767.pak')
PAK_BACKUP = os.path.join(DESKTOP, 'res767_backup.pak')


def deploy_pak():
    if not os.path.exists(PAK_COMBINED):
        print(f'错误: {PAK_COMBINED} 不存在')
        print('先运行: py patch_res767_add.py')
        return False

    # 备份
    if not os.path.exists(PAK_BACKUP):
        print(f'备份原始pak → {PAK_BACKUP}')
        shutil.copy2(PAK_GAME, PAK_BACKUP)
    else:
        print(f'备份已存在: {PAK_BACKUP}')

    # 部署
    print(f'部署: {PAK_COMBINED} → {PAK_GAME}')
    shutil.copy2(PAK_COMBINED, PAK_GAME)
    sz = os.path.getsize(PAK_GAME)
    print(f'部署完成: {sz:,} bytes')
    print('重启游戏后运行: py combined_attack.py')
    return True


def restore_pak():
    if os.path.exists(PAK_BACKUP):
        print(f'恢复: {PAK_BACKUP} → {PAK_GAME}')
        shutil.copy2(PAK_BACKUP, PAK_GAME)
        print('已恢复原始pak')
    else:
        print('无备份文件')


def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None


def run_hook():
    import frida

    pid = find_pid()
    if not pid:
        print('错误: FreeStyle.exe 未运行')
        print('请先启动游戏并登录到大厅')
        return

    print(f'FreeStyle.exe PID: {pid}')

    # 验证pak是否已部署
    game_size = os.path.getsize(PAK_GAME)
    combined_size = os.path.getsize(PAK_COMBINED) if os.path.exists(PAK_COMBINED) else 0
    if combined_size and game_size != combined_size:
        print(f'警告: 游戏目录pak ({game_size:,}B) 与combined ({combined_size:,}B) 不匹配')
        print('可能未部署。运行: py combined_attack.py --deploy')
        ans = input('继续? (y/n) ').strip().lower()
        if ans != 'y':
            return

    with open(JS_FILE, encoding='utf-8') as f:
        js = f.read()

    session = frida.attach(pid)
    script = session.create_script(js)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'  [Apollo] {p["msg"]}')
            elif t == 'hook':
                print(f'  [Hook] {p["msg"]}')
            elif t == 'bml':
                meshes_str = ' | '.join(p.get('meshes', []))
                print(f'  [BML #{p["n"]}] ic={p["ic"]} meshes: {meshes_str}')
            elif t == 'patched':
                after_str = ' | '.join(p.get('after', []))
                print(f'  [PATCH] #{p["total"]} 处替换 (本次{p["patches"]}处)')
                print(f'    替换后: {after_str}')
            elif t == 'error':
                print(f'  [错误] {p["msg"]}')
            elif t == 'status':
                print(f'  状态: src={p["src"]} dst={p["dst"]} patches={p["patches"]} bmls={p["bmls"]}')
            else:
                print(f'  {p}')
        elif msg['type'] == 'error':
            print(f'  [JS错误] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    print()
    print('=== 组合攻击已激活 ===')
    print(f'  BML: {js[js.find("SRC_CODE")+11:js.find("SRC_CODE")+19]} → {js[js.find("DST_CODE")+11:js.find("DST_CODE")+19]}')
    print('  现在装备美丽梦想发型(50125461)查看效果')
    print('  命令: status | quit')
    print()

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                script.post({'type': 'cmd', 'cmd': 'status'})
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    print('已断开。')


def main():
    parser = argparse.ArgumentParser(description='组合攻击启动器')
    parser.add_argument('--deploy', action='store_true', help='部署patched pak到游戏目录')
    parser.add_argument('--restore', action='store_true', help='恢复原始pak')
    args = parser.parse_args()

    if args.deploy:
        deploy_pak()
    elif args.restore:
        restore_pak()
    else:
        run_hook()


if __name__ == '__main__':
    main()

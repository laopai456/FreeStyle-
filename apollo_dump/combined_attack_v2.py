"""
combined_attack_v2.py — 组合攻击v2 诊断版
日志同时输出到终端 + 写入 combined_attack_log.txt
用法:
  1. 启动游戏, 登录大厅
  2. py combined_attack_v2.py --deploy   # 首次部署pak
  3. 重启游戏
  4. py combined_attack_v2.py            # 启动hook
"""
import sys, os, time, json, shutil, argparse

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
DESKTOP = r'C:\Users\w\Desktop'

JS_FILE = os.path.join(SCRIPT_DIR, 'combined_attack_v2.js')
PAK_COMBINED = os.path.join(DESKTOP, 'res767_combined.pak')
PAK_GAME = os.path.join(GAME_DIR, 'res767.pak')
PAK_BACKUP = os.path.join(DESKTOP, 'res767_backup.pak')

# 日志文件
LOG_TS = time.strftime('%Y%m%d_%H%M%S')
LOG_FILE = os.path.join(SCRIPT_DIR, f'combined_attack_log_{LOG_TS}.txt')
LOG_F = None

def log_print(msg):
    """同时输出到终端和日志文件"""
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def log_json(obj):
    """JSON格式写入日志"""
    line = json.dumps(obj, ensure_ascii=False)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()


def deploy_pak():
    if not os.path.exists(PAK_COMBINED):
        print(f'错误: {PAK_COMBINED} 不存在, 先运行 py patch_res767_add.py')
        return False
    if not os.path.exists(PAK_BACKUP):
        print(f'备份 → {PAK_BACKUP}')
        shutil.copy2(PAK_GAME, PAK_BACKUP)
    print(f'部署: {PAK_COMBINED} → {PAK_GAME}')
    shutil.copy2(PAK_COMBINED, PAK_GAME)
    print(f'完成: {os.path.getsize(PAK_GAME):,} bytes. 重启游戏后运行本脚本.')
    return True

def restore_pak():
    if os.path.exists(PAK_BACKUP):
        shutil.copy2(PAK_BACKUP, PAK_GAME)
        print('已恢复原始pak')
    else:
        print('无备份')

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def run_hook():
    global LOG_F
    import frida

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行, 请先启动游戏')
        return

    # 检查pak
    game_sz = os.path.getsize(PAK_GAME)
    comb_sz = os.path.getsize(PAK_COMBINED) if os.path.exists(PAK_COMBINED) else 0
    pak_ok = comb_sz and game_sz == comb_sz

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log_print(f'=== 组合攻击 v2 诊断版 ===')
    log_print(f'PID: {pid}')
    log_print(f'res767.pak: {game_sz:,} bytes')
    log_print(f'res767_combined.pak: {comb_sz:,} bytes')
    log_print(f'PAK部署状态: {"OK" if pak_ok else "MISMATCH - 可能未部署!"}')
    log_print(f'日志文件: {LOG_FILE}')
    log_print('')

    if not pak_ok:
        log_print('警告: pak大小不匹配! 可能未部署combined pak.')
        log_print('运行: py combined_attack_v2.py --deploy')

    session = frida.attach(pid)
    with open(JS_FILE, encoding='utf-8') as f:
        js = f.read()

    script = session.create_script(js)

    stats = {'bml': 0, 'sskf': 0, 'patch': 0, 'error': 0, 'sskf_target': 0, 'sskf_source': 0}

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'log':
                line = p.get('line', '')
                # 解析event类型
                try:
                    obj = json.loads(line)
                    evt = obj.get('event', '')
                    if evt == 'bml':
                        stats['bml'] += 1
                        ic = obj.get('ic', '?')
                        meshes = obj.get('meshes', [])
                        log_print(f'[BML #{obj.get("n","")}] ic={ic}')
                        for m in meshes:
                            log_print(f'  mesh: {m}')
                        for tx in obj.get('textures', []):
                            log_print(f'  tex:  {tx}')
                    elif evt == 'sskf':
                        stats['sskf'] += 1
                        fname = obj.get('fname', '?')
                        sz = obj.get('size', 0)
                        flag = ''
                        if DST_CODE in fname:
                            stats['sskf_target'] += 1
                            flag = ' ★ TARGET SMD'
                        elif SRC_CODE in fname:
                            stats['sskf_source'] += 1
                            flag = ' ★ SOURCE SMD'
                        log_print(f'[SSKF #{obj.get("n","")}] {fname} ({sz:,}B){flag}')
                    elif evt == 'sskf_target':
                        log_print(f'★★★ 50125711 SMD加载: {obj.get("fname","")} ({obj.get("size",0):,}B)')
                    elif evt == 'sskf_source':
                        log_print(f'★★★ 50125461 SMD仍在被加载! {obj.get("fname","")}')
                    elif evt == 'patch':
                        stats['patch'] += 1
                        log_print(f'[PATCH] {obj.get("patches",0)}处 (总计{obj.get("total",0)})')
                        for m in obj.get('after_meshes', []):
                            log_print(f'  → mesh: {m}')
                        for tx in obj.get('after_textures', []):
                            log_print(f'  → tex:  {tx}')
                    elif evt == 'pak_open':
                        log_print(f'[PAK打开] {obj.get("file","")}')
                    elif evt == 'apollo_deception':
                        log_print(f'[Apollo] {obj.get("msg","")}')
                    elif evt == 'hook_ready':
                        log_print(f'[Hook] {obj.get("msg","")} | src={obj.get("src","")} dst={obj.get("dst","")}')
                    elif evt == 'module':
                        log_print(f'[Module] base={obj.get("base","")} text={obj.get("textStart","")} size={obj.get("textSize",0):,}')
                    elif evt == 'status':
                        log_print(f'[状态] BML={obj.get("bmls",0)} SSKF={obj.get("sskfs",0)} Patch={obj.get("patches",0)}')
                        log_print(f'  PAK打开: {obj.get("paks_opened",[])}')
                        log_print(f'  SSKF文件: {obj.get("sskf_files",[])}')
                    elif evt == 'error':
                        stats['error'] += 1
                        log_print(f'[错误] {obj.get("where","")}: {obj.get("msg","")}')
                    else:
                        log_print(f'[{evt}] {json.dumps(obj, ensure_ascii=False)[:200]}')
                except:
                    log_print(line[:200])
            else:
                log_print(f'[{t}] {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            desc = msg.get('description', '')
            log_print(f'[JS错误] {desc}')

    script.on('message', on_msg)
    script.load()

    log_print('')
    log_print('=== Hook已激活, 触发物品加载 ===')
    log_print(f'  50125461(美丽梦想) BML mesh路径会被替换为50125711(紫色超赛)')
    log_print(f'  日志: {LOG_FILE}')
    log_print('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                script.post({'type': 'cmd', 'cmd': 'status'})
            elif cmd == 'summary':
                log_print(f'--- 汇总 ---')
                log_print(f'BML: {stats["bml"]}')
                log_print(f'SSKF: {stats["sskf"]} (target={stats["sskf_target"]}, source={stats["sskf_source"]})')
                log_print(f'Patch: {stats["patch"]}')
                log_print(f'Error: {stats["error"]}')
    except (KeyboardInterrupt, EOFError):
        pass

    # 结束时写入汇总
    final = script.exports_sync.get_log() if hasattr(script, 'exports_sync') else ''
    log_print(f'\n=== 会话结束 ===')
    log_print(f'BML: {stats["bml"]} | SSKF: {stats["sskf"]} | Patch: {stats["patch"]} | Error: {stats["error"]}')
    log_print(f'完整日志已保存: {LOG_FILE}')

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if args.deploy:
        deploy_pak()
    elif args.restore:
        restore_pak()
    else:
        run_hook()

if __name__ == '__main__':
    main()

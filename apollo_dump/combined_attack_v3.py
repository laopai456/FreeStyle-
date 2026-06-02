"""
combined_attack_v3.py — v3 诊断版
BML替换 + Actor创建监控
重点: 确认游戏为50125461创建的是Static还是Dynamic actor
日志写入文件
"""
import sys, os, time, json, shutil, argparse

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
DESKTOP = r'C:\Users\w\Desktop'

JS_FILE = os.path.join(SCRIPT_DIR, 'combined_attack_v3.js')
PAK_COMBINED = os.path.join(DESKTOP, 'res767_combined.pak')
PAK_GAME = os.path.join(GAME_DIR, 'res767.pak')
PAK_BACKUP = os.path.join(DESKTOP, 'res767_backup.pak')

LOG_TS = time.strftime('%Y%m%d_%H%M%S')
LOG_FILE = os.path.join(SCRIPT_DIR, f'v3_log_{LOG_TS}.txt')
LOG_F = None

def log_print(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def deploy():
    if not os.path.exists(PAK_COMBINED):
        print(f'先运行: py patch_res767_add.py')
        return
    if not os.path.exists(PAK_BACKUP):
        shutil.copy2(PAK_GAME, PAK_BACKUP)
    shutil.copy2(PAK_COMBINED, PAK_GAME)
    print(f'部署完成: {os.path.getsize(PAK_GAME):,} bytes')

def restore():
    if os.path.exists(PAK_BACKUP):
        shutil.copy2(PAK_BACKUP, PAK_GAME)
        print('已恢复')

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def run():
    global LOG_F
    import frida

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log_print(f'=== v3 Actor诊断 === PID:{pid} ===')
    log_print(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    with open(JS_FILE, encoding='utf-8') as f:
        js = f.read()

    script = session.create_script(js)
    stats = {'bml':0, 'sskf':0, 'patch':0, 'actor':0, 'actor_ret':0, 'error':0}
    actor_events = []

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t','')
            if t == 'log':
                try:
                    raw = p.get('line','{}')
                    # strip timestamp prefix (format: HH:MM:SS.mmm {...})
                    brace_idx = raw.find('{')
                    if brace_idx > 0:
                        raw = raw[brace_idx:]
                    obj = json.loads(raw)
                    evt = obj.get('event','')
                    if evt == 'actor_call':
                        stats['actor'] += 1
                        actor_events.append(obj)
                        log_print(f'[ACTOR #{stats["actor"]}] {obj["type"]} @ {obj["addr"]}')
                        log_print(f'  ret={obj.get("retAddrRVA","")} eax={obj.get("eax","")} stack={obj.get("stackTop8",[])}')
                    elif evt == 'actor_ret':
                        stats['actor_ret'] += 1
                        log_print(f'[ACTOR RET] {obj.get("type","")} → {obj.get("retval","")}')
                    elif evt == 'bml':
                        stats['bml'] += 1
                        ic = obj.get('ic','?')
                        log_print(f'[BML #{obj.get("n","")}] ic={ic} meshes={len(obj.get("meshes",[]))}')
                    elif evt == 'sskf':
                        stats['sskf'] += 1
                        fn = obj.get('fname','?')
                        fl = obj.get('flag','')
                        log_print(f'[SSKF #{obj.get("n","")}] {fn} ({obj.get("size",0):,}B){fl}')
                    elif evt == 'patch':
                        stats['patch'] += 1
                        log_print(f'[PATCH] {obj.get("patches",0)}处 总{obj.get("total",0)}')
                        for m in obj.get('after',[]):
                            log_print(f'  → {m}')
                    elif evt == 'hook_ok':
                        log_print(f'[HOOK OK] {obj.get("name","")} @ {obj.get("addr","")}')
                    elif evt == 'hook_fail':
                        log_print(f'[HOOK FAIL] {obj.get("name","")} {obj.get("err","")}')
                    elif evt == 'ready':
                        log_print(f'[READY] {obj.get("msg","")}')
                    elif evt == 'status':
                        log_print(f'[STATUS] BML={obj.get("bmls",0)} SSKF={obj.get("sskfs",0)} Actors={obj.get("actors",0)} types={obj.get("actorTypes",[])}')
                    elif evt == 'error':
                        stats['error'] += 1
                        log_print(f'[ERROR] {obj.get("where","")}: {obj.get("msg","")}')
                    elif evt in ('module', 'apollo'):
                        log_print(f'[{evt}] {json.dumps(obj, ensure_ascii=False)[:150]}')
                    else:
                        log_print(f'[{evt}] {json.dumps(obj, ensure_ascii=False)[:150]}')
                except Exception as e:
                    log_print(f'[parse_err] {e}')
        elif msg['type'] == 'error':
            log_print(f'[JS_ERR] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log_print('')
    log_print('Hook已激活。装备美丽梦想发型(50125461)查看效果。')
    log_print('命令: status | actors | quit')
    log_print('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                script.post({'type':'cmd','cmd':'status'})
            elif cmd == 'actors':
                # 写actor详情到文件
                actors_json = script.exports_sync.get_log()
                log_print(f'Actor调用详情:')
                log_print(actors_json)
    except (KeyboardInterrupt, EOFError):
        pass

    log_print(f'\n=== 汇总 ===')
    log_print(f'BML={stats["bml"]} SSKF={stats["sskf"]} Patch={stats["patch"]} ActorCalls={stats["actor"]} ActorRets={stats["actor_ret"]} Errors={stats["error"]}')
    log_print(f'日志: {LOG_FILE}')

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if args.deploy:
        deploy()
    elif args.restore:
        restore()
    else:
        run()

"""
hook_quick_detach.py — sprintf + LoadItemFile替换, 自动脱离
策略: 替换完成后自动detach, 避免Apollo反作弊检测
进练习场前输入 attach 重新挂钩

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida, threading
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'quick_detach_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767, 静态)
DST_IC = 50125711  # 紫色超赛发型 (pak768, 动态)

AUTO_DETACH_SEC = 90  # 总挂钩时间上限，Apollo约120秒检测

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
'use strict';

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;
var hooked = false;
var patchCount = 0;
var hookStartTime = 0;
var listeners = [];

// 异常处理器 — 只记录真崩溃(access-violation/illegal)，过滤Apollo断点噪声
Process.setExceptionHandler(function(details) {
    if (details.type !== 'breakpoint') {
        send({t: 'CRASH',
              type: details.type,
              addr: '0x' + details.address.toString(16),
              eip: '0x' + details.context.pc.toString(16),
              eax: '0x' + details.context.eax.toString(16),
              esp: '0x' + details.context.esp.toString(16),
              ebp: '0x' + details.context.ebp.toString(16),
              patches: patchCount,
              mem: details.memory || {}
        });
    }
    return false;
});

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function hookAll() {
    if (hooked) return false;
    var base = ptr('0x400000');

    // 1. sprintf hook
    var msvcr100 = Process.getModuleByName('MSVCR100.dll');
    var sprintfAddr = msvcr100.getExportByName('sprintf');
    var l1 = Interceptor.attach(sprintfAddr, {
        onEnter: function(args) {
            try {
                var fmt = readAscii(args[1], 50);
                if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;
                var itemCode = args[2].toInt32();
                if (itemCode === SRC_IC) {
                    args[2] = ptr(DST_IC);
                    var callerEbp = this.context.ebp;
                    callerEbp.sub(0xD8).writeU32(DST_IC);
                    patchCount++;
                    send({t: 'sprintf_patched', n: patchCount});
                }
            } catch(e) {}
        }
    });
    listeners.push(l1);

    // 2. LoadItemFile hook
    var lifAddr = base.add(0x1ACE1C0);
    var l2 = Interceptor.attach(lifAddr, {
        onEnter: function(args) {
            var ic = args[0].toInt32();
            if (ic === SRC_IC) {
                args[0] = ptr(DST_IC);
                var dstStr = DST_IC.toString();
                for (var j = 0; j < dstStr.length; j++) {
                    args[1].add(16 + j).writeU8(dstStr.charCodeAt(j));
                }
                patchCount++;
                send({t: 'lif_patched', n: patchCount});
            }
        }
    });
    listeners.push(l2);

    hooked = true;
    hookStartTime = Date.now();
    send({t: 'hooked', msg: 'sprintf + LoadItemFile hook已设置'});
    return true;
}

function unhookAll() {
    if (!hooked) return false;
    for (var i = 0; i < listeners.length; i++) {
        try { listeners[i].detach(); } catch(e) {}
    }
    listeners = [];
    hooked = false;
    send({t: 'unhooked', msg: '所有hook已脱离'});
    return true;
}

hookAll();

rpc.exports = {
    status: function() {
        var elapsed = hooked ? Math.floor((Date.now() - hookStartTime) / 1000) : -1;
        return JSON.stringify({
            hooked: hooked,
            patches: patchCount,
            elapsed: elapsed
        });
    },
    attach: function() {
        return hookAll();
    },
    detach: function() {
        return unhookAll();
    }
};
"""


def main():
    global LOG_F
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 快速脱离替换 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')
    log(f'自动脱离: {AUTO_DETACH_SEC}秒无活动后')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'hooked':
                log(f'  [挂钩] {p["msg"]}')
            elif t == 'unhooked':
                log(f'  [脱离] {p["msg"]}')
            elif t == 'sprintf_patched':
                log(f'  [sprintf替换] #{p["n"]}')
            elif t == 'lif_patched':
                log(f'  [LoadItemFile替换] #{p["n"]}')
            elif t == 'CRASH':
                log(f'  ★ 崩溃! type={p["type"]} addr={p["addr"]}')
                log(f'    EIP={p["eip"]} EAX={p["eax"]}')
                log(f'    ESP={p["esp"]} EBP={p["ebp"]}')
                log(f'    patches={p["patches"]}')
                if p.get('mem') and p['mem'].get('address'):
                    log(f'    mem: addr={p["mem"]["address"]} op={p["mem"].get("operation","?")}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    # 自动脱离线程 — 按总挂钩时间
    detached_by_auto = [False]

    def auto_detach_watcher():
        while True:
            time.sleep(1)
            try:
                st = json.loads(script.exports_sync.status())
                if st['hooked'] and st['elapsed'] >= AUTO_DETACH_SEC:
                    script.exports_sync.detach()
                    detached_by_auto[0] = True
                    log(f'  [自动脱离] 挂钩{st["elapsed"]}秒，已达上限{AUTO_DETACH_SEC}秒')
                elif st['hooked'] and st['elapsed'] >= AUTO_DETACH_SEC - 15:
                    log(f'  [警告] 挂钩{st["elapsed"]}秒，即将自动脱离({AUTO_DETACH_SEC}秒)')
            except:
                break

    watcher = threading.Thread(target=auto_detach_watcher, daemon=True)
    watcher.start()

    log('')
    log('流程:')
    log('  1. 进房间 → 头发渲染 → 自动脱离')
    log('  2. 输入 attach → 重新挂钩')
    log('  3. 进练习场 → 头发渲染 → 自动脱离')
    log('命令: attach | detach | status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                st = json.loads(script.exports_sync.status())
                state = '已挂钩' if st['hooked'] else '已脱离'
                elapsed = f'{st["elapsed"]}秒' if st['hooked'] else '-'
                log(f'  {state} | 替换{st["patches"]}次 | 挂钩{elapsed}/{AUTO_DETACH_SEC}秒')
            elif cmd == 'attach':
                detached_by_auto[0] = False
                result = script.exports_sync.attach()
                log(f'  重新挂钩: {"成功" if result else "失败/已挂钩"}')
            elif cmd == 'detach':
                result = script.exports_sync.detach()
                log(f'  脱离: {"成功" if result else "已脱离"}')
    except (KeyboardInterrupt, EOFError):
        pass

    try:
        script.exports_sync.detach()
    except:
        pass
    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

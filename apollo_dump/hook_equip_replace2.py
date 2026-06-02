"""
hook_equip_replace2.py — Phase 5v2: 安全栈扫描 + 替换
不做EBP链遍历(导致崩溃), 改为线性扫描栈空间找ItemCode。
扫描范围: esp到esp+0x2000, 涵盖所有调用者的栈帧。

发现ItemCode后, 直接替换, 并验证。
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_replace2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

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

SRC_INT = 50125461  # 美丽梦想发型 (pak767)
DST_INT = 50125711  # 紫色超赛发型 (pak768)

JS_CODE = r"""
'use strict';

var base = Process.getModuleByName('FreeStyle.exe').base;
var SRC_INT = 50125461;
var DST_INT = 50125711;
var SRC_STR = '50125461';
var DST_STR = '50125711';
var dstBytes = [];
for (var i = 0; i < DST_STR.length; i++) dstBytes.push(DST_STR.charCodeAt(i));

var callIndex = 0;
var patchCount = 0;

var dc1Addr = base.add(0x01E99730);

Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callIndex++;
        var idx = callIndex;
        var esp = this.context.esp;

        // 安全线性扫描栈: esp到esp+0x2000
        // 只读, 不做任何指针跟踪, 避免崩溃
        var intHits = [];
        var strHits = [];

        try {
            for (var off = 0; off < 0x2000; off += 4) {
                var val = esp.add(off).readU32();
                if (val === SRC_INT) {
                    intHits.push({off: off, addr: esp.add(off).toString()});
                }
            }
        } catch(e) {}  // 到达栈末尾会异常, 正常

        // 搜ASCII字符串 (字节级)
        try {
            for (var off = 0; off < 0x2000; off++) {
                var match = true;
                for (var b = 0; b < 8; b++) {
                    if (esp.add(off + b).readU8() !== SRC_STR.charCodeAt(b)) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    strHits.push({off: off, addr: esp.add(off).toString()});
                }
            }
        } catch(e) {}

        if (intHits.length === 0 && strHits.length === 0) return;

        send({t: 'found', idx: idx, intHits: intHits.length, strHits: strHits.length});

        // === 替换所有INT ===
        for (var i = 0; i < intHits.length; i++) {
            var addr = esp.add(intHits[i].off);
            addr.writeU32(DST_INT);
            patchCount++;
            send({t: 'int_patch', off: '0x' + intHits[i].off.toString(16), addr: intHits[i].addr});
        }

        // === 替换所有ASCII字符串 ===
        for (var i = 0; i < strHits.length; i++) {
            var addr = esp.add(strHits[i].off);
            for (var b = 0; b < dstBytes.length; b++) {
                addr.add(b).writeU8(dstBytes[b]);
            }
            patchCount++;
            send({t: 'str_patch', off: '0x' + strHits[i].off.toString(16), addr: strHits[i].addr});
        }
    }
});

send({t: 'ready', msg: '安全栈扫描hook ready.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, calls: callIndex});
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
    log(f'=== Phase 5v2: 安全栈扫描替换 === PID:{pid} ===')
    log(f'{SRC_INT}(美丽梦想 pak767) → {DST_INT}(紫色超赛 pak768)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'found':
                log(f'  [#{p["idx"]}] 栈上找到 INT:{p["intHits"]}处 STRING:{p["strHits"]}处')
            elif t == 'int_patch':
                log(f'    INT替换 esp+{p["off"]} @ {p["addr"]}')
            elif t == 'str_patch':
                log(f'    STR替换 esp+{p["off"]} @ {p["addr"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                status = script.exports_sync.status()
                log(f'  {status}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

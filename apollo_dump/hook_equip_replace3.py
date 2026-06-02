"""
hook_equip_replace3.py — Phase 5v3: 精确6次读取替换
已知: depth=4的EBP帧, [ebp-0xB8]指向数据, [ptr+0x50]是ItemCode INT

策略: 在onEnter中只做6次精确读取, 不扫描:
  1-4. walk EBP链4次 (readPointer)
  5.   read [ebp-0xB8] (readPointer)
  6.   read [ptr+0x50] (readU32)
  如果==50125461则替换为50125711
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_replace3_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var DST_STR = '50125711';
var dstBytes = [];
for (var i = 0; i < DST_STR.length; i++) dstBytes.push(DST_STR.charCodeAt(i));

var callIndex = 0;
var patchCount = 0;

function isValidPtr(p) {
    return p.compare(ptr(0x10000)) > 0 && p.compare(ptr(0x80000000)) < 0;
}

var dc1Addr = base.add(0x01E99730);

Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callIndex++;
        var idx = callIndex;
        var ebp0 = this.context.ebp;

        // 精确walk: 只走4步, 每步验证
        var fp = ebp0;
        var ok = true;
        for (var d = 0; d < 4; d++) {
            try {
                var next = fp.readPointer();
                if (!isValidPtr(next)) { ok = false; break; }
                fp = next;
            } catch(e) { ok = false; break; }
        }
        if (!ok) return;

        // fp现在是depth=4的ebp, 读[fp-0xB8]
        var dataPtr;
        try {
            dataPtr = fp.sub(0xB8).readPointer();
        } catch(e) { return; }
        if (!isValidPtr(dataPtr)) return;

        // 读[dataPtr+0x50]
        var itemCode;
        try {
            itemCode = dataPtr.add(0x50).readU32();
        } catch(e) { return; }

        // 只在首次调用时汇报结构信息(帮助调试)
        if (callIndex <= 8) {
            send({t: 'probe', idx: idx, code: itemCode, dataPtr: dataPtr.toString()});
        }

        if (itemCode !== SRC_INT) return;

        // === 命中! 替换 ===
        patchCount++;
        send({t: 'hit', idx: idx, dataPtr: dataPtr.toString(), old: itemCode});

        // 替换 INT
        dataPtr.add(0x50).writeU32(DST_INT);

        // 搜索附近ASCII字符串 (只在ptr+0x30到0x90范围, 按字节)
        for (var off = 0x30; off < 0x90; off++) {
            try {
                var match = true;
                for (var b = 0; b < 8; b++) {
                    if (dataPtr.add(off + b).readU8() !== 0x35 + b) {
                        // 50125461 = 0x35,0x30,0x31,0x32,0x35,0x34,0x36,0x31
                        match = false;
                        break;
                    }
                }
                if (match) {
                    for (var b = 0; b < dstBytes.length; b++) {
                        dataPtr.add(off + b).writeU8(dstBytes[b]);
                    }
                    send({t: 'str_patch', off: '0x' + off.toString(16)});
                }
            } catch(e) {}
        }

        // 验证
        try {
            var verify = dataPtr.add(0x50).readU32();
            send({t: 'verify', val: verify, ok: verify === DST_INT});
        } catch(e) {}
    }
});

send({t: 'ready', msg: '精确替换v3 ready (6次读取). 进房间.'});

rpc.exports = {
    status: function() { return JSON.stringify({patches: patchCount, calls: callIndex}); }
};
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Phase 5v3: 精确替换 === PID:{pid} ===')
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
            elif t == 'probe':
                log(f'  [#{p["idx"]}] dataPtr={p["dataPtr"]} code={p["code"]}')
            elif t == 'hit':
                log(f'  [命中!] #{p["idx"]} dataPtr={p["dataPtr"]} old={p["old"]}')
            elif t == 'str_patch':
                log(f'    字符串替换 @+{p["off"]}')
            elif t == 'verify':
                log(f'    验证: {p["val"]} {"OK" if p["ok"] else "FAIL"}')
            else:
                log(f'  {json.dumps(p)[:200]}')
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
                log(f'  {script.exports_sync.status()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

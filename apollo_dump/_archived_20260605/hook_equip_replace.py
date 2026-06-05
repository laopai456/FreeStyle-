"""
hook_equip_replace.py — Phase 5: 精确替换ItemCode
发现: DynamicCreate1被调用时, depth=4的栈帧(retAddr RVA 0x1723E84)中
      [ebp-0xB8] 是一个指针, [ptr+0x50] = INT ItemCode

策略:
  Hook DynamicCreate1, 只在第4次调用(发型)时:
  1. 沿EBP链走到depth=4
  2. 读 [ebp-0xB8]->ptr+0x50 确认是 50125461
  3. 替换为 50125711
  4. 同时搜索同结构中是否有字符串形式也要替换
  5. 让游戏继续, 后续代码读到新ItemCode走完整管线

注意: 不做大范围扫描, 只碰已知的几个地址, 避免崩溃
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_replace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

# 50125461(美丽梦想发型 pak767) → 50125711(紫色超赛发型 pak768)
SRC_INT = 50125461
DST_INT = 50125711

JS_CODE = r"""
'use strict';

var base = Process.getModuleByName('FreeStyle.exe').base;
var SRC_INT = 50125461;   // 美丽梦想发型 (pak767)
var DST_INT = 50125711;   // 紫色超赛发型 (pak768)
var SRC_STR = '50125461';
var DST_STR = '50125711';

var callIndex = 0;
var patchCount = 0;

var dc1Addr = base.add(0x01E99730);

Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callIndex++;
        var idx = callIndex;

        // 只在第4次调用处理 (发型actor)
        // 前3次是身体/衣服, 第4次是发型 (延迟约2秒)
        // 实际上: 每次都检查, 看depth=4是否有ItemCode
        var ebp = this.context.ebp;

        // 走到depth=4
        var framePtr = ebp;
        for (var d = 0; d < 4; d++) {
            try {
                framePtr = framePtr.readPointer();
            } catch(e) {
                return; // EBP链断了, 跳过
            }
            if (framePtr.compare(ptr(0x10000)) < 0) return;
        }

        // depth=4的帧: [ebp-0xB8] 是指针
        var dataPtr;
        try {
            dataPtr = framePtr.sub(0xB8).readPointer();
        } catch(e) { return; }

        if (dataPtr.compare(ptr(0x10000)) < 0 || dataPtr.compare(ptr(0x80000000)) >= 0) return;

        // 检查 [ptr+0x50] 是否是目标ItemCode
        var itemCode;
        try {
            itemCode = dataPtr.add(0x50).readU32();
        } catch(e) { return; }

        if (itemCode !== SRC_INT) return; // 不是美丽梦想, 跳过

        // === 命中! 替换 ===
        patchCount++;
        send({
            t: 'hit',
            idx: idx,
            dataPtr: dataPtr.toString(),
            oldCode: itemCode,
            frameEbp: framePtr.toString()
        });

        // 替换 INT at ptr+0x50
        dataPtr.add(0x50).writeU32(DST_INT);

        // 搜索附近是否有ASCII字符串也要替换
        // 扫描 ptr+0x30到ptr+0x80 看有没有"50125461"
        var dstBytes = [];
        for (var i = 0; i < DST_STR.length; i++) dstBytes.push(DST_STR.charCodeAt(i));

        for (var off = 0x30; off < 0x90; off++) {
            try {
                var match = true;
                for (var b = 0; b < 8; b++) {
                    if (dataPtr.add(off + b).readU8() !== SRC_STR.charCodeAt(b)) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    for (var b = 0; b < dstBytes.length; b++) {
                        dataPtr.add(off + b).writeU8(dstBytes[b]);
                    }
                    send({t: 'str_patch', off: '0x' + off.toString(16), old: SRC_STR, new: DST_STR});
                }
            } catch(e) {}
        }

        // 检查ptr附近的其他指针, 跟踪并替换
        for (var off = 0x40; off < 0x80; off += 4) {
            try {
                var subPtr = dataPtr.add(off).readPointer();
                if (subPtr.compare(ptr(0x10000)) > 0 && subPtr.compare(ptr(0x80000000)) < 0) {
                    // 在子对象中搜ItemCode字符串
                    for (var off2 = 0; off2 < 0x40; off2++) {
                        var match = true;
                        for (var b = 0; b < 8; b++) {
                            if (subPtr.add(off2 + b).readU8() !== SRC_STR.charCodeAt(b)) {
                                match = false;
                                break;
                            }
                        }
                        if (match) {
                            for (var b = 0; b < dstBytes.length; b++) {
                                subPtr.add(off2 + b).writeU8(dstBytes[b]);
                            }
                            send({t: 'substr_patch', ptrOff: '0x' + off.toString(16), subOff: '0x' + off2.toString(16)});
                        }
                    }
                }
            } catch(e) {}
        }

        // 验证替换
        var newVal;
        try { newVal = dataPtr.add(0x50).readU32(); } catch(e) {}
        send({t: 'verified', newVal: newVal, expected: DST_INT, ok: newVal === DST_INT});
    }
});

send({t: 'ready', msg: '精确替换hook ready. 进房间触发角色加载.'});

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
    log(f'=== Phase 5: 精确替换ItemCode === PID:{pid} ===')
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
            elif t == 'hit':
                log(f'  [命中!] 调用#{p["idx"]} dataPtr={p["dataPtr"]}')
                log(f'    ItemCode: {p["oldCode"]} → {DST_INT}')
            elif t == 'str_patch':
                log(f'    字符串替换 @+{p["off"]}: {p["old"]} → {p["new"]}')
            elif t == 'substr_patch':
                log(f'    子对象字符串替换 ptr+{p["ptrOff"]} sub+{p["subOff"]}')
            elif t == 'verified':
                ok = '成功' if p['ok'] else '失败!'
                log(f'    验证: {p["newVal"]} (期望{p["expected"]}) → {ok}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Hook已激活。进房间触发角色加载。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                status = script.exports_sync.status()
                log(f'  状态: {status}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

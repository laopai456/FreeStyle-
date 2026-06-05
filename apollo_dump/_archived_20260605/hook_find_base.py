"""
hook_find_base.py — 从 sprintf 调用点反推 ItemCode 内存基地址
当 sprintf 命中 SRC_IC 时:
1. dump 调用者栈帧 (扫描 [ebp-0x200] ~ [ebp+0x10] 找所有含 SRC_IC 的位置)
2. dump 调用者上一层 (caller's caller) 的栈帧
3. 扫描堆上的对象, 找 SRC_IC 出现在哪些结构体里
4. 输出每个命中地址的上下文 (前后各 4 个 DWORD)

目标: 找到 SRC_IC 在堆对象中的稳定偏移 → 直接改堆对象, 不依赖 ebp
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'find_base_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

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

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});

var scanCount = 0;

// Hook sprintf
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = args[1];
            var c0 = fmt.readU8();
            if (c0 !== 0x63) return;  // 'c'
            var fmtStr = readAscii(fmt, 50);
            if (fmtStr.indexOf('customize') < 0) return;
            if (fmtStr.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            if (itemCode !== SRC_IC) return;

            scanCount++;
            // 抓前 20 次, 验证偏移稳定性
            if (scanCount > 20) return;

            var ebp = this.context.ebp;
            var esp = this.context.esp;
            var retAddr = this.returnAddress;

            send({t: 'hit', n: scanCount, retAddr: retAddr.toString(), ebp: ebp.toString(), esp: esp.toString()});

            // 1. 扫描当前栈帧: [ebp-0x200] ~ [ebp+0x20]
            //    找所有值等于 SRC_IC 的位置
            var stackHits = [];
            for (var offset = -0x200; offset <= 0x20; offset += 4) {
                try {
                    var val = ebp.add(offset).readU32();
                    if (val === SRC_IC) {
                        // 读前后各 4 个 DWORD 作为上下文
                        var ctx = [];
                        for (var j = -16; j <= 16; j += 4) {
                            ctx.push(ebp.add(offset + j).readU32().toString(16));
                        }
                        stackHits.push({
                            offset: offset,
                            offsetHex: '0x' + (offset >>> 0).toString(16),
                            addr: ebp.add(offset).toString(),
                            context: ctx
                        });
                    }
                } catch(e) {}
            }
            send({t: 'stack', n: scanCount, hits: stackHits});

            // 2. 检查 caller's caller (上一层)
            //    [ebp+4] = return address = caller's EIP after call
            //    [ebp+0] = caller's EBP (previous frame)
            try {
                var callerEbp = ebp.readPointer();  // saved ebp = caller's frame
                var callerRetAddr = ebp.add(4).readPointer();  // caller's return address

                send({t: 'caller', n: scanCount,
                      callerEbp: callerEbp.toString(),
                      callerRetAddr: callerRetAddr.toString()});

                // 扫描 caller's frame
                var callerHits = [];
                for (var offset = -0x200; offset <= 0x20; offset += 4) {
                    try {
                        var val = callerEbp.add(offset).readU32();
                        if (val === SRC_IC) {
                            var ctx = [];
                            for (var j = -16; j <= 16; j += 4) {
                                ctx.push(callerEbp.add(offset + j).readU32().toString(16));
                            }
                            callerHits.push({
                                offset: offset,
                                offsetHex: '0x' + (offset >>> 0).toString(16),
                                addr: callerEbp.add(offset).toString(),
                                context: ctx
                            });
                        }
                    } catch(e) {}
                }
                send({t: 'caller_stack', n: scanCount, hits: callerHits});

                // 3. 从 caller's frame 中的指针, 追踪堆对象
                //    检查每个栈上的值, 看它是否是堆指针, 且指向的结构体包含 SRC_IC
                var heapHits = [];
                for (var offset = -0x100; offset <= 0x10; offset += 4) {
                    try {
                        var ptrVal = callerEbp.add(offset).readPointer();
                        // 尝试把栈上的值当作指针, 读取它指向的内存
                        // 在 [ptr+0] ~ [ptr+0x200] 范围搜索 SRC_IC
                        for (var objOff = 0; objOff < 0x200; objOff += 4) {
                            try {
                                var memVal = ptrVal.add(objOff).readU32();
                                if (memVal === SRC_IC) {
                                    // 读这个对象前后各 8 个 DWORD
                                    var objCtx = [];
                                    var readStart = Math.max(0, objOff - 32);
                                    var readEnd = objOff + 48;
                                    for (var k = readStart; k < readEnd; k += 4) {
                                        try {
                                            objCtx.push(ptrVal.add(k).readU32().toString(16));
                                        } catch(e2) { objCtx.push('????????'); }
                                    }
                                    heapHits.push({
                                        stackOffset: offset,
                                        stackOffsetHex: '0x' + (offset >>> 0).toString(16),
                                        objectBase: ptrVal.toString(),
                                        fieldOffset: objOff,
                                        fieldOffsetHex: '0x' + objOff.toString(16),
                                        context: objCtx
                                    });
                                }
                            } catch(e) {}
                        }
                    } catch(e) {}
                }
                send({t: 'heap', n: scanCount, hits: heapHits});

            } catch(e) {
                send({t: 'error', msg: 'caller trace: ' + e});
            }

        } catch(e) {
            send({t: 'error', msg: 'sprintf: ' + e});
        }
    }
});

send({t: 'ready', msg: '基地址扫描就绪: 等 sprintf 命中 ' + SRC_IC});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 基地址扫描 === PID:{pid} ===')
    log(f'目标: 找 {SRC_IC} 在堆对象中的稳定位置')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'ready':
                log(f'  ★ {p["msg"]}')
            elif t == 'hit':
                log(f'  [命中] #{p["n"]} retAddr={p["retAddr"]} ebp={p["ebp"]}')
            elif t == 'stack':
                log(f'  [栈扫描] #{p["n"]} 命中 {len(p["hits"])} 处:')
                for h in p['hits']:
                    log(f'    [ebp{h["offsetHex"]}] addr={h["addr"]} ctx={h["context"]}')
            elif t == 'caller':
                log(f'  [上层] #{p["n"]} callerEbp={p["callerEbp"]} callerRet={p["callerRetAddr"]}')
            elif t == 'caller_stack':
                log(f'  [上层栈] #{p["n"]} 命中 {len(p["hits"])} 处:')
                for h in p['hits']:
                    log(f'    [ebp{h["offsetHex"]}] addr={h["addr"]} ctx={h["context"]}')
            elif t == 'heap':
                log(f'  [堆追踪] #{p["n"]} 命中 {len(p["hits"])} 处:')
                for h in p['hits']:
                    log(f'    栈[ebp{h["stackOffsetHex"]}] → 对象基址={h["objectBase"]} + 字段偏移={h["fieldOffsetHex"]}')
                    log(f'    对象上下文: {h["context"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:300]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('进房间触发 sprintf, 会自动扫描前5次命中。')
    log('')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

"""
hook_itemcode_hunt2.py — Phase 4v2: 沿EBP链向上搜索ItemCode
DynamicCreate1的直接参数中没有ItemCode, 说明它在上层函数的栈帧中。
通过EBP链逐帧搜索, 找到ItemCode在哪个调用层、哪个偏移。
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'itemcode_hunt2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

JS_CODE = r"""
'use strict';

var base = Process.getModuleByName('FreeStyle.exe').base;
var TARGET_INT = 50125461;  // 0x02FCDA95
var TARGET_STR_BYTES = [0x35, 0x30, 0x31, 0x32, 0x35, 0x34, 0x36, 0x31]; // "50125461"

var callIndex = 0;

var dc1Addr = base.add(0x01E99730);
Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callIndex++;
        var idx = callIndex;
        var ecx = this.context.ecx;
        var esp = this.context.esp;
        var ebp = this.context.ebp;

        var findings = [];

        // === 搜索1: 沿EBP链逐帧搜索 ===
        var framePtr = ebp;
        for (var depth = 0; depth < 20 && framePtr.compare(ptr(0x10000)) > 0; depth++) {
            var retAddr = 0;
            try { retAddr = framePtr.add(4).readU32(); } catch(e) { break; }
            var retRva = retAddr - base;

            // 搜索当前栈帧: 从framePtr-0x300到framePtr+8
            for (var off = -0x300; off <= 0x8; off += 4) {
                try {
                    var val = framePtr.add(off).readU32();
                    if (val === TARGET_INT) {
                        findings.push({
                            depth: depth,
                            ebp: framePtr.toString(),
                            offset: off,
                            addr: framePtr.add(off).toString(),
                            retAddr: '0x' + retRva.toString(16),
                            type: 'INT',
                            desc: 'frame[ebp+' + (off >= 0 ? '+' : '') + off.toString(16) + '] ret=RVA:0x' + retRva.toString(16)
                        });
                    }
                } catch(e) {}
            }

            // 也搜ASCII字符串 (按字节搜索)
            for (var off = -0x300; off <= 0x8; off += 1) {
                try {
                    var match = true;
                    for (var b = 0; b < TARGET_STR_BYTES.length; b++) {
                        if (framePtr.add(off + b).readU8() !== TARGET_STR_BYTES[b]) {
                            match = false;
                            break;
                        }
                    }
                    if (match) {
                        findings.push({
                            depth: depth,
                            ebp: framePtr.toString(),
                            offset: off,
                            addr: framePtr.add(off).toString(),
                            retAddr: '0x' + retRva.toString(16),
                            type: 'ASCII_STRING',
                            desc: 'frame[ebp+' + (off >= 0 ? '+' : '') + off.toString(16) + '] ret=RVA:0x' + retRva.toString(16)
                        });
                    }
                } catch(e) {}
            }

            // 搜索栈帧中的指针 -> 检查指针目标的前0x80字节
            for (var off = -0x100; off <= 0x8; off += 4) {
                try {
                    var ptrVal = framePtr.add(off).readPointer();
                    if (ptrVal.compare(ptr(0x10000)) > 0 && ptrVal.compare(ptr(0x80000000)) < 0) {
                        for (var off2 = 0; off2 < 0x80; off2 += 4) {
                            try {
                                var val2 = ptrVal.add(off2).readU32();
                                if (val2 === TARGET_INT) {
                                    findings.push({
                                        depth: depth,
                                        ebp: framePtr.toString(),
                                        offset: off,
                                        addr: ptrVal.add(off2).toString(),
                                        retAddr: '0x' + retRva.toString(16),
                                        type: 'INT_VIA_PTR',
                                        desc: 'frame[ebp+' + (off >= 0 ? '+' : '') + off.toString(16) + ']->ptr+' + off2.toString(16) + ' ret=RVA:0x' + retRva.toString(16)
                                    });
                                }
                            } catch(e) {}
                        }
                    }
                } catch(e) {}
            }

            // 跟到上一个ebp
            try {
                framePtr = framePtr.readPointer();
            } catch(e) { break; }
        }

        send({t: 'hunt', idx: idx, ecx: ecx.toString(), findings: findings});
    }
});

send({t: 'ready', msg: 'EBP链搜索器ready. 进房间触发角色加载.'});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Phase 4v2: EBP链搜索ItemCode === PID:{pid} ===')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'hunt':
                idx = p['idx']
                findings = p['findings']
                log(f'  [#{idx}] ecx={p["ecx"]}')
                if findings:
                    log(f'  !!! 找到 {len(findings)} 处:')
                    for f in findings:
                        log(f'    depth={f["depth"]} {f["type"]}: {f["desc"]}')
                        log(f'      addr={f["addr"]}')
                else:
                    log(f'  未找到ItemCode')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Hook已激活。进房间触发角色加载。')
    log('命令: quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

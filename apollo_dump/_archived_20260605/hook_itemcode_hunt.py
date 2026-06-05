"""
hook_itemcode_hunt.py — Phase 4: 定位ItemCode在DynamicCreate参数中的位置
在DynamicCreate1被调用时, 扫描this对象和栈帧找INT 50125461(0x02FCDA95)

找到后我们就知道在哪层函数、哪个偏移替换ItemCode
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'itemcode_hunt_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var TARGET_BYTES = [0x95, 0xDA, 0xFC, 0x02];

var callIndex = 0;

// Hook DynamicCreate1 at RVA 0x01E99730
var dc1Addr = base.add(0x01E99730);
Interceptor.attach(dc1Addr, {
    onEnter: function(args) {
        callIndex++;
        var idx = callIndex;
        var ecx = this.context.ecx;
        var eax = this.context.eax;
        var esp = this.context.esp;
        var ebp = this.context.ebp;

        var report = {
            callIdx: idx,
            ecx: ecx.toString(),
            eax: eax.toString(),
            findings: []
        };

        // 1. 扫描this对象(ecx)前256字节找ItemCode
        for (var off = 0; off < 0x100; off += 4) {
            try {
                var val = ecx.add(off).readU32();
                if (val === TARGET_INT) {
                    report.findings.push({
                        where: 'this+' + off.toString(16),
                        addr: ecx.add(off).toString(),
                        type: 'INT match'
                    });
                }
            } catch(e) {}
        }

        // 2. 扫描栈帧 (esp到esp+0x100)
        for (var off = 0; off < 0x100; off += 4) {
            try {
                var val = esp.add(off).readU32();
                if (val === TARGET_INT) {
                    report.findings.push({
                        where: 'stack+' + off.toString(16),
                        addr: esp.add(off).toString(),
                        type: 'INT on stack'
                    });
                }
            } catch(e) {}
        }

        // 3. 扫描ebp帧帧 (ebp-0x100到ebp+0x100)
        for (var off = -0x100; off < 0x100; off += 4) {
            try {
                var val = ebp.add(off).readU32();
                if (val === TARGET_INT) {
                    report.findings.push({
                        where: 'ebp' + (off >= 0 ? '+' : '') + off.toString(16),
                        addr: ebp.add(off).toString(),
                        type: 'INT in frame'
                    });
                }
            } catch(e) {}
        }

        // 4. 跟踪this对象中的指针, 检查二级对象
        for (var off = 0; off < 0x40; off += 4) {
            try {
                var ptrVal = ecx.add(off).readPointer();
                // 检查指针是否有效(在堆范围内)
                if (ptrVal.compare(ptr(0x10000)) > 0 && ptrVal.compare(ptr(0x80000000)) < 0) {
                    // 在二级对象中搜ItemCode
                    for (var off2 = 0; off2 < 0x80; off2 += 4) {
                        try {
                            var val2 = ptrVal.add(off2).readU32();
                            if (val2 === TARGET_INT) {
                                report.findings.push({
                                    where: 'this+' + off.toString(16) + '->ptr+' + off2.toString(16),
                                    addr: ptrVal.add(off2).toString(),
                                    ptrAddr: ecx.add(off).toString(),
                                    type: 'INT via pointer'
                                });
                            }
                        } catch(e) {}
                    }
                }
            } catch(e) {}
        }

        // 5. 扫描栈上指针指向的对象
        for (var off = 0; off < 0x40; off += 4) {
            try {
                var ptrVal = esp.add(off).readPointer();
                if (ptrVal.compare(ptr(0x10000)) > 0 && ptrVal.compare(ptr(0x80000000)) < 0) {
                    for (var off2 = 0; off2 < 0x40; off2 += 4) {
                        try {
                            var val2 = ptrVal.add(off2).readU32();
                            if (val2 === TARGET_INT) {
                                report.findings.push({
                                    where: 'stack+' + off.toString(16) + '->ptr+' + off2.toString(16),
                                    addr: ptrVal.add(off2).toString(),
                                    ptrAddr: esp.add(off).toString(),
                                    type: 'INT via stack ptr'
                                });
                            }
                        } catch(e) {}
                    }
                }
            } catch(e) {}
        }

        // 6. dump this对象前64字节和栈前64字节供参考
        var thisHex = '';
        try {
            var buf = new Uint8Array(ecx.readByteArray(64));
            for (var i = 0; i < buf.length; i++) {
                thisHex += ('0' + buf[i].toString(16)).slice(-2) + ' ';
            }
        } catch(e) { thisHex = 'read failed'; }

        var stackHex = '';
        try {
            var sbuf = new Uint8Array(esp.readByteArray(64));
            for (var i = 0; i < sbuf.length; i++) {
                stackHex += ('0' + sbuf[i].toString(16)).slice(-2) + ' ';
            }
        } catch(e) { stackHex = 'read failed'; }

        report.thisHex = thisHex;
        report.stackHex = stackHex;

        send({t: 'hunt', report: report});
    }
});

send({t: 'ready', msg: 'ItemCode hunter ready. 触发角色加载.'});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Phase 4: ItemCode定位 === PID:{pid} ===')
    log(f'搜索 INT 50125461 (0x02FCDA95)')
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
                r = p['report']
                idx = r['callIdx']
                findings = r['findings']
                log(f'  [#{idx}] DynamicCreate1 ecx={r["ecx"]} eax={r["eax"]}')
                log(f'    this hex: {r.get("thisHex","")}')
                log(f'    stack hex: {r.get("stackHex","")}')
                if findings:
                    log(f'    !!! 找到 {len(findings)} 处ItemCode:')
                    for f in findings:
                        log(f'        {f["where"]} @ {f["addr"]} ({f["type"]})')
                else:
                    log(f'    未找到ItemCode (0x02FCDA95)')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Hook已激活。触发角色加载（进房间/换频道）。')
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

# diag_sprintf.py
# 诊断版本：看 sprintf 替换后实际加载了什么

import sys
import frida

sys.stdout.reconfigure(encoding='utf-8')

SRC_IC = 50125461  # 美丽梦想
DST_IC = 50126141  # 少年漫主角

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
'use strict';

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

var patchCount = 0;

// Hook sprintf
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            send({t: 'sprintf', fmt: fmt, ic: itemCode});

            if (itemCode === SRC_IC) {
                // 改参数
                args[2] = ptr(DST_IC);

                // 改栈
                var ebp = this.context.ebp;
                var addr = ebp.sub(0xD8);

                send({t: 'before_patch', ebp: ebp.toString(), addr: addr.toString(),
                      old_val: addr.readU32()});

                addr.writeU32(DST_IC);

                send({t: 'after_patch', new_val: addr.readU32()});

                patchCount++;
                send({t: 'patched', n: patchCount});
            }
        } catch(e) {
            send({t: 'error', msg: e.toString()});
        }
    }
});

// Hook CreateFileA/W 看实际打开的文件
var CreateFileA = Process.getModuleByName('kernel32.dll').getExportByName('CreateFileA');
var CreateFileW = Process.getModuleByName('kernel32.dll').getExportByName('CreateFileW');

Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        var path = readAscii(args[0], 200);
        if (path.indexOf('50125') >= 0 || path.indexOf('customize') >= 0) {
            send({t: 'CreateFileA', path: path});
        }
    }
});

Interceptor.attach(CreateFileW, {
    onEnter: function(args) {
        var path = args[0].readUtf16String();
        if (path.indexOf('50125') >= 0 || path.indexOf('customize') >= 0) {
            send({t: 'CreateFileW', path: path});
        }
    }
});

send({t: 'ready', src: SRC_IC, dst: DST_IC});
"""

def main():
    print('=== sprintf 诊断 ===')
    print(f'{SRC_IC} → {DST_IC}')
    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    print(f'PID: {pid}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'就绪: {p["src"]} → {p["dst"]}')
            elif t == 'sprintf':
                print(f'[sprintf] fmt={p["fmt"]} ic={p["ic"]}')
            elif t == 'before_patch':
                print(f'  替换前: [ebp-0xD8]={p["addr"]} 值={p["old_val"]}')
            elif t == 'after_patch':
                print(f'  替换后: 值={p["new_val"]}')
            elif t == 'patched':
                print(f'  ✅ 替换 #{p["n"]}')
            elif t == 'CreateFileA' or t == 'CreateFileW':
                print(f'[{t}] {p["path"]}')
            elif t == 'error':
                print(f'[ERROR] {p["msg"]}')

    script.on('message', on_msg)
    script.load()

    print('')
    print('进房间观察。命令: quit')
    print('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    print('已断开。')

if __name__ == '__main__':
    main()
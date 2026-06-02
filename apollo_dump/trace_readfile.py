"""
trace_readfile.py — 抓ReadFile调用栈, 找buffer分配来源
当检测到目标SSKF的第二次读取时, 打印完整backtrace
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'trace_readfile_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

import psutil
pid = None
for p in psutil.process_iter(['pid','name']):
    if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
        pid = p.info['pid']; break
if not pid:
    print('FreeStyle.exe 未运行'); sys.exit(1)

JS_CODE = r"""
'use strict';

var ReadFile = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');
var base = Process.getModuleByName('FreeStyle.exe').base;

send({t: 'ready', msg: 'ReadFile调用栈追踪就绪'});

var firstReadHandle = 0;
var count = 0;

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.sizeReq = args[2].toInt32();
        this.brPtr = args[3];
        this.handle = args[0].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 8) return;

            // 检查SSKF magic
            var m0 = this.buf.readU8();
            var m1 = this.buf.add(1).readU8();
            var m2 = this.buf.add(2).readU8();
            var m3 = this.buf.add(3).readU8();
            if (m0 !== 0x53 || m1 !== 0x53 || m2 !== 0x4B || m3 !== 0x46) return;

            var name = '';
            for (var i = 8; i < 72; i++) {
                var c = this.buf.add(i).readU8();
                if (c === 0) break;
                name += String.fromCharCode(c);
            }

            count++;

            // 只关注目标文件
            if (name.indexOf('50125461_FN') < 0) return;

            send({t: 'sskf', name: name, reqSize: this.sizeReq, bytesRead: bytesRead,
                  bufAddr: this.buf.toString(), handle: this.handle});

            // 第二次读取 (100864B) — 抓完整backtrace
            if (bytesRead > 512) {
                var bt;
                try {
                    bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                } catch(e) {
                    bt = Thread.backtrace(this.context, Backtracer.FUZZY);
                }
                var frames = bt.map(function(addr) {
                    var mod = Process.findModuleByAddress(addr);
                    var offset = mod ? '0x' + addr.sub(mod.base).toString(16) : '?';
                    return addr + ' (' + (mod ? mod.name : '?') + '+' + offset + ')';
                });
                send({t: 'backtrace', frames: frames, bufAddr: this.buf.toString(),
                      bufSize: bytesRead, reqSize: this.sizeReq});

                // 也读buffer前32字节
                var hex = '';
                for (var h = 0; h < 32; h++) {
                    hex += ('0' + this.buf.add(h).readU8().toString(16)).slice(-2) + ' ';
                }
                send({t: 'bufhex', hex: hex});
            }
        } catch(e) {
            send({t: 'error', msg: '' + e});
        }
    }
});
"""

LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
log(f'=== ReadFile调用栈追踪 === PID:{pid} ===')
log(f'日志: {LOG_FILE}')

session = frida.attach(pid)
script = session.create_script(JS_CODE)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'ready':
            log(f'  {p["msg"]}')
        elif t == 'sskf':
            log(f'  [SSKF] "{p["name"]}" req={p["reqSize"]} read={p["bytesRead"]} buf={p["bufAddr"]}')
        elif t == 'backtrace':
            log(f'  [BT] buf={p["bufAddr"]} size={p["bufSize"]} req={p["reqSize"]}')
            for i, f in enumerate(p['frames'][:10]):
                log(f'    #{i} {f}')
        elif t == 'bufhex':
            log(f'  [BUF] {p["hex"]}')
        elif t == 'error':
            log(f'  [错误] {p["msg"]}')
    elif msg['type'] == 'error':
        log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

script.on('message', on_msg)
script.load()

log('')
log('进房间触发角色加载。命令: quit')
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
if LOG_F: LOG_F.close()
print('已断开。')

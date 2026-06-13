# diag_char_code.py — 诊断 c%d.xml sprintf 调用，记录实际 IC 值
# 用法: python diag_char_code.py
# 启动游戏后运行，进房间触发角色加载，观察日志
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8')

JS_CODE = r"""
'use strict';

var msvcr = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = null;
var exports = msvcr.enumerateExports();
for (var i = 0; i < exports.length; i++) {
    if (exports[i].name === 'sprintf') sprintfAddr = exports[i].address;
}

if (!sprintfAddr) {
    send({t:'error', msg:'sprintf not found'});
} else {
    send({t:'ready', addr: sprintfAddr.toString()});
}

var CUSTOMIZE_PREFIX = 0x74737563; // "cust" LE

function readAscii(buf, maxLen) {
    try { return buf.readUtf8String(maxLen); } catch(e) {
        var s = '';
        for (var i = 0; i < maxLen; i++) {
            var c = buf.add(i).readU8();
            if (c === 0) break;
            s += String.fromCharCode(c);
        }
        return s;
    }
}

var callIndex = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            // 快速检查格式串是否以 "cust" 开头
            try { if (args[1].readU32() !== CUSTOMIZE_PREFIX) return; } catch(e) { return; }

            var fmt = readAscii(args[1], 80);
            // 只关心 customize\item 下的调用
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            callIndex++;
            var ic = args[2].toInt32();
            var isCcode = fmt.indexOf('c%d.xml') >= 0 || fmt.indexOf('C%d.xml') >= 0;
            var isIcode = fmt.indexOf('i%d.xml') >= 0 || fmt.indexOf('I%d.xml') >= 0;

            // 记录所有调用，c-code 特别标注
            send({
                t: 'sprintf',
                idx: callIndex,
                fmt: fmt,
                ic: ic,
                ic_unsigned: args[2].toUInt32(),
                ic_hex: '0x' + (args[2].toUInt32() >>> 0).toString(16),
                is_c: isCcode,
                is_i: isIcode,
            });

            // 如果是 c%d.xml，额外输出 ebp 上下文
            if (isCcode) {
                send({
                    t: 'c_code_detail',
                    idx: callIndex,
                    ic: ic,
                    ic_unsigned: args[2].toUInt32(),
                    ic_hex: '0x' + (args[2].toUInt32() >>> 0).toString(16),
                    ebp: this.context.ebp.toString(),
                    retaddr: this.returnAddress.toString(),
                });
            }
        } catch(e) {
            send({t:'err', msg: e.message});
        }
    }
});
"""

def on_message(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')

        if t == 'ready':
            print(f'[READY] sprintf @ {p["addr"]}')
        elif t == 'sprintf':
            tag = ''
            if p.get('is_c'): tag = ' ★ C-CODE'
            elif p.get('is_i'): tag = '   i-code'
            print(f'  #{p["idx"]:3d}  IC={p["ic"]:>12d} (0x{p["ic_unsigned"]:08X})  fmt={p["fmt"]}{tag}')
        elif t == 'c_code_detail':
            print(f'       └── C-CODE 详情: IC={p["ic"]} unsigned={p["ic_unsigned"]} hex={p["ic_hex"]} ret={p["retaddr"]}')
        elif t == 'error' or t == 'err':
            print(f'[ERR] {p.get("msg","")}')
        else:
            print(f'[{t}] {p}')
    elif msg['type'] == 'error':
        print(f'[FRIDA ERROR] {msg.get("description","")}')

print('=== c%d.xml 诊断 ===')
print('查找 FreeStyle.exe 进程 ...')

def find_pid():
    """通过系统命令查找 FreeStyle.exe 的 PID"""
    try:
        out = subprocess.check_output(
            ['wmic', 'process', 'where', "name='FreeStyle.exe'", 'get', 'ProcessId', '/value'],
            text=True
        )
        for line in out.strip().split('\n'):
            line = line.strip()
            if line.startswith('ProcessId='):
                return int(line.split('=', 1)[1])
    except Exception:
        pass
    return None

pid = None
while pid is None:
    pid = find_pid()
    if pid is None:
        time.sleep(1)

print(f'找到进程 PID={pid}')
session = frida.attach(pid)

print(f'已连接 PID={session._impl.pid if hasattr(session, "_impl") else "?"}')
script = session.create_script(JS_CODE)
script.on('message', on_message)
script.load()
print('Hook 已注入，进房间触发角色加载...')
print('Ctrl+C 退出\n')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n退出')
    session.detach()

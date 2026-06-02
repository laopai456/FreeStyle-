"""
hook_sprintf_replace.py — sprintf ItemCode替换 v2
当游戏调用 sprintf("customize\item\i%d.xml", ItemCode) 时,
将 ItemCode 50125461(美丽梦想发型) 替换为 50125711(紫色超赛发型)。

v2关键修复: 同时写[ebp-0xD8]，使LoadItemFile也拿到替换后的ItemCode。
否则LoadItemFile用原始ItemCode在多item BML中查找，找不到→光头。

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'sprintf_replace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767, 静态)
DST_IC = 50122451  # 鬼魅发型 (pak742, 动态)

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

var patchCount = 0;
var totalItemSprintf = 0;

// Hook MSVCR100 sprintf
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
send({t: 'step', msg: 'MSVCR100 sprintf=' + sprintfAddr});

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            // args[0]=buf, args[1]=fmt, args[2]=ItemCode
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0) return;
            if (fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            totalItemSprintf++;

            if (totalItemSprintf <= 200) {
                send({t: 'sprintf', n: totalItemSprintf, fmt: fmt, itemCode: itemCode});
            }

            // 替换目标ItemCode
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);  // 改sprintf参数(栈上的副本)

                // 关键修复: 同时改调用者的局部变量[ebp-0xD8]
                // 代码在0x1AE2576处: mov eax, [ebp-0xD8]; push eax → LoadItemFile arg
                // sprintf hook只改了栈上push的副本，[ebp-0xD8]仍是原值
                // LoadItemFile用它做BML内item查找，必须也改
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);

                patchCount++;
                send({t: 'patched', n: patchCount, orig: SRC_IC, new: DST_IC,
                      fmt: fmt, result_preview: 'i' + DST_IC + '.xml',
                      ebp_val: callerEbp.toString()});
            }
        } catch(e) {
            send({t: 'error', msg: 'sprintf hook: ' + e});
        }
    }
});

// ==========================================
// 诊断: 监控ReadFile看BML是否被读取
// ==========================================
var base = ptr('0x400000');
var ReadFile = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');
var readfileCount = 0;

Interceptor.attach(ReadFile, {
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 8) return;
            var buf = this.rbuf;
            var name = readAscii(buf, 64);
            // 只看SSKF和BML相关的
            if (name.indexOf('SSKF') >= 0 || name.indexOf('50125') >= 0) {
                readfileCount++;
                send({t: 'readfile', n: readfileCount, name: name, bytes: bytesRead});
            }
        } catch(e) {}
    },
    onEnter: function(args) {
        this.rbuf = args[1];
        this.brPtr = args[3];
    }
});

// ==========================================
// 诊断: 监控AcquireSMD调用者看mesh是否加载
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;

Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            if (path.indexOf('50125') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'sprintf替换就绪: ' + SRC_IC + ' → ' + DST_IC + ' (含ReadFile+AcquireSMD诊断)'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            patches: patchCount,
            totalSprintf: totalItemSprintf
        });
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
    log(f'=== sprintf ItemCode替换 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想发型) → {DST_IC}(紫色超赛发型)')
    log(f'前置: sc.exe stop ApolloProtect')
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
                log(f'  {p["msg"]}')
            elif t == 'sprintf':
                log(f'  [sprintf] #{p["n"]} fmt="{p["fmt"]}" IC={p["itemCode"]}')
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]} {p["orig"]}→{p["new"]} → {p["result_preview"]}')
            elif t == 'readfile':
                log(f'  [ReadFile] #{p["n"]} name="{p["name"]}" bytes={p["bytes"]}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。观察是否显示紫色超赛发型。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
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

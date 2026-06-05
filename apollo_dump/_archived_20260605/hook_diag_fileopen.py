"""
hook_diag_fileopen.py — 诊断LoadItemFile内部的BML文件打开
关键: hook 0x1ACE30D处的文件打开调用，看返回值和Group确定逻辑

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_fileopen_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

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
var base = ptr('0x400000');
var patchCount = 0;

// ==========================================
// 1. Dump 0x1ACDF33 函数代码（文件打开函数）
// ==========================================
var fileOpenFunc = base.add(0x1ACDF33);
try {
    var fofBytes = new Uint8Array(fileOpenFunc.readByteArray(192));
    var lines = [];
    for (var i = 0; i < 192; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < 192; j++) {
            hex += ('0' + fofBytes[i + j].toString(16)).slice(-2) + ' ';
        }
        lines.push('0x' + (0x1ACDF33 + i).toString(16) + ': ' + hex);
    }
    send({t: 'code_dump', label: 'FileOpenFunc_0x1ACDF33', lines: lines});
} catch(e) {
    send({t: 'error', msg: 'dump failed: ' + e});
}

// ==========================================
// 2. Hook LoadItemFile内的sprintf (RVA 0x1ACE343)
//    这个sprintf构建BML文件名
// ==========================================
var sprintfInLIF = base.add(0x1ACE343);
try {
    Interceptor.attach(sprintfInLIF, {
        onEnter: function(args) {
            // 这个sprintf的参数: sprintf(buf, fmt, iItemCode)
            var fmt = readAscii(args[1], 64);
            var ic = args[2].toInt32();
            send({t: 'lif_sprintf', fmt: fmt, iItemCode: ic});
        }
    });
    send({t: 'step', msg: 'LoadItemFile内sprintf hook已设置'});
} catch(e) {
    send({t: 'error', msg: 'LIF sprintf hook失败: ' + e});
}

// ==========================================
// 3. Hook 文件打开调用 (RVA 0x1ACE30D)
//    call 0x1ACDF33 — 检查返回值
// ==========================================
var fileOpenCallAddr = base.add(0x1ACE312); // call返回后的地址
try {
    Interceptor.attach(fileOpenCallAddr, {
        onEnter: function(args) {
            // 此时EAX = 文件打开调用的返回值
            var retVal = this.context.eax.toInt32();
            // 从栈上获取iItemCode
            var ebp = this.context.ebp;
            var iItemCode = ebp.add(0x8).readU32();
            send({t: 'fileopen_ret', iItemCode: iItemCode, retEAX: retVal,
                  success: retVal !== 0});
        }
    });
    send({t: 'step', msg: '文件打开返回值hook已设置 (0x1ACE312)'});
} catch(e) {
    send({t: 'error', msg: 'fileopen ret hook失败: ' + e});
}

// ==========================================
// 4. Hook 0x1ACDF33 函数入口 — 看参数和内部行为
// ==========================================
try {
    Interceptor.attach(fileOpenFunc, {
        onEnter: function(args) {
            // thiscall: ecx=this, args[0]=[esp+4]
            // 调用: push flag(0), push &iItemCode, mov ecx=this, call
            // args[0] = &iItemCode (pointer on stack)
            // args[1] = flag (0)
            var pItemCodePtr = args[0];
            var itemCode = pItemCodePtr.readU32();
            var flag = args[1].toInt32();
            this._itemCode = itemCode;
            send({t: 'fof_enter', iItemCode: itemCode, flag: flag, ecx: this.context.ecx.toString()});
        },
        onLeave: function(retval) {
            var ret = retval.toInt32();
            var ic = this._itemCode || 0;
            send({t: 'fof_leave', iItemCode: ic, ret: ret, success: ret !== 0});
        }
    });
    send({t: 'step', msg: '0x1ACDF33 函数hook已设置'});
} catch(e) {
    send({t: 'error', msg: '0x1ACDF33 hook失败: ' + e});
}

// ==========================================
// 5. sprintf + [ebp-0xD8] 双重替换
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;
            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);
                patchCount++;
            }
        } catch(e) {}
    }
});

// AcquireSMD
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;
Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            if (path.indexOf('50125') >= 0 || path.indexOf('768') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '文件打开诊断就绪'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, acquires: acquireCount});
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
    log(f'=== 文件打开诊断 === PID:{pid} ===')

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
            elif t == 'fof_enter':
                log(f'  [文件打开] iItemCode={p["iItemCode"]} flag={p["flag"]} ecx={p["ecx"]}')
            elif t == 'fof_leave':
                log(f'  [文件打开返回] iItemCode={p["iItemCode"]} ret={p["ret"]} {"成功" if p["success"] else "失败!"}')
            elif t == 'fileopen_ret':
                log(f'  [文件打开结果] iItemCode={p["iItemCode"]} EAX={p["retEAX"]} {"成功" if p["success"] else "失败!"}')
            elif t == 'lif_sprintf':
                log(f'  [LIF sprintf] fmt="{p["fmt"]}" iItemCode={p["iItemCode"]}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}"')
            elif t == 'code_dump':
                log(f'  [代码] {p["label"]}:')
                for line in p['lines']:
                    log(f'    {line}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
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

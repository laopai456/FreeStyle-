"""
hook_diag_loaditem.py — 诊断LoadItemFile内部Group确定逻辑
1. sprintf + [ebp-0xD8] 双重替换
2. dump LoadItemFile入口代码，找Group构建逻辑
3. hook LoadItemFile入口，验证iItemCode是否已替换

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_loaditem_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
// 1. Dump LoadItemFile入口代码 (RVA 0x1ACE1C0)
// ==========================================
var loadItemFileAddr = base.add(0x1ACE1C0);
send({t: 'step', msg: 'LoadItemFile地址: ' + loadItemFileAddr});

try {
    var lifBytes = new Uint8Array(loadItemFileAddr.readByteArray(256));
    var lines = [];
    for (var i = 0; i < 256; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < 256; j++) {
            hex += ('0' + lifBytes[i + j].toString(16)).slice(-2) + ' ';
        }
        lines.push('0x' + (0x1ACE1C0 + i).toString(16) + ': ' + hex);
    }
    send({t: 'code_dump', label: 'LoadItemFile', lines: lines});
} catch(e) {
    send({t: 'error', msg: 'LoadItemFile dump failed: ' + e});
}

// 也dump更大范围
try {
    var lifBytes2 = new Uint8Array(loadItemFileAddr.add(256).readByteArray(256));
    var lines2 = [];
    for (var i = 0; i < 256; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < 256; j++) {
            hex += ('0' + lifBytes2[i + j].toString(16)).slice(-2) + ' ';
        }
        lines2.push('0x' + (0x1ACE1C0 + 256 + i).toString(16) + ': ' + hex);
    }
    send({t: 'code_dump', label: 'LoadItemFile+256', lines: lines2});
} catch(e) {}

// ==========================================
// 2. Hook LoadItemFile入口 — 验证参数
// ==========================================
try {
    Interceptor.attach(loadItemFileAddr, {
        onEnter: function(args) {
            // thiscall: ecx=this, [esp+4]=arg1, [esp+8]=arg2, ...
            // 从调用代码: push 0, push local, push szFilename, push iItemCode, mov ecx,this, call
            // 所以: arg1=[esp+4]=iItemCode, arg2=[esp+8]=szFilename, arg3=[esp+C]=local, arg4=[esp+10]=0
            // 但Frida的args索引: args[0]=esp+4, args[1]=esp+8, args[2]=esp+C, args[3]=esp+10
            var iItemCode = args[0].toInt32();
            var szFilename = args[1];
            var fname = readAscii(szFilename, 80);

            send({t: 'loaditem', iItemCode: iItemCode, szFilename: fname, ecx: this.context.ecx.toString()});

            // dump栈上的更多参数
            var esp = this.context.esp;
            var stackVals = [];
            for (var i = 0; i < 8; i++) {
                stackVals.push(esp.add(4 + i * 4).readU32());
            }
            send({t: 'loaditem_stack', vals: stackVals});
        }
    });
    send({t: 'step', msg: 'LoadItemFile入口hook已设置'});
} catch(e) {
    send({t: 'error', msg: 'LoadItemFile hook失败: ' + e});
}

// ==========================================
// 3. sprintf hook — 双重替换
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
                // 1) 改sprintf参数
                args[2] = ptr(DST_IC);

                // 2) 改调用者局部变量[ebp-0xD8]
                var callerEbp = this.context.ebp;
                var targetAddr = callerEbp.sub(0xD8);
                var oldVal = targetAddr.readU32();
                targetAddr.writeU32(DST_IC);
                var newVal = targetAddr.readU32();

                patchCount++;
                send({t: 'patched', n: patchCount,
                      ebp: callerEbp.toString(),
                      old_ebpD8: oldVal,
                      new_ebpD8: newVal,
                      write_ok: newVal === DST_IC});
            }
        } catch(e) {
            send({t: 'error', msg: 'sprintf hook error: ' + e});
        }
    }
});

// ==========================================
// 4. AcquireSMD监控
// ==========================================
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

send({t: 'ready', msg: 'LoadItemFile诊断就绪'});

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
    log(f'=== LoadItemFile诊断 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')
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
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]} ebp={p["ebp"]} '
                    f'[ebp-0xD8]: {p["old_ebpD8"]}→{p["new_ebpD8"]} '
                    f'write_ok={p["write_ok"]}')
            elif t == 'loaditem':
                log(f'  [LoadItemFile] iItemCode={p["iItemCode"]} '
                    f'szFilename="{p["szFilename"]}" ecx={p["ecx"]}')
            elif t == 'loaditem_stack':
                log(f'  [LoadItemFile栈] {p["vals"]}')
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
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

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

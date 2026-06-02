"""
hook_diag_code.py — 诊断LoadItemFile调用链 + 同时替换iItemCode
1. sprintf替换: 50125461 → 50125711
2. dump sprintf返回后的代码，找LoadItemFile调用点
3. 在LoadItemFile调用前替换iItemCode参数

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_code_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767, 静态)
DST_IC = 50125711  # 紫色超赛发型 (pak768, 动态)

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

// ==========================================
// 1. Dump代码: sprintf返回地址附近
// ==========================================
var sprintfRetAddr = base.add(0x1AE2563);
send({t: 'step', msg: 'sprintf返回地址: ' + sprintfRetAddr});

// dump sprintf返回地址前后各64字节
var dumpStart = base.add(0x1AE2520);
var dumpSize = 160;
try {
    var bytes = new Uint8Array(dumpStart.readByteArray(dumpSize));
    var lines = [];
    for (var i = 0; i < dumpSize; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < dumpSize; j++) {
            var b = bytes[i + j];
            hex += ('0' + b.toString(16)).slice(-2) + ' ';
        }
        var rva = 0x1AE2520 + i;
        lines.push('0x' + rva.toString(16) + ': ' + hex);
    }
    send({t: 'code_dump', addr: '0x1AE2520', size: dumpSize, lines: lines});
} catch(e) {
    send({t: 'error', msg: 'code dump failed: ' + e});
}

// 也dump更后面的代码（找LoadItemFile调用）
var dumpStart2 = base.add(0x1AE2580);
var dumpSize2 = 128;
try {
    var bytes2 = new Uint8Array(dumpStart2.readByteArray(dumpSize2));
    var lines2 = [];
    for (var i = 0; i < dumpSize2; i += 16) {
        var hex = '';
        for (var j = 0; j < 16 && i + j < dumpSize2; j++) {
            var b = bytes2[i + j];
            hex += ('0' + b.toString(16)).slice(-2) + ' ';
        }
        var rva = 0x1AE2580 + i;
        lines2.push('0x' + rva.toString(16) + ': ' + hex);
    }
    send({t: 'code_dump', addr: '0x1AE2580', size: dumpSize2, lines: lines2});
} catch(e) {}

// ==========================================
// 2. sprintf hook — 替换ItemCode + 捕获上下文
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var patchCount = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();

            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                patchCount++;
                send({t: 'patched', n: patchCount, msg: 'sprintf替换: ' + SRC_IC + ' → ' + DST_IC});

                // 捕获调用时的寄存器状态（用于分析LoadItemFile参数传递）
                send({t: 'regs', eax: this.context.eax, ecx: this.context.ecx,
                      edx: this.context.edx, ebx: this.context.ebx,
                      esi: this.context.esi, edi: this.context.edi,
                      ebp: this.context.ebp, esp: this.context.esp});
            }
        } catch(e) {}
    }
});

// ==========================================
// 3. Hook sprintf返回地址 — 修改iItemCode参数
// ==========================================
// sprintf返回后，调用代码会用原始iItem调用LoadItemFile
// 我们需要在那个时刻修改iItem值
// 策略: hook sprintf返回地址的下一行代码

// 先用stalker或简单hook在sprintf返回时拦截
// 使用Interceptor.attach在返回地址处hook
var sprintfRetHook = null;
try {
    sprintfRetHook = Interceptor.attach(sprintfRetAddr, {
        onEnter: function(args) {
            // 这个在sprintf返回后被调用
            // 此时ESP指向调用者的栈帧
            // 需要找到iItem在栈上的位置

            // dump ESP附近32字节看栈内容
            try {
                var esp = this.context.esp;
                var stackDump = [];
                for (var i = 0; i < 16; i++) {
                    var val = esp.add(i * 4).readU32();
                    stackDump.push('[' + (i*4) + ']=' + val);
                }
                send({t: 'stack_at_ret', stack: stackDump});
            } catch(e) {}
        }
    });
    send({t: 'step', msg: 'sprintf返回地址hook已设置'});
} catch(e) {
    send({t: 'error', msg: 'sprintf返回hook失败: ' + e});
}

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
            if (path.indexOf('50125') >= 0 || path.indexOf('50711') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '诊断就绪: sprintf替换+代码dump+栈分析'});

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
    log(f'=== 诊断: 代码dump + iItemCode分析 === PID:{pid} ===')
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
                log(f'  [替换!] {p["msg"]}')
            elif t == 'regs':
                log(f'  [寄存器] eax={p["eax"]} ecx={p["ecx"]} edx={p["edx"]}')
                log(f'           ebx={p["ebx"]} esi={p["esi"]} edi={p["edi"]}')
                log(f'           ebp={p["ebp"]} esp={p["esp"]}')
            elif t == 'stack_at_ret':
                log(f'  [栈@返回] {" ".join(p["stack"])}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}"')
            elif t == 'code_dump':
                log(f'  [代码dump] addr={p["addr"]} size={p["size"]}')
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

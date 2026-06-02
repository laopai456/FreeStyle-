"""
crash_diag.py — 崩溃诊断: 在v4 hook基础上捕获异常现场
捕获EIP、寄存器、调用栈, 定位SSKF解析崩溃位置
前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'crash_diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

function readName(buf, offset, maxLen) {
    var s = '';
    for (var i = offset; i < offset + maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function hexAddr(p) {
    return ('00000000' + p.toString(16)).slice(-8);
}

send({t: 'step', msg: 'JS开始执行'});

// ==========================================
// 1. CRT函数
// ==========================================
var crtMod = Process.getModuleByName('msvcrt.dll');
var fopenAddr  = crtMod.getExportByName('fopen');
var freadAddr  = crtMod.getExportByName('fread');
var fcloseAddr = crtMod.getExportByName('fclose');

var _fopen  = new NativeFunction(fopenAddr,  'pointer', ['pointer', 'pointer']);
var _fread  = new NativeFunction(freadAddr,  'int', ['pointer', 'int', 'int', 'pointer']);
var _fclose = new NativeFunction(fcloseAddr, 'int', ['pointer']);

send({t: 'step', msg: 'CRT函数OK'});

// ==========================================
// 2. 加载目标SSKF数据
// ==========================================
var TARGET_SIZE = 270264;
var targetPath = Memory.allocUtf8String('C:\\tmp\\sskf\\sskf_50125711_full.bin');
var modeStr = Memory.allocUtf8String('rb');

var fp = _fopen(targetPath, modeStr);
if (fp.isNull()) {
    send({t: 'error', msg: '无法打开目标文件'});
} else {
    var targetBuf = Memory.alloc(TARGET_SIZE);
    var totalRead = 0;
    while (totalRead < TARGET_SIZE) {
        var chunk = _fread(targetBuf.add(totalRead), 1, TARGET_SIZE - totalRead, fp);
        if (chunk <= 0) break;
        totalRead += chunk;
    }
    _fclose(fp);
    send({t: 'loaded', size: totalRead, magic: readName(targetBuf, 0, 4),
          name: readName(targetBuf, 8, 64)});
}

// ==========================================
// 3. 异常捕获 — 最先注册!
// ==========================================
var gameBase = Process.getModuleByName('FreeStyle.exe').base;

Process.setExceptionHandler(function(details) {
    var ctx = details.context;
    var addr = details.address;
    var mod = Process.findModuleByAddress(addr);

    send({t: 'crash',
          type: details.type,
          address: '0x' + hexAddr(addr),
          module: mod ? mod.name : 'unknown',
          moduleBase: mod ? '0x' + hexAddr(mod.base) : '?',
          rva: mod ? '0x' + hexAddr(addr.sub(mod.base)) : '?',
          eax: '0x' + hexAddr(ctx.eax),
          ebx: '0x' + hexAddr(ctx.ebx),
          ecx: '0x' + hexAddr(ctx.ecx),
          edx: '0x' + hexAddr(ctx.edx),
          esi: '0x' + hexAddr(ctx.esi),
          edi: '0x' + hexAddr(ctx.edi),
          esp: '0x' + hexAddr(ctx.esp),
          ebp: '0x' + hexAddr(ctx.ebp),
          eip: '0x' + hexAddr(ctx.eip)
    });

    // 抓backtrace
    var bt;
    try {
        bt = Thread.backtrace(ctx, Backtracer.FUZZY);
    } catch(e) {
        bt = [];
    }
    var frames = bt.map(function(a) {
        var m = Process.findModuleByAddress(a);
        var rva = m ? '0x' + hexAddr(a.sub(m.base)) : '?';
        return '0x' + hexAddr(a) + ' (' + (m ? m.name : '?') + '+' + rva + ')';
    });
    send({t: 'backtrace', frames: frames});

    // 读EIP附近指令 (崩溃点前后16字节)
    try {
        var crashBytes = [];
        for (var i = -8; i < 24; i++) {
            crashBytes.push(('0' + addr.add(i).readU8().toString(16)).slice(-2));
        }
        send({t: 'crash_code', offset: '-8..+24', hex: crashBytes.join(' ')});
    } catch(e) {}

    // 读ESP附近 (栈内容)
    try {
        var stackWords = [];
        for (var si = 0; si < 16; si++) {
            var val = ctx.esp.add(si * 4).readPointer();
            stackWords.push('0x' + hexAddr(val));
        }
        send({t: 'stack', words: stackWords});
    } catch(e) {}

    return false; // 不处理异常, 让游戏崩溃
});

send({t: 'step', msg: '异常捕获已注册'});

// ==========================================
// 4. 状态机 + malloc hook
// ==========================================
var STATE_IDLE = 0;
var STATE_FIRST_READ = 1;
var STATE_MALLOC_EXPANDED = 2;

var state = STATE_IDLE;
var trackedHandle = 0;
var expandedBuf = null;
var expandedSize = 0;
var totalSSKF = 0;
var patchCount = 0;

var allocHooks = [];
try {
    var msvcr100Mod = Process.getModuleByName('MSVCR100.dll');
    allocHooks.push({name: 'MSVCR100 malloc', addr: msvcr100Mod.getExportByName('malloc')});
    allocHooks.push({name: 'MSVCR100 new', addr: msvcr100Mod.getExportByName('??2@YAPAXI@Z')});
} catch(e) {}
try {
    allocHooks.push({name: 'msvcrt malloc', addr: crtMod.getExportByName('malloc')});
} catch(e) {}

for (var hi = 0; hi < allocHooks.length; hi++) {
    (function(hookInfo) {
        Interceptor.attach(hookInfo.addr, {
            onEnter: function(args) {
                this.origSize = args[0].toInt32();
                this.modified = false;
                if (state !== STATE_FIRST_READ) return;
                if (this.origSize >= 90000 && this.origSize <= 120000) {
                    args[0] = ptr(TARGET_SIZE);
                    expandedSize = TARGET_SIZE;
                    state = STATE_MALLOC_EXPANDED;
                    this.modified = true;
                    send({t: 'malloc_expand', source: hookInfo.name,
                          origReq: this.origSize, newSize: TARGET_SIZE});
                }
            },
            onLeave: function(retval) {
                if (this.modified && expandedBuf === null) {
                    expandedBuf = ptr(retval.toString());
                    send({t: 'malloc_result', addr: expandedBuf.toString(), size: expandedSize});
                }
            }
        });
    })(allocHooks[hi]);
}

// ==========================================
// 5. MSVCR100 fread hook
// ==========================================
var msvcr100Fread = Process.getModuleByName('MSVCR100.dll').getExportByName('fread');

Interceptor.attach(msvcr100Fread, {
    onEnter: function(args) {
        this.bufPtr = args[0];
        this.elemSize = args[1].toInt32();
        this.elemCount = args[2].toInt32();
        this.shouldPatch = false;
        if (state === STATE_MALLOC_EXPANDED && expandedBuf !== null) {
            if (this.bufPtr.equals(expandedBuf)) {
                this.shouldPatch = true;
                send({t: 'fread_target', buf: this.bufPtr.toString(),
                      req: this.elemSize * this.elemCount});
            }
        }
    },
    onLeave: function(retval) {
        if (!this.shouldPatch) return;
        if (this.elemSize !== 1) {
            send({t: 'error', msg: 'elemSize!=1'});
            return;
        }
        var origRet = retval.toInt32();
        Memory.copy(this.bufPtr, targetBuf, TARGET_SIZE);
        retval.replace(TARGET_SIZE);
        patchCount++;
        state = STATE_IDLE;
        expandedBuf = null;
        send({t: 'fread_done', origRet: origRet, newRet: TARGET_SIZE,
              name: readName(this.bufPtr, 8, 64)});
    }
});

// ==========================================
// 6. ReadFile hook (header + 日志)
// ==========================================
var ReadFile = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');

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
            var m0 = this.buf.readU8();
            var m1 = this.buf.add(1).readU8();
            var m2 = this.buf.add(2).readU8();
            var m3 = this.buf.add(3).readU8();
            if (m0 !== 0x53 || m1 !== 0x53 || m2 !== 0x4B || m3 !== 0x46) return;

            totalSSKF++;
            var name = readName(this.buf, 8, 64);

            if (name.indexOf('50125461_FN') >= 0 && bytesRead === 512 && state === STATE_IDLE) {
                Memory.copy(this.buf, targetBuf, 512);
                state = STATE_FIRST_READ;
                trackedHandle = this.handle;
                send({t: 'header_patched', name: readName(this.buf, 8, 64)});
                return;
            }

            if (state === STATE_MALLOC_EXPANDED && this.handle === trackedHandle && bytesRead > 512) {
                send({t: 'readfile2', bytesRead: bytesRead, buf: this.buf.toString()});
            }
        } catch(e) {
            send({t: 'error', msg: 'ReadFile: ' + e});
        }
    }
});

send({t: 'ready', msg: '崩溃诊断v4就绪 — 异常捕获已开启'});
"""


def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 崩溃诊断 === PID:{pid} ===')
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
            elif t == 'loaded':
                log(f'  目标: {p["size"]}B {p["magic"]} {p["name"]}')
            elif t == 'header_patched':
                log(f'  [Header] → {p["name"]}')
            elif t == 'malloc_expand':
                log(f'  [malloc] {p["origReq"]}B→{p["newSize"]}B ({p["source"]})')
            elif t == 'malloc_result':
                log(f'  [malloc buf] {p["addr"]}')
            elif t == 'fread_target':
                log(f'  [fread] buf={p["buf"]} req={p["req"]}B')
            elif t == 'fread_done':
                log(f'  [fread替换] {p["origRet"]}B→{p["newRet"]}B name="{p["name"]}"')
            elif t == 'readfile2':
                log(f'  [ReadFile2] {p["bytesRead"]}B buf={p["buf"]}')
            elif t == 'crash':
                log(f'  ===== 崩溃 =====')
                log(f'  类型: {p["type"]}')
                log(f'  地址: {p["address"]} ({p["module"]}+{p["rva"]})')
                log(f'  模块基址: {p["moduleBase"]}')
                log(f'  EAX={p["eax"]} EBX={p["ebx"]} ECX={p["ecx"]} EDX={p["edx"]}')
                log(f'  ESI={p["esi"]} EDI={p["edi"]} ESP={p["esp"]} EBP={p["ebp"]}')
                log(f'  EIP={p["eip"]}')
            elif t == 'backtrace':
                log(f'  [调用栈]')
                for i, f in enumerate(p['frames'][:12]):
                    log(f'    #{i} {f}')
            elif t == 'crash_code':
                log(f'  [崩溃指令] {p["hex"]}')
            elif t == 'stack':
                log(f'  [栈] {", ".join(p["words"])}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
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
            if cmd in ('quit', 'q', 'exit'):
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

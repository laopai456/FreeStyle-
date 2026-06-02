"""
hook_acquire_caller.py — Hook AcquireSMD的调用者
目标: 在 0x1EEBAE3 附近找到调用者函数入口, hook它
      那里应该还有SString/ItemCode参数

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_caller_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var modSize = Process.getModuleByName('FreeStyle.exe').size;

// ==========================================
// Step 1: 找到调用者函数入口
// AcquireSMD返回地址 0x1EEBAE3, 往前扫描找函数prologue
// ==========================================
var callerRetAddr = base.add(0x01EEBAE3);
var callerEntry = null;

// 常见 MSVC prologue 模式
var prologues = [
    [0x55, 0x8B, 0xEC],                    // push ebp; mov ebp, esp
    [0x55, 0x8B, 0xEC, 0x83, 0xEC],        // push ebp; mov ebp, esp; sub esp, XX
    [0x55, 0x8B, 0xEC, 0x6A, 0xFF],        // push ebp; mov ebp, esp; push -1 (SEH)
    [0x55, 0x8B, 0xEC, 0x51],              // push ebp; mov ebp, esp; push ecx
];

send({t: 'scan_start', retAddr: callerRetAddr.toString()});

// 读取调用者函数附近的代码 (往前0x800字节)
var codeSize = 0x800;
var codeStart = callerRetAddr.sub(codeSize);
var codeBytes;
try {
    codeBytes = new Uint8Array(codeStart.readByteArray(codeSize));
} catch(e) {
    send({t: 'error', msg: '读取代码失败: ' + e});
}

if (codeBytes) {
    // 从返回地址往回找prologue
    for (var off = codeSize - 1; off >= 0; off--) {
        var match = false;
        for (var p = 0; p < prologues.length; p++) {
            var pro = prologues[p];
            var allMatch = true;
            for (var j = 0; j < pro.length && (off + j) < codeBytes.length; j++) {
                if (codeBytes[off + j] !== pro[j]) {
                    allMatch = false;
                    break;
                }
            }
            if (allMatch && pro.length > 0) {
                // 检查前面是否有ret/nop/padding (函数边界标志)
                var prevByte = off > 0 ? codeBytes[off - 1] : 0xCC;
                var isBoundary = (prevByte === 0xC3) ||  // ret
                                 (prevByte === 0xCC) ||  // int3 padding
                                 (prevByte === 0x90) ||  // nop
                                 (off === 0);

                var entryAddr = codeStart.add(off);
                var rva = entryAddr.sub(base);

                // 读前16字节确认
                var preview = '';
                for (var k = 0; k < 16 && (off + k) < codeBytes.length; k++) {
                    preview += ('0' + codeBytes[off + k].toString(16)).slice(-2) + ' ';
                }

                send({
                    t: 'candidate',
                    rva: '0x' + rva.toString(16),
                    addr: entryAddr.toString(),
                    dist: '0x' + (codeSize - off).toString(16) + ' bytes before retAddr',
                    isBoundary: isBoundary,
                    preview: preview,
                    prologueIdx: p
                });

                // 选最近的边界prologue作为入口
                if (isBoundary && !callerEntry) {
                    callerEntry = entryAddr;
                }
            }
        }
    }
}

if (!callerEntry) {
    // 没找到带边界的, 用最近的prologue
    send({t: 'warn', msg: '未找到带边界的prologue, 尝试最近的一个'});
    // 重新扫描, 不要求边界
    for (var off = codeSize - 1; off >= 0; off--) {
        for (var p = 0; p < prologues.length; p++) {
            var pro = prologues[p];
            var allMatch = true;
            for (var j = 0; j < pro.length && (off + j) < codeBytes.length; j++) {
                if (codeBytes[off + j] !== pro[j]) { allMatch = false; break; }
            }
            if (allMatch) {
                callerEntry = codeStart.add(off);
                break;
            }
        }
        if (callerEntry) break;
    }
}

if (!callerEntry) {
    send({t: 'error', msg: '找不到函数入口!'});
} else {
    var entryRva = callerEntry.sub(base);
    send({t: 'entry_found', addr: callerEntry.toString(), rva: '0x' + entryRva.toString(16)});

    // ==========================================
    // Step 2: Hook 调用者函数入口
    // ==========================================
    var callerCallCount = 0;

    Interceptor.attach(callerEntry, {
        onEnter: function(args) {
            callerCallCount++;
            var idx = callerCallCount;
            if (idx > 20) return;  // 只记录前20次

            var esp = this.context.esp;
            var ebp = this.context.ebp;
            var ecx = this.context.ecx;
            var eax = this.context.eax;
            var edx = this.context.edx;
            var esi = this.context.esi;
            var edi = this.context.edi;

            // 读栈参数
            var stackArgs = [];
            for (var i = 0; i < 12; i++) {
                try {
                    var val = esp.add(4 + i * 4).readU32();
                    stackArgs.push('0x' + val.toString(16));
                } catch(e) { stackArgs.push('err'); }
            }

            // 读ecx(this)对象前128字节, 搜索字符串
            var thisStrings = [];
            try {
                for (var off = 0; off < 0x80; off += 4) {
                    var ptrVal = ecx.add(off).readU32();
                    if (ptrVal > 0x10000 && ptrVal < 0x80000000) {
                        // 尝试读ANSI字符串
                        try {
                            var s = ptr(ptrVal).readAnsiString(64);
                            if (s && s.length > 2 && /[a-zA-Z0-9_\\\.]/.test(s)) {
                                thisStrings.push({
                                    off: '0x' + off.toString(16),
                                    str: s.substring(0, 80)
                                });
                            }
                        } catch(e) {}
                    }
                }
            } catch(e) {}

            // 读栈参数指向的字符串
            var stackStrings = [];
            for (var i = 0; i < 8; i++) {
                try {
                    var ptrVal = esp.add(4 + i * 4).readU32();
                    if (ptrVal > 0x10000 && ptrVal < 0x80000000) {
                        var s = ptr(ptrVal).readAnsiString(80);
                        if (s && s.length > 2 && /[a-zA-Z0-9_\\\.]/.test(s)) {
                            stackStrings.push({
                                argIdx: i,
                                ptr: '0x' + ptrVal.toString(16),
                                str: s.substring(0, 80)
                            });
                        }
                        // 也尝试读SString结构 (前4字节=length, 后面是data)
                        try {
                            var strLen = ptr(ptrVal).readU32();
                            if (strLen > 0 && strLen < 100) {
                                var strData = '';
                                for (var b = 0; b < strLen && b < 80; b++) {
                                    var c = ptr(ptrVal).add(4 + b).readU8();
                                    if (c >= 0x20 && c < 0x7F) strData += String.fromCharCode(c);
                                    else strData += '.';
                                }
                                if (strData.length > 2) {
                                    stackStrings.push({
                                        argIdx: i,
                                        ptr: '0x' + ptrVal.toString(16),
                                        sstring: strData.substring(0, 80),
                                        len: strLen
                                    });
                                }
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
            }

            // 也在eax/edx/esi/edi里搜索字符串指针
            var regStrings = [];
            var regs = [
                {name: 'eax', val: eax},
                {name: 'edx', val: edx},
                {name: 'esi', val: esi},
                {name: 'edi', val: edi}
            ];
            for (var r = 0; r < regs.length; r++) {
                var rv = regs[r].val;
                try {
                    var ptrVal = ptr(rv.toString()).readU32();
                    // check if rv itself points to a string
                    var s = ptr(rv.toString()).readAnsiString(80);
                    if (s && s.length > 2 && /[a-zA-Z0-9_\\\.]/.test(s)) {
                        regStrings.push({reg: regs[r].name, str: s.substring(0, 80)});
                    }
                } catch(e) {}
                // also check if rv points to SString struct
                try {
                    var strLen = ptr(rv.toString()).readU32();
                    if (strLen > 0 && strLen < 100) {
                        var strData = '';
                        for (var b = 0; b < strLen && b < 80; b++) {
                            var c = ptr(rv.toString()).add(4 + b).readU8();
                            if (c >= 0x20 && c < 0x7F) strData += String.fromCharCode(c);
                            else strData += '.';
                        }
                        if (strData.length > 2) {
                            regStrings.push({reg: regs[r].name, sstring: strData, len: strLen});
                        }
                    }
                } catch(e) {}
            }

            send({
                t: 'caller_call',
                idx: idx,
                regs: {
                    eax: '0x' + (eax.toInt32() >>> 0).toString(16),
                    ecx: ecx.toString(),
                    edx: '0x' + (edx.toInt32() >>> 0).toString(16),
                    esi: esi.toString(),
                    edi: edi.toString()
                },
                stackArgs: stackArgs,
                thisStrings: thisStrings,
                stackStrings: stackStrings,
                regStrings: regStrings
            });

            // 前3次做backtrace
            if (idx <= 3) {
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                var frames = [];
                for (var i = 0; i < bt.length && i < 15; i++) {
                    frames.push('0x' + bt[i].sub(base).toString(16));
                }
                send({t: 'caller_bt', idx: idx, frames: frames});
            }
        }
    });

    send({t: 'hook_ok', msg: '调用者hook已安装 @ ' + callerEntry});
}

// ==========================================
// Step 3: 同时保留 AcquireSMD hook (只记数)
// ==========================================
var acquireAddr = base.add(0x01EEC130);
var acquireCount = 0;
Interceptor.attach(acquireAddr, {
    onEnter: function(args) {
        acquireCount++;
    }
});

// ==========================================
// Step 4: SSKF 监控
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var sskfCount = 0;
Interceptor.attach(ReadFile, {
    onEnter: function(args) { this.buf = args[1]; this.brPtr = args[3]; },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 4) return;
            var b0 = this.buf.readU8();
            var b1 = this.buf.add(1).readU8();
            var b2 = this.buf.add(2).readU8();
            var b3 = this.buf.add(3).readU8();
            if (b0 === 0x53 && b1 === 0x53 && b2 === 0x4B && b3 === 0x46) {
                sskfCount++;
                send({t: 'sskf', n: sskfCount});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '调用者诊断就绪. 进房间触发.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({callerCalls: callerCallCount, acquireCalls: acquireCount, sskf: sskfCount});
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
    log(f'=== AcquireSMD调用者诊断 === PID:{pid} ===')
    log(f'目标: 0x1EEBAE3 附近的函数入口')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'scan_start':
                log(f'  扫描起始: 返回地址 {p["retAddr"]}')
            elif t == 'candidate':
                boundary = '有边界' if p['isBoundary'] else '无边界'
                log(f'  [候选] RVA={p["rva"]} ({p["dist"]}) [{boundary}] prologue#{p["prologueIdx"]}')
                log(f'    bytes: {p["preview"]}')
            elif t == 'entry_found':
                log(f'  [入口] {p["addr"]} RVA={p["rva"]}')
            elif t == 'hook_ok':
                log(f'  {p["msg"]}')
            elif t == 'caller_call':
                idx = p['idx']
                log(f'  [CALLER #{idx}] ======')
                log(f'    regs: eax={p["regs"]["eax"]} ecx={p["regs"]["ecx"]} edx={p["regs"]["edx"]}')
                log(f'          esi={p["regs"]["esi"]} edi={p["regs"]["edi"]}')
                log(f'    stack: {" ".join(p["stackArgs"])}')
                if p['thisStrings']:
                    log(f'    this对象字符串:')
                    for s in p['thisStrings']:
                        log(f'      +{s["off"]}: "{s["str"]}"')
                if p['stackStrings']:
                    log(f'    栈参数字符串:')
                    for s in p['stackStrings']:
                        if 'sstring' in s:
                            log(f'      arg{s["argIdx"]} [{s["ptr"]}] SString(len={s["len"]}): "{s["sstring"]}"')
                        else:
                            log(f'      arg{s["argIdx"]} [{s["ptr"]}]: "{s["str"]}"')
                if p['regStrings']:
                    log(f'    寄存器字符串:')
                    for s in p['regStrings']:
                        if 'sstring' in s:
                            log(f'      {s["reg"]} SString(len={s["len"]}): "{s["sstring"]}"')
                        else:
                            log(f'      {s["reg"]}: "{s["str"]}"')
                if not p['thisStrings'] and not p['stackStrings'] and not p['regStrings']:
                    log(f'    (无字符串发现)')
            elif t == 'caller_bt':
                log(f'    backtrace #{p["idx"]}: {" → ".join(p["frames"])}')
            elif t == 'sskf':
                pass  # 太多, 不逐个打印
            elif t == 'warn':
                log(f'  [警告] {p["msg"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
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
            if cmd in ('quit','q','exit'):
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

"""
hook_alloc_expand.py — v6: NOP+挂起ApolloCT检测线程 + SSKF替换
策略:
  0. NOP掉ApolloCT的INT3指令 + 挂起检测线程 + 异常兜底
  1. 第一次512B ReadFile: 替换header
  2. Hook malloc onEnter: 扩大分配到270KB
  3. Hook MSVCR100 fread onLeave: Memory.copy目标数据

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'alloc_expand_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

send({t: 'step', msg: 'JS开始执行'});

// ==========================================
// 0. 瘫痪ApolloCT — NOP + 挂起 + 异常兜底
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var _OpenThread = new NativeFunction(kernel32.getExportByName('OpenThread'), 'pointer', ['int', 'int', 'int']);
var _SuspendThread = new NativeFunction(kernel32.getExportByName('SuspendThread'), 'int', ['pointer']);
var _CloseHandle = new NativeFunction(kernel32.getExportByName('CloseHandle'), 'int', ['pointer']);

var THREAD_SUSPEND_RESUME = 0x0002;

var apolloBase = null;
var apolloSize = 0;
var apolloInt3Offsets = [0x00557e4d, 0x004f3e32];

try {
    var apolloMod = Process.getModuleByName('ApolloCT.Dll');
    apolloBase = apolloMod.base;
    apolloSize = apolloMod.size;
    send({t: 'step', msg: 'ApolloCT.Dll base=' + apolloBase + ' size=' + apolloSize});

    // --- 步骤A: NOP掉已知INT 3指令 ---
    for (var ni = 0; ni < apolloInt3Offsets.length; ni++) {
        var addr = apolloBase.add(apolloInt3Offsets[ni]);
        Memory.protect(addr, 2, 'rwx');
        var origByte = addr.readU8();
        if (origByte === 0xCC) {
            addr.writeU8(0x90); // 单字节INT3 → NOP
            send({t: 'nop', addr: 'ApolloCT+0x' + apolloInt3Offsets[ni].toString(16),
                  origByte: '0xCC', patched: '0x90 (1byte)'});
        } else {
            addr.writeByteArray([0x90, 0x90]); // 双字节保险
            send({t: 'nop', addr: 'ApolloCT+0x' + apolloInt3Offsets[ni].toString(16),
                  origByte: '0x' + origByte.toString(16), patched: '0x9090 (2byte)'});
        }
    }
    send({t: 'step', msg: 'INT3 NOP完成'});

    // --- 步骤B: 挂起当前EIP在ApolloCT范围内的线程 ---
    var threads = Process.enumerateThreads();
    var suspended = 0;
    for (var ti = 0; ti < threads.length; ti++) {
        try {
            var tid = threads[ti].id;
            var ctx = Thread.getContext(tid);
            var pc = ctx.pc;
            var offset = pc.sub(apolloBase).toInt32();
            if (offset >= 0 && offset < apolloSize) {
                var hThread = _OpenThread(THREAD_SUSPEND_RESUME, 0, tid);
                if (!hThread.isNull()) {
                    _SuspendThread(hThread);
                    _CloseHandle(hThread);
                    suspended++;
                    send({t: 'thread_suspended', tid: tid,
                          pc: 'ApolloCT+0x' + offset.toString(16)});
                }
            }
        } catch(e) {
            // 跳过无法读取context的线程(如系统线程)
        }
    }
    send({t: 'step', msg: '挂起了 ' + suspended + ' 个ApolloCT线程'});

} catch(e) {
    send({t: 'step', msg: 'ApolloCT.Dll未找到, 跳过: ' + e});
}

// --- 步骤C: 简单异常兜底 — 任何来自ApolloCT的breakpoint都吞掉 ---
Process.setExceptionHandler(function(details) {
    try {
        if (details.type !== 'breakpoint') return false;
        var mod = Process.findModuleByAddress(details.address);
        if (mod && mod.name === 'ApolloCT.Dll') {
            send({t: 'exception_suppressed', addr: details.address.toString(),
                  tid: details.threadId});
            return true;
        }
    } catch(e) {}
    return false;
});

send({t: 'step', msg: 'ApolloCT异常兜底已注册'});

// ==========================================
// 1. CRT函数 (用msvcrt加载目标文件)
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

    var magic = readName(targetBuf, 0, 4);
    var name = readName(targetBuf, 8, 64);
    send({t: 'loaded', size: totalRead, expected: TARGET_SIZE,
          magic: magic, name: name, addr: targetBuf.toString()});

    if (totalRead !== TARGET_SIZE) {
        send({t: 'error', msg: '文件不完整! 读取' + totalRead + '/期望' + TARGET_SIZE});
    }
    if (magic !== 'SSKF') {
        send({t: 'error', msg: '非SSKF文件! magic=' + magic});
    }
}

send({t: 'step', msg: '目标文件加载完成'});

// ==========================================
// 3. 状态机
// ==========================================
var STATE_IDLE = 0;
var STATE_FIRST_READ = 1;       // 第一次512B已替换header, 等待malloc
var STATE_MALLOC_EXPANDED = 2;  // malloc已扩大, 等待fread

var state = STATE_IDLE;
var trackedHandle = 0;
var expandedBuf = null;
var expandedSize = 0;
var totalSSKF = 0;
var patchCount = 0;

// ==========================================
// 4. Hook malloc — 同时hook MSVCR100和msvcrt
// ==========================================
var allocHooks = [];

try {
    var msvcr100Mod = Process.getModuleByName('MSVCR100.dll');
    var msvcr100Malloc = msvcr100Mod.getExportByName('malloc');
    allocHooks.push({name: 'MSVCR100 malloc', addr: msvcr100Malloc});
    send({t: 'step', msg: 'MSVCR100 malloc=' + msvcr100Malloc});
} catch(e) {
    send({t: 'step', msg: 'MSVCR100未找到: ' + e});
}

try {
    var msvcrtMalloc = crtMod.getExportByName('malloc');
    allocHooks.push({name: 'msvcrt malloc', addr: msvcrtMalloc});
    send({t: 'step', msg: 'msvcrt malloc=' + msvcrtMalloc});
} catch(e) {}

try {
    var msvcr100New = Process.getModuleByName('MSVCR100.dll').getExportByName('??2@YAPAXI@Z');
    allocHooks.push({name: 'MSVCR100 new', addr: msvcr100New});
    send({t: 'step', msg: 'MSVCR100 operator new=' + msvcr100New});
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
                    send({t: 'malloc_result', source: hookInfo.name,
                          addr: expandedBuf.toString(), size: expandedSize});
                }
            }
        });
    })(allocHooks[hi]);
}

// ==========================================
// 5. Hook MSVCR100 fread — 参数明确, 无wrapper歧义
//    fread(void *ptr, size_t size, size_t count, FILE *stream)
//    args[0]=ptr, args[1]=size, args[2]=count, args[3]=stream
// ==========================================
var msvcr100Fread = Process.getModuleByName('MSVCR100.dll').getExportByName('fread');
send({t: 'step', msg: 'MSVCR100 fread=' + msvcr100Fread});

Interceptor.attach(msvcr100Fread, {
    onEnter: function(args) {
        this.bufPtr = args[0];
        this.elemSize = args[1].toInt32();
        this.elemCount = args[2].toInt32();
        this.totalReq = this.elemSize * this.elemCount;

        // 只在malloc已扩大时, 且buffer匹配expandedBuf时才处理
        this.shouldPatch = false;
        if (state === STATE_MALLOC_EXPANDED && expandedBuf !== null) {
            if (this.bufPtr.equals(expandedBuf)) {
                this.shouldPatch = true;
                send({t: 'fread_target', buf: this.bufPtr.toString(),
                      totalReq: this.totalReq,
                      elemSize: this.elemSize, elemCount: this.elemCount});
            }
        }
    },
    onLeave: function(retval) {
        if (!this.shouldPatch) return;

        var origRet = retval.toInt32();

        // fread返回项目数, elemSize=1时项目数=字节数
        if (this.elemSize !== 1) {
            send({t: 'error', msg: 'elemSize不为1! size=' + this.elemSize});
            return;
        }

        // fread已完成, bufPtr中的数据是最终状态
        Memory.copy(this.bufPtr, targetBuf, TARGET_SIZE);
        retval.replace(TARGET_SIZE);

        patchCount++;
        state = STATE_IDLE;
        trackedHandle = 0;
        expandedBuf = null;
        expandedSize = 0;

        send({t: 'fread_done', origRet: origRet, newRet: TARGET_SIZE,
              buf: this.bufPtr.toString(),
              name: readName(this.bufPtr, 8, 64)});
    }
});

// ==========================================
// 6. Hook ReadFile — 仅用于header替换和日志
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

            if (totalSSKF <= 15) {
                send({t: 'sskf', n: totalSSKF, name: name,
                      bytesRead: bytesRead, reqSize: this.sizeReq,
                      buf: this.buf.toString()});
            }

            // === 第一次512B: 替换header ===
            if (name.indexOf('50125461_FN') >= 0 && bytesRead === 512 && state === STATE_IDLE) {
                Memory.copy(this.buf, targetBuf, 512);
                state = STATE_FIRST_READ;
                trackedHandle = this.handle;
                send({t: 'header_patched', name: readName(this.buf, 8, 64)});
                return;
            }

            // 第二次读取只做日志
            if (state === STATE_MALLOC_EXPANDED && this.handle === trackedHandle && bytesRead > 512) {
                send({t: 'second_readfile', bytesRead: bytesRead, reqSize: this.sizeReq,
                      buf: this.buf.toString()});
            }
        } catch(e) {
            send({t: 'error', msg: 'ReadFile hook: ' + e});
        }
    }
});

send({t: 'ready', msg: 'v6就绪: NOP+挂起ApolloCT + SSKF替换'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            totalSSKF: totalSSKF, patches: patchCount, state: state,
            expandedBuf: expandedBuf ? expandedBuf.toString() : 'null',
            states: ['idle', 'firstRead', 'mallocExpanded']
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
    log(f'=== v6: NOP+挂起ApolloCT === PID:{pid} ===')
    log(f'策略: NOP INT3 + 挂起线程 + SSKF替换')
    log(f'目标: i50125461_FN.smd(美丽梦想发型) → i50125711_FN.smd(紫色超赛发型)')
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
                log(f'  目标加载: {p["size"]}B/{p["expected"]}B magic={p["magic"]} name={p["name"]}')
            elif t == 'sskf':
                if p['n'] <= 20:
                    log(f'  [SSKF #{p["n"]}] "{p["name"]}" read={p["bytesRead"]}B req={p["reqSize"]}B buf={p["buf"]}')
            elif t == 'header_patched':
                log(f'  [Header替换] → {p["name"]}')
            elif t == 'malloc_expand':
                log(f'  [malloc扩大] {p["origReq"]}B → {p["newSize"]}B (via {p["source"]})')
            elif t == 'malloc_result':
                log(f'  [malloc返回] buf={p["addr"]} size={p["size"]}')
            elif t == 'fread_target':
                log(f'  [fread目标] buf={p["buf"]} req={p["totalReq"]}B (size={p["elemSize"]}*count={p["elemCount"]})')
            elif t == 'fread_done':
                log(f'  [fread替换] 返回{p["origRet"]}B→{p["newRet"]}B buf={p["buf"]} name="{p["name"]}"')
            elif t == 'second_readfile':
                log(f'  [ReadFile第二次] read={p["bytesRead"]}B req={p["reqSize"]}B buf={p["buf"]}')
            elif t == 'nop':
                log(f'  [NOP] {p["addr"]} {p["origByte"]}→{p["patched"]}')
            elif t == 'thread_suspended':
                log(f'  [线程挂起] tid={p["tid"]} pc={p["pc"]}')
            elif t == 'exception_suppressed':
                log(f'  [异常抑制] addr={p["addr"]} tid={p["tid"]}')
            elif t == 'apollo_killed':
                log(f'  [ApolloCT击杀] tid={p["tid"]} rva={p["rva"]}')
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

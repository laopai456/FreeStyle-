"""
hook_deep_crash.py — 崩溃捕获 + 深层hook
目标: 抓住替换后的崩溃地址, 为后续深层hook铺路
策略:
  1. AcquireSMD调用者替换 (已验证可用)
  2. Process.setExceptionHandler 捕获崩溃地址/寄存器
  3. Hook AcquireSMD返回后的处理链 (0x1EEBA30的后续代码)
  4. SSKF数据dump (比较原始vs替换的mesh结构差异)

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'deep_crash_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var SRC_CODE = '50125461';  // 美丽梦想发型 (pak767)
var DST_CODE = '50125711';  // 紫色超赛发型 (pak768)
var SRC_PAK = 'res767';
var DST_PAK = 'res768';

var srcCodeBytes = [];
var dstCodeBytes = [];
for (var i = 0; i < SRC_CODE.length; i++) {
    srcCodeBytes.push(SRC_CODE.charCodeAt(i));
    dstCodeBytes.push(DST_CODE.charCodeAt(i));
}
var srcPakBytes = [];
var dstPakBytes = [];
for (var i = 0; i < SRC_PAK.length; i++) {
    srcPakBytes.push(SRC_PAK.charCodeAt(i));
    dstPakBytes.push(DST_PAK.charCodeAt(i));
}

var totalCalls = 0;
var patchCount = 0;
var patchedFilename = '';

// ==========================================
// 1. 异常处理器 — 抓崩溃点
// ==========================================
Process.setExceptionHandler(function(details) {
    var crashAddr = details.address;
    var rva = crashAddr.sub(base);
    var ctx = details.context;

    send({
        t: 'crash',
        type: details.type,
        addr: crashAddr.toString(),
        rva: '0x' + rva.toString(16),
        inModule: (rva.toInt32() >= 0 && rva.toInt32() < 0x3000000),
        eax: ctx.eax.toString(),
        ecx: ctx.ecx.toString(),
        edx: ctx.edx.toString(),
        esi: ctx.esi.toString(),
        edi: ctx.edi.toString(),
        esp: ctx.esp.toString(),
        ebp: ctx.ebp.toString(),
        eip: ctx.pc.toString()
    });

    // 读崩溃地址附近的代码
    try {
        var codeDump = '';
        for (var i = 0; i < 16; i++) {
            codeDump += ('0' + crashAddr.add(i).readU8().toString(16)).slice(-2) + ' ';
        }
        send({t: 'crash_code', bytes: codeDump.trim()});
    } catch(e) {}

    // 读ESP栈
    try {
        var stackDump = '';
        for (var i = 0; i < 16; i++) {
            stackDump += ('00000000' + ctx.esp.add(i * 4).readU32().toString(16)).slice(-8) + ' ';
        }
        send({t: 'crash_stack', dump: stackDump.trim()});

        // 栈回溯
        var bt = [];
        for (var i = 0; i < 20; i++) {
            try {
                var retAddr = ctx.esp.add(i * 4).readU32();
                var rva2 = retAddr - base.toInt32();
                if (rva2 > 0 && rva2 < 0x3000000) {
                    bt.push('0x' + rva2.toString(16));
                }
            } catch(e) { break; }
        }
        if (bt.length > 0) {
            send({t: 'crash_bt', frames: bt});
        }
    } catch(e) {}

    // 读ECX指向的对象 (可能是this指针崩溃)
    try {
        var ecxVal = ctx.ecx;
        var objDump = '';
        for (var i = 0; i < 8; i++) {
            objDump += ('00000000' + ecxVal.add(i * 4).readU32().toString(16)).slice(-8) + ' ';
        }
        send({t: 'crash_ecx_obj', dump: objDump.trim()});
    } catch(e) {}

    return false;  // 不处理异常, 让游戏崩溃 (我们只需要地址)
});

// ==========================================
// 2. AcquireSMD调用者替换 (已验证)
// ==========================================
var callerEntry = base.add(0x01EEBA30);

Interceptor.attach(callerEntry, {
    onEnter: function(args) {
        totalCalls++;
        var idx = totalCalls;
        var ecx = this.context.ecx;

        // 读字符串
        var strPtr = null;
        var filename = '';
        var ptrVal = 0;

        try {
            ptrVal = ecx.add(0x10).readU32();
            if (ptrVal >= 0x10000) {
                strPtr = ptr(ptrVal);
                filename = strPtr.readAnsiString(80);
            }
        } catch(e) {}

        if (!filename || filename.length < 5) return;

        var hasCode = filename.indexOf(SRC_CODE) >= 0;
        if (!hasCode) return;

        send({t: 'target', idx: idx, file: filename});

        // 替换
        var strLen = filename.length;
        var replaceCount = 0;

        try {
            for (var pos = 0; pos <= strLen - srcCodeBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcCodeBytes.length; j++) {
                    if (strPtr.add(pos + j).readU8() !== srcCodeBytes[j]) { match = false; break; }
                }
                if (match) {
                    for (var j = 0; j < dstCodeBytes.length; j++) strPtr.add(pos + j).writeU8(dstCodeBytes[j]);
                    replaceCount++;
                }
            }
            for (var pos = 0; pos <= strLen - srcPakBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcPakBytes.length; j++) {
                    if (strPtr.add(pos + j).readU8() !== srcPakBytes[j]) { match = false; break; }
                }
                if (match) {
                    for (var j = 0; j < dstPakBytes.length; j++) strPtr.add(pos + j).writeU8(dstPakBytes[j]);
                    replaceCount++;
                }
            }
        } catch(e) {
            send({t: 'error', msg: '写入失败: ' + e});
            return;
        }

        if (replaceCount > 0) {
            patchCount++;
            patchedFilename = filename;
            var newFile = '';
            try { newFile = strPtr.readAnsiString(80); } catch(e) {}
            send({t: 'patched', idx: idx, from: filename, to: newFile, count: replaceCount});
        }
    }
});

// ==========================================
// 3. Hook AcquireSMD 本体 — 追踪返回后的处理
// ==========================================
var acquireSMD = base.add(0x01EEC130);
var acquireResults = [];

Interceptor.attach(acquireSMD, {
    onEnter: function(args) {
        this.callIdx = totalCalls;
    },
    onLeave: function(retval) {
        // 记录返回值和状态
        send({
            t: 'acquire_ret',
            idx: this.callIdx,
            ret: retval.toString(),
            eax: this.context.eax.toString()
        });
    }
});

// ==========================================
// 4. Hook AcquireSMD返回地址 — 看后续处理
//    返回地址 0x1EEBAE3, 调用者在0x1EEBA30
//    调用指令在0x1EEBAE3-5 = 0x1EEBADE (call)
//    返回后0x1EEBAE3处的代码就是后续处理
// ==========================================
// 不直接hook 0x1EEBAE3 (那是下一条指令, 不是函数入口)
// 改为: 在AcquireSMD返回时记录ebp, 追踪调用者的栈帧

// ==========================================
// 5. SSKF 数据dump — 捕获替换文件的SSKF头部
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var sskfCount = 0;
var dumpNextSSKF = false;

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3];
        this.filename = '';
        // 尝试获取文件名 (args[0]是HANDLE, 不能直接读文件名)
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 4) return;
            var magic = this.buf.readU32();
            if (magic !== 0x464B5353) return;  // 不是SSKF

            sskfCount++;
            var flag = this.buf.add(0x2C).readU8();
            var meshSize = this.buf.add(0x04).readU32();

            // 如果刚做了替换, dump接下来的2个SSKF (header+mesh)
            if (patchCount > 0 && sskfCount <= 42 && !dumpNextSSKF) {
                dumpNextSSKF = true;
            }

            send({t: 'sskf', n: sskfCount, size: n, meshSize: meshSize, flag: '0x' + flag.toString(16)});

            // dump SSKF头部 (前64字节)
            if (dumpNextSSKF && sskfCount <= 42) {
                var headerSize = Math.min(n, 64);
                var headerHex = '';
                for (var i = 0; i < headerSize; i++) {
                    headerHex += ('0' + this.buf.add(i).readU8().toString(16)).slice(-2);
                    if ((i + 1) % 16 === 0) headerHex += '\n';
                    else if ((i + 1) % 4 === 0) headerHex += ' ';
                }
                send({t: 'sskf_dump', n: sskfCount, size: n, hex: headerHex});

                // 只dump前4个SSKF的详细数据
                if (sskfCount >= 42) dumpNextSSKF = false;
            }
        } catch(e) {}
    }
});

// ==========================================
// 6. Hook CreateFileA/W — 追踪文件打开
//    看游戏是否试图打开不存在的文件
// ==========================================
var CreateFileA = kernel32.getExportByName('CreateFileA');
var CreateFileW = kernel32.getExportByName('CreateFileW');
var fileOpenCount = 0;

Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        try {
            var path = args[0].readAnsiString(128);
            if (path && path.indexOf('50125711') >= 0) {
                fileOpenCount++;
                var rva = this.returnAddress.sub(base);
                send({t: 'file_open', n: fileOpenCount, path: path, rva: '0x' + rva.toString(16), type: 'A'});
            }
        } catch(e) {}
    }
});

Interceptor.attach(CreateFileW, {
    onEnter: function(args) {
        try {
            var path = args[0].readUtf16String(128);
            if (path && path.indexOf('50125711') >= 0) {
                fileOpenCount++;
                var rva = this.returnAddress.sub(base);
                send({t: 'file_open', n: fileOpenCount, path: path, rva: '0x' + rva.toString(16), type: 'W'});
            }
        } catch(e) {}
    }
});

// ==========================================
// 7. Hook 几个可能的崩溃点 — 渲染/动画相关
// ==========================================

// DynamicCreate1 0x01E99730 — 创建actor
var dynCreate1 = base.add(0x01E99730);
Interceptor.attach(dynCreate1, {
    onEnter: function(args) { send({t: 'dyn_create', eax: this.context.eax.toString()}); },
    onLeave: function(retval) { send({t: 'dyn_create_ret', ret: retval.toString()}); }
});

send({t: 'ready', msg: '深层崩溃诊断就绪. 进房间.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            total: totalCalls,
            patches: patchCount,
            sskf: sskfCount,
            fileOpens: fileOpenCount
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
    log(f'=== 深层崩溃诊断 === PID:{pid} ===')
    log(f'50125461(美丽梦想发型 pak767) → 50125711(紫色超赛发型 pak768)')
    log(f'策略: 替换+崩溃捕获+SSKF dump+文件追踪+DynamicCreate监控')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'target':
                log(f'  [目标 #{p["idx"]}] "{p["file"]}"')
            elif t == 'patched':
                log(f'  [补丁 #{p["idx"]}] "{p["from"]}" → "{p["to"]}" ({p["count"]}处)')
            elif t == 'acquire_ret':
                log(f'  [AcquireSMD返回 #{p["idx"]}] ret={p["ret"]} eax={p["eax"]}')
            elif t == 'sskf':
                log(f'  [SSKF #{p["n"]}] size={p["size"]} mesh={p["meshSize"]} flag={p["flag"]}')
            elif t == 'sskf_dump':
                log(f'  [SSKF dump #{p["n"]}] size={p["size"]}:')
                for line in p['hex'].strip().split('\n'):
                    log(f'    {line}')
            elif t == 'file_open':
                log(f'  [文件打开 #{p["n"]}] "{p["path"]}" (rva={p["rva"]}, {p["type"]})')
            elif t == 'dyn_create':
                log(f'  [DynamicCreate] eax={p["eax"]}')
            elif t == 'dyn_create_ret':
                log(f'  [DynamicCreate返回] ret={p["ret"]}')
            elif t == 'crash':
                in_mod = 'YES' if p.get('inModule') else 'NO'
                log(f'  !!! 崩溃 !!!')
                log(f'    类型: {p["type"]}')
                log(f'    地址: {p["addr"]} RVA={p["rva"]} (模块内: {in_mod})')
                log(f'    EAX={p["eax"]} ECX={p["ecx"]} EDX={p["edx"]}')
                log(f'    ESI={p["esi"]} EDI={p["edi"]}')
                log(f'    ESP={p["esp"]} EBP={p["ebp"]} EIP={p["eip"]}')
            elif t == 'crash_code':
                log(f'    崩溃指令: {p["bytes"]}')
            elif t == 'crash_stack':
                log(f'    栈: {p["dump"]}')
            elif t == 'crash_bt':
                log(f'    栈回溯: {" → ".join(p["frames"])}')
            elif t == 'crash_ecx_obj':
                log(f'    ECX对象: {p["dump"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。崩溃时自动捕获地址。')
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

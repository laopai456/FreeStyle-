"""
hook_diag_crash.py — 全面监控+崩溃捕获
监控: sprintf/LoadItemFile/AcquireSMD/CreateFileA
崩溃: Frida异常处理器捕获崩溃地址和寄存器

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_crash_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767)
DST_IC = 50125711  # 紫色超赛发型 (pak768) — 改为50122451测鬼魅

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

function hexAddr(p) { return '0x' + p.toString(16); }

send({t: 'step', msg: 'JS开始执行'});
var base = ptr('0x400000');
var patchCount = 0;
var loadCycle = 0;

// ==========================================
// 0. 异常处理器 — 捕获崩溃
// ==========================================
Process.setExceptionHandler(function(details) {
    send({t: 'CRASH',
          type: details.type,
          addr: hexAddr(details.address),
          ctx_eip: hexAddr(details.context.pc),
          ctx_eax: hexAddr(details.context.eax),
          ctx_ebx: hexAddr(details.context.ebx),
          ctx_ecx: hexAddr(details.context.ecx),
          ctx_edx: hexAddr(details.context.edx),
          ctx_esp: hexAddr(details.context.esp),
          ctx_ebp: hexAddr(details.context.ebp),
          mem: details.memory || {},
          patches: patchCount,
          loadCycle: loadCycle
    });
    // 尝试读取ESP附近栈数据
    try {
        var esp = details.context.esp;
        var stack = [];
        for (var i = 0; i < 16; i++) {
            stack.push(hexAddr(esp.add(i*4).readU32()));
        }
        send({t: 'CRASH_STACK', vals: stack});
    } catch(e) {}
    // 读取EIP附近代码
    try {
        var pc = details.context.pc;
        var code = new Uint8Array(pc.sub(8).readByteArray(24));
        var hex = '';
        for (var i = 0; i < 24; i++) hex += ('0'+code[i].toString(16)).slice(-2) + ' ';
        send({t: 'CRASH_CODE', offset: hexAddr(pc.sub(base)), hex: hex});
    } catch(e) {}
    return false;
});
send({t: 'step', msg: '异常处理器已设置'});

// ==========================================
// 1. sprintf + [ebp-0xD8] 替换
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
                loadCycle++;
                args[2] = ptr(DST_IC);
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);
                patchCount++;
                send({t: 'patched', n: patchCount, cycle: loadCycle});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook已设置'});

// ==========================================
// 2. LoadItemFile入口 — 跟踪每次加载
// ==========================================
var lifAddr = base.add(0x1ACE1C0);
var lifCount = 0;

Interceptor.attach(lifAddr, {
    onEnter: function(args) {
        var ic = args[0].toInt32();
        lifCount++;
        // 双重保险: LoadItemFile也做替换，覆盖sprintf之外的代码路径
        if (ic === SRC_IC) {
            args[0] = ptr(DST_IC);
            // 原地修改filename buffer中的ItemCode数字，不改指针
            // "customize\item\iXXXXXXXX.xml" — 数字从offset 16开始，8位
            var dstStr = DST_IC.toString();
            for (var j = 0; j < dstStr.length; j++) {
                args[1].add(16 + j).writeU8(dstStr.charCodeAt(j));
            }
            patchCount++;
            send({t: 'lif_patched', n: lifCount, origIc: SRC_IC, newIc: DST_IC, patches: patchCount});
        }
        var fname = readAscii(args[1], 80);
        send({t: 'lif', n: lifCount, ic: args[0].toInt32(), fname: fname});
    }
});
send({t: 'step', msg: 'LoadItemFile hook已设置(含替换)'});

// ==========================================
// 3. AcquireSMD — 跟踪SMD加载
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;

Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            // 所有res768/res742/50125相关 + 前20个
            if (path.indexOf('768') >= 0 || path.indexOf('742') >= 0 ||
                path.indexOf('50125') >= 0 || acquireCount <= 20) {
                send({t: 'smd', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'AcquireSMD hook已设置'});

// ==========================================
// 4. CreateFileA — 跟踪文件打开
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var CreateFileA = kernel32.getExportByName('CreateFileA');
var cfCount = 0;

Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 256);
            if (path.indexOf('50125') >= 0 || path.indexOf('50122') >= 0 ||
                path.indexOf('item7') >= 0 || path.indexOf('.bml') >= 0 ||
                path.indexOf('res7') >= 0) {
                cfCount++;
                send({t: 'file', n: cfCount, path: path});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA hook已设置'});

// BuildBoneIndex / VirtualAlloc / GetLastError — 暂禁用，排查立即崩溃
var boneCallCount = 0;
var boneFails = 0;
var allocCount = 0;
var errCount = 0;

send({t: 'ready', msg: '诊断就绪 — 异常/sprintf/LoadItemFile/SMD/CreateFile (骨骼/分配/错误已禁用)'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            patches: patchCount,
            loadCycle: loadCycle,
            lifs: lifCount,
            smds: acquireCount,
            files: cfCount,
            boneCalls: boneCallCount,
            boneFails: boneFails
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
    log(f'=== 崩溃诊断 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}')
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
                log(f'  [替换!] #{p["n"]} cycle={p["cycle"]}')
            elif t == 'lif':
                log(f'  [LoadItemFile] #{p["n"]} ic={p["ic"]} "{p["fname"]}"')
            elif t == 'smd':
                log(f'  [AcquireSMD] #{p["n"]} "{p["path"]}"')
            elif t == 'file':
                log(f'  [CreateFile] #{p["n"]} "{p["path"]}"')
            elif t == 'bone_fail':
                log(f'  [骨骼失败!] #{p["n"]} (总调用={p["total"]})')
            elif t == 'big_alloc':
                log(f'  [大块分配] #{p["n"]} size={p["size"]} bytes')
            elif t == 'win_error':
                log(f'  [Win错误] code={p["code"]} #{p["n"]}')
            elif t == 'CRASH':
                log(f'  ★★★ 崩溃! ★★★')
                log(f'    type={p["type"]} addr={p["addr"]}')
                log(f'    EIP={p["ctx_eip"]} EAX={p["ctx_eax"]} EBX={p["ctx_ebx"]}')
                log(f'    ECX={p["ctx_ecx"]} EDX={p["ctx_edx"]}')
                log(f'    ESP={p["ctx_esp"]} EBP={p["ctx_ebp"]}')
                log(f'    patches={p["patches"]} cycle={p["loadCycle"]}')
                if p.get('mem') and p['mem'].get('address'):
                    log(f'    mem_access: addr={p["mem"]["address"]} op={p["mem"].get("operation","?")}')
            elif t == 'CRASH_STACK':
                log(f'    栈: {p["vals"]}')
            elif t == 'CRASH_CODE':
                log(f'    代码@{p["offset"]}: {p["hex"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间 → 穿戴发型 → 进练习场。')
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

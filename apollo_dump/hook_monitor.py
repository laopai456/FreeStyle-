"""
hook_monitor.py — 动态发型不显示诊断
全面监控 sprintf→LoadItemFile→CreateFileA→AcquireSMD 链路
找出BML在哪一步断了

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'monitor_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

function hexAddr(p) { return '0x' + p.toString(16); }

send({t: 'step', msg: 'JS开始执行'});
var base = ptr('0x400000');
var patchCount = 0;
var startTime = Date.now();
function elapsed() { return ((Date.now() - startTime) / 1000).toFixed(1) + 's'; }

// ==========================================
// 1. 异常处理器
// ==========================================
Process.setExceptionHandler(function(details) {
    send({t: 'CRASH', type: details.type, addr: hexAddr(details.address),
          eip: hexAddr(details.context.pc), patches: patchCount});
    return false;
});

// ==========================================
// 2. sprintf hook — 替换 + 详细日志
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var sprintfCount = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0) return;

            var itemCode = args[2].toInt32();
            sprintfCount++;
            var isTarget = (itemCode === SRC_IC);

            // 记录所有item sprintf调用
            if (sprintfCount <= 30 || isTarget) {
                send({t: 'sprintf', n: sprintfCount, fmt: fmt, ic: itemCode,
                      target: isTarget, t: elapsed()});
            }

            if (isTarget) {
                // 替换sprintf参数
                args[2] = ptr(DST_IC);
                // 同时写[ebp-0xD8]
                var callerEbp = this.context.ebp;
                var ebpD8addr = callerEbp.sub(0xD8);
                var oldVal = ebpD8addr.readU32();
                ebpD8addr.writeU32(DST_IC);
                patchCount++;
                send({t: 'PATCH', n: patchCount, orig: SRC_IC, to: DST_IC,
                      ebp_old: oldVal, ebp_new: ebpD8addr.readU32(),
                      ebp_addr: hexAddr(ebpD8addr)});
            }
        } catch(e) {
            send({t: 'error', where: 'sprintf', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'sprintf hook OK'});

// ==========================================
// 3. LoadItemFile hook — 看ic参数和BML路径
// ==========================================
var lifAddr = base.add(0x1ACE1C0);
var lifCount = 0;
var lifPatched = 0;

Interceptor.attach(lifAddr, {
    onEnter: function(args) {
        try {
            var ic = args[0].toInt32();
            lifCount++;
            var fname = readAscii(args[1], 120);

            // 双重保险: LoadItemFile也替换
            if (ic === SRC_IC) {
                args[0] = ptr(DST_IC);
                lifPatched++;
                // 改filename buffer中的ItemCode
                var dstStr = DST_IC.toString();
                for (var j = 0; j < dstStr.length; j++) {
                    args[1].add(16 + j).writeU8(dstStr.charCodeAt(j));
                }
                send({t: 'LIF_PATCH', n: lifCount, origIc: SRC_IC, toIc: DST_IC, fname: fname});
            }

            // 所有LIF调用都记录
            if (lifCount <= 30 || ic === DST_IC) {
                // 读this对象的Group信息
                var thisPtr = this.context.ecx;
                var g7E4 = 0, g7E8 = 0;
                try { g7E4 = thisPtr.add(0x7E4).readU32(); } catch(e) {}
                try { g7E8 = thisPtr.add(0x7E8).readU32(); } catch(e) {}

                send({t: 'lif', n: lifCount, ic: ic, fname: fname,
                      group7E4: g7E4, group7E8: g7E8,
                      thisPtr: hexAddr(thisPtr)});
            }
        } catch(e) {
            send({t: 'error', where: 'lif', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'LoadItemFile hook OK'});

// ==========================================
// 4. CreateFileA — 看BML文件打开路径和结果
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var CreateFileA = kernel32.getExportByName('CreateFileA');
var GetLastError = kernel32.getExportByName('GetLastError');
var cfCount = 0;

Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        this._path = null;
        try {
            var path = readAscii(args[0], 300);
            // 过滤：只看BML/SMD/PAK/XML/item/res相关
            if (path.indexOf('.bml') >= 0 || path.indexOf('.pak') >= 0 ||
                path.indexOf('.xml') >= 0 || path.indexOf('.smd') >= 0 ||
                path.indexOf('item7') >= 0 || path.indexOf('res7') >= 0 ||
                path.indexOf('Resource') >= 0 || path.indexOf('customize') >= 0 ||
                path.indexOf('50125') >= 0 || path.indexOf('50122') >= 0) {
                this._path = path;
                cfCount++;
                this._n = cfCount;
            }
        } catch(e) {}
    },
    onLeave: function(retval) {
        if (!this._path) return;
        var handle = retval.toInt32();
        var fail = (handle === -1);  // INVALID_HANDLE_VALUE
        var errCode = 0;
        if (fail) {
            errCode = GetLastError().toInt32();
        }
        // 前50条 + 所有失败的都记录
        if (this._n <= 50 || fail || this._path.indexOf('50122') >= 0) {
            send({t: 'file', n: this._n, path: this._path,
                  ok: !fail, handle: handle, err: errCode});
        }
    }
});
send({t: 'step', msg: 'CreateFileA hook OK'});

// ==========================================
// 5. ReadFile — 看BML内容是否被读取
// ==========================================
var ReadFile = kernel32.getExportByName('ReadFile');
var rfCount = 0;
var targetBmlRead = false;

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.rbuf = args[1];
        this.brPtr = args[3];
        this._handle = args[0].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 4 || bytesRead > 1000000) return;

            // 读前几个字节判断内容
            var buf = this.rbuf;
            var header = '';
            for (var i = 0; i < Math.min(bytesRead, 16); i++) {
                var b = buf.add(i).readU8();
                header += ('0' + b.toString(16)).slice(-2) + ' ';
            }

            rfCount++;
            // 只看SSKF/BML/XML相关的，或大小可疑的
            var name = readAscii(buf, 64);
            if (name.indexOf('SSKF') >= 0 || name.indexOf('BML') >= 0 ||
                name.indexOf('50125') >= 0 || name.indexOf('50122') >= 0 ||
                (bytesRead < 10000 && rfCount <= 100)) {
                send({t: 'read', n: rfCount, bytes: bytesRead, hex: header.trim(),
                      name: name.substring(0, 40)});
            }

            // 特别关注目标BML是否被读取 (XOR 0xFF编码，所以原始是乱码)
            if (bytesRead > 100 && bytesRead < 10000 && !targetBmlRead) {
                // XOR后第一个字节应该不是0x00
                var firstByte = buf.readU8();
                // 检查是否可能是XOR编码的XML (0xFF ^ '<' = 0xBC)
                if (firstByte === 0xBC) {
                    targetBmlRead = true;
                    send({t: 'BML_DECODED', bytes: bytesRead, hex: header.trim()});
                }
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'ReadFile hook OK'});

// ==========================================
// 6. AcquireSMD — 看SMD加载路径
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;

Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 100);
            acquireCount++;
            // 所有与目标相关的 + 前20个
            if (path.indexOf('50122') >= 0 || path.indexOf('742') >= 0 ||
                path.indexOf('50125') >= 0 || acquireCount <= 20) {
                send({t: 'smd', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'AcquireSMD hook OK'});

// ==========================================
// 7. GetLastError监控 — 大量错误时报告
// ==========================================
var errSnapshot = {};
var errCheckInterval = setInterval(function() {
    try {
        var err = GetLastError().toInt32();
        if (err !== 0) {
            if (!errSnapshot[err]) errSnapshot[err] = 0;
            errSnapshot[err]++;
        }
    } catch(e) {}
}, 2000);

send({t: 'ready', msg: '全链路监控就绪: sprintf→LIF→CreateFile→ReadFile→AcquireSMD'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            patches: patchCount,
            sprintfs: sprintfCount,
            lifs: lifCount,
            lifPatches: lifPatched,
            files: cfCount,
            reads: rfCount,
            smds: acquireCount,
            bmlRead: targetBmlRead,
            elapsed: elapsed()
        });
    },
    errors: function() {
        return JSON.stringify(errSnapshot);
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
    log(f'=== 动态发型不显示诊断 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(鬼魅)')
    log(f'监控: sprintf → LoadItemFile → CreateFileA → ReadFile → AcquireSMD')
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
                tag = ' ★TARGET' if p.get('target') else ''
                log(f'  [sprintf] #{p["n"]} fmt="{p["fmt"]}" IC={p["ic"]}{tag}')
            elif t == 'PATCH':
                log(f'  [替换!] #{p["n"]} {p["orig"]}→{p["to"]} ebp@{p["ebp_addr"]} old={p["ebp_old"]} new={p["ebp_new"]}')
            elif t == 'lif':
                log(f'  [LoadItemFile] #{p["n"]} ic={p["ic"]} "{p["fname"]}" grp=({p["group7E4"]},{p["group7E8"]})')
            elif t == 'LIF_PATCH':
                log(f'  [LIF替换!] #{p["n"]} {p["origIc"]}→{p["toIc"]} "{p["fname"]}"')
            elif t == 'file':
                ok = 'OK' if p['ok'] else f'FAIL(err={p["err"]})'
                log(f'  [CreateFile] #{p["n"]} {ok} "{p["path"]}"')
            elif t == 'read':
                log(f'  [ReadFile] #{p["n"]} {p["bytes"]}B hex={p["hex"]} "{p["name"]}"')
            elif t == 'BML_DECODED':
                log(f'  [BML解码!] {p["bytes"]}B hex={p["hex"]}')
            elif t == 'smd':
                log(f'  [AcquireSMD] #{p["n"]} "{p["path"]}"')
            elif t == 'CRASH':
                log(f'  ★★★ 崩溃! {p["type"]} @ {p["addr"]} EIP={p["eip"]} patches={p["patches"]}')
            elif t == 'error':
                log(f'  [错误] {p.get("where","")} {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。重点看:')
    log('  1. [CreateFile] 是否打开i50122451.bml? 路径是什么?')
    log('  2. [LoadItemFile] ic是否=50122451?')
    log('  3. [BML解码] 是否看到XOR编码的BML被读取?')
    log('  4. [AcquireSMD] 是否加载res742的SMD?')
    log('')
    log('命令: status | errors | quit')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'errors':
                log(f'  GetLastError统计: {script.exports_sync.errors()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

"""
hook_acquire_diag.py — AcquireSMD 0x01EEC130 诊断
目标: 验证 Apollo 拆除后此函数是否被调用, 参数是什么

前置条件: sc stop ApolloProtect (停L0驱动)

Hook策略:
  Phase 1: 先hook ReadFile检测SSKF加载 (确认SMD确实在加载)
  Phase 2: hook 0x01EEC130 (AcquireSMD候选入口)
  Phase 3: 如果触发, dump参数/寄存器/栈, 做backtrace

所有输出同时写日志文件, 方便反复调试
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
// Phase 1: ReadFile SSKF 检测 (确认SMD在加载)
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var sskfCount = 0;

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3]; // bytesRead ptr
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 4 || n > 10000000) return;
            // SSKF magic: 53 53 4B 46 = "SSKF"
            var b0 = this.buf.readU8();
            var b1 = this.buf.add(1).readU8();
            var b2 = this.buf.add(2).readU8();
            var b3 = this.buf.add(3).readU8();
            if (b0 === 0x53 && b1 === 0x53 && b2 === 0x4B && b3 === 0x46) {
                sskfCount++;
                // 读取更多SSKF header信息
                var fileSize = this.buf.add(4).readU32();
                var flag = this.buf.add(0x2C).readU8();
                send({t: 'sskf', n: sskfCount, size: fileSize, flag: flag,
                      flagHex: '0x' + flag.toString(16)});
            }
        } catch(e) {}
    }
});

send({t: 'phase1', msg: 'ReadFile SSKF 监控已安装'});

// ==========================================
// Phase 2: Hook AcquireSMD 候选入口 0x01EEC130
// ==========================================
var acquireAddr = base.add(0x01EEC130);

// 先验证地址: 读前16字节
var acquireBytes = '';
try {
    var raw = new Uint8Array(acquireAddr.readByteArray(16));
    for (var i = 0; i < raw.length; i++) {
        acquireBytes += ('0' + raw[i].toString(16)).slice(-2) + ' ';
    }
} catch(e) {
    acquireBytes = 'READ FAILED: ' + e;
}

// 检查是否是有效函数入口 (常见prologue)
var isPrologue = acquireBytes.indexOf('55 8b ec') >= 0 ||
                 acquireBytes.indexOf('55 8b ec 83 ec') >= 0 ||
                 acquireBytes.indexOf('6a ff 68') >= 0 ||
                 acquireBytes.indexOf('cc cc cc') === 0;  // 未初始化

send({t: 'addr_check', addr: acquireAddr.toString(), bytes: acquireBytes,
      isPrologue: isPrologue});

// Hook入口
var acquireCallCount = 0;

try {
    Interceptor.attach(acquireAddr, {
        onEnter: function(args) {
            acquireCallCount++;
            var idx = acquireCallCount;

            // 读取所有寄存器
            var regs = {
                eax: this.context.eax.toString(),
                ecx: this.context.ecx.toString(),
                edx: this.context.edx.toString(),
                ebx: this.context.ebx.toString(),
                esp: this.context.esp.toString(),
                ebp: this.context.ebp.toString(),
                esi: this.context.esi.toString(),
                edi: this.context.edi.toString()
            };

            // 尝试读取args[0..3] (前4个栈参数)
            // thiscall: ecx=this, args从esp+4开始(跳过retaddr)
            var stackArgs = [];
            var esp = this.context.esp;
            for (var i = 0; i < 8; i++) {
                try {
                    var val = esp.add(4 + i * 4).readU32();
                    stackArgs.push('0x' + val.toString(16));
                } catch(e) {
                    stackArgs.push('err');
                }
            }

            // 尝试从ecx(this)读取对象信息
            var thisDump = '';
            try {
                var thisBytes = new Uint8Array(this.context.ecx.readByteArray(64));
                for (var i = 0; i < thisBytes.length; i++) {
                    thisDump += ('0' + thisBytes[i].toString(16)).slice(-2) + ' ';
                }
            } catch(e) { thisDump = 'read fail'; }

            // 检查每个栈参数是否像指针, 如果是则读指向的内容
            var ptrDumps = [];
            for (var i = 0; i < 4; i++) {
                try {
                    var ptrVal = esp.add(4 + i * 4).readU32();
                    if (ptrVal > 0x10000 && ptrVal < 0x80000000) {
                        // 看看指向的内容是否包含SString或文件名
                        var content = '';
                        try {
                            var bytes = new Uint8Array(ptr(ptrVal).readByteArray(32));
                            for (var j = 0; j < bytes.length; j++) {
                                var c = bytes[j];
                                if (c >= 0x20 && c < 0x7F) content += String.fromCharCode(c);
                                else content += '.';
                            }
                        } catch(e) { content = 'read fail'; }

                        var hexStr = '';
                        try {
                            var hbytes = new Uint8Array(ptr(ptrVal).readByteArray(16));
                            for (var j = 0; j < hbytes.length; j++) {
                                hexStr += ('0' + hbytes[j].toString(16)).slice(-2) + ' ';
                            }
                        } catch(e) {}

                        ptrDumps.push({
                            argIdx: i,
                            ptr: '0x' + ptrVal.toString(16),
                            text: content,
                            hex: hexStr
                        });
                    }
                } catch(e) {}
            }

            // 也检查ecx(this)指向的对象是否包含字符串
            var thisStrings = [];
            try {
                var ecxVal = this.context.ecx;
                for (var off = 0; off < 0x40; off += 4) {
                    try {
                        var ptrVal = ecxVal.add(off).readU32();
                        if (ptrVal > 0x10000 && ptrVal < 0x80000000) {
                            var s = '';
                            try {
                                for (var j = 0; j < 32; j++) {
                                    var c = ptr(ptrVal).add(j).readU8();
                                    if (c >= 0x20 && c < 0x7F) s += String.fromCharCode(c);
                                    else break;
                                }
                            } catch(e) {}
                            if (s.length > 3) {
                                thisStrings.push({off: '0x' + off.toString(16), str: s});
                            }
                        }
                    } catch(e) {}
                }
            } catch(e) {}

            send({
                t: 'acquire_call',
                idx: idx,
                regs: regs,
                stackArgs: stackArgs,
                thisDump: thisDump.substring(0, 100),
                ptrDumps: ptrDumps,
                thisStrings: thisStrings
            });

            // 第一次调用时做backtrace
            if (idx <= 3) {
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                var frames = [];
                for (var i = 0; i < bt.length && i < 15; i++) {
                    var rva = bt[i].sub(base);
                    frames.push('0x' + rva.toString(16));
                }
                send({t: 'backtrace', idx: idx, frames: frames});
            }
        }
    });
    send({t: 'phase2', msg: 'AcquireSMD hook @ ' + acquireAddr + ' 已安装'});
} catch(e) {
    send({t: 'hook_fail', msg: 'Hook失败: ' + e});
}

// ==========================================
// Phase 3: 也hook附近的0x01EED020 (push字符串的位置)
// 这是函数体内的字符串引用点, 如果phase2不触发可以试这个
// ==========================================
var stringRefAddr = base.add(0x01EED020);
var stringRefBytes = '';
try {
    var raw = new Uint8Array(stringRefAddr.readByteArray(16));
    for (var i = 0; i < raw.length; i++) {
        stringRefBytes += ('0' + raw[i].toString(16)).slice(-2) + ' ';
    }
} catch(e) { stringRefBytes = 'READ FAILED'; }

send({t: 'string_ref', addr: stringRefAddr.toString(), bytes: stringRefBytes});

// ==========================================
// 汇总
// ==========================================
send({t: 'ready', msg: '诊断已就绪. 触发角色加载(进房间/换频道).'});
send({t: 'info', msg: '监控: SSKF加载 + AcquireSMD入口 + backtrace'});
send({t: 'info', msg: '期望: 进房间后看到sskf事件, 然后acquire_call事件'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            sskfCount: sskfCount,
            acquireCalls: acquireCallCount
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
    log(f'=== AcquireSMD 诊断 === PID:{pid} ===')
    log(f'目标: 0x01EEC130 (RVA) = base+0x01EEC130')
    log(f'前置: sc stop ApolloProtect 是否已执行?')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'phase1':
                log(f'  [P1] {p["msg"]}')
            elif t == 'addr_check':
                prologue = '有效入口' if p['isPrologue'] else '非标准入口!'
                log(f'  [地址] {p["addr"]} [{prologue}]')
                log(f'    bytes: {p["bytes"]}')
            elif t == 'phase2':
                log(f'  [P2] {p["msg"]}')
            elif t == 'hook_fail':
                log(f'  [!!!] {p["msg"]}')
            elif t == 'string_ref':
                log(f'  [StringRef] {p["addr"]} bytes: {p["bytes"]}')
            elif t == 'sskf':
                log(f'  [SSKF #{p["n"]}] size={p["size"]} flag={p["flagHex"]}')
            elif t == 'acquire_call':
                idx = p['idx']
                log(f'  [ACQUIRE #{idx}] ===== 命中! =====')
                log(f'    寄存器: eax={p["regs"]["eax"]} ecx={p["regs"]["ecx"]}')
                log(f'            edx={p["regs"]["edx"]} esi={p["regs"]["esi"]}')
                log(f'    栈参数: {" ".join(p["stackArgs"])}')
                if p['ptrDumps']:
                    log(f'    指针参数:')
                    for pd in p['ptrDumps']:
                        log(f'      arg{pd["argIdx"]}: {pd["ptr"]} hex={pd["hex"]}')
                        log(f'              text="{pd["text"]}"')
                if p['thisStrings']:
                    log(f'    this对象字符串:')
                    for ts in p['thisStrings']:
                        log(f'      +{ts["off"]}: "{ts["str"]}"')
                if not p['ptrDumps'] and not p['thisStrings']:
                    log(f'    this hex: {p["thisDump"]}')
            elif t == 'backtrace':
                log(f'    backtrace #{p["idx"]}: {" → ".join(p["frames"])}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'info':
                log(f'  {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('=== 诊断已就绪 ===')
    log('进房间或换频道触发角色加载。')
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

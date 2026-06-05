"""
hook_crash_qualify.py — 低干扰崩溃定性脚本 (v2, 基于 05a 设计)
目标: 用最少 hook / 最少修改，先定性"谁在杀"（Apollo vs 业务崩）

原则:
  - 只 hook 系统 DLL (sprintf / CreateFileA / ReadFile) + ExceptionHandler
  - 不 hook 游戏 .text
  - 不 hook Actor 构造函数
  - 不扫描 vtable / 对象字段
  - 默认不修改 [ebp-0xD8]
  - verdict 只给信号等级，不轻易定案
"""
import sys, os, time, json, frida
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'crash_probe_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

PATCH_EBP_D8 = True
ENABLE_READFILE = True
ENABLE_VERBOSE_FILELOG = False
ENABLE_EXCEPTION_HANDLER = False  # 临时关闭，排除干扰


def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()


def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None


JS_TEMPLATE = r"""
'use strict';

var SRC_IC = __SRC_IC__;
var DST_IC = __DST_IC__;
var PATCH_EBP_D8 = __PATCH_EBP_D8__;
var ENABLE_READFILE = __ENABLE_READFILE__;
var ENABLE_EXCEPTION_HANDLER = __ENABLE_EXCEPTION_HANDLER__;

var base = ptr('0x400000');

var APOLLO_START = ptr('0x69000000');
var APOLLO_END   = ptr('0x69700000');
var GAME_START   = ptr('0x400000');
var GAME_END     = ptr('0x30000000');

var phase = 'INJECTED';

// ==========================================
// 事件缓存 (最多20条)
// ==========================================
var events = [];

function pushEvent(kind, data) {
    events.push({
        kind: kind,
        phase: phase,
        ts: Date.now(),
        data: data
    });
    if (events.length > 20) events.shift();
}

function setPhase(newPhase) {
    if (phase !== newPhase) {
        var old = phase;
        phase = newPhase;
        pushEvent('phase_change', {from: old, to: newPhase});
        send({t: 'phase', from: old, to: newPhase});
    }
}

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function hexAddr(p) {
    return '0x' + p.toString(16);
}

function classifyModule(eip) {
    if (eip.compare(APOLLO_START) >= 0 && eip.compare(APOLLO_END) <= 0)
        return 'ApolloCT.dll';
    if (eip.compare(GAME_START) >= 0 && eip.compare(GAME_END) <= 0)
        return 'FreeStyle.exe';
    var mod = Process.findModuleByAddress(eip);
    return mod ? mod.name : 'UNKNOWN';
}

// ==========================================
// 模块 A: 轻量阶段机
// ==========================================
var sprintfHitCount = 0;

// ==========================================
// 模块 B: 唯一业务修改点 — sprintf
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            var isTargetFmt =
                fmt.indexOf('customize\\item\\i%d.xml') >= 0 ||
                fmt.indexOf('customize\\item\\c%d.xml') >= 0;
            if (!isTargetFmt) return;

            var itemCode = args[2].toInt32();
            if (itemCode !== SRC_IC) return;

            args[2] = ptr(DST_IC);
            sprintfHitCount++;

            if (PATCH_EBP_D8) {
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);
            }

            if (sprintfHitCount === 1)
                setPhase('ROOM_LOAD');
            else if (sprintfHitCount === 2)
                setPhase('PRACTICE_LOAD');

            var retAddr = this.returnAddress;
            var retMod = '?';
            try {
                var m = Process.findModuleByAddress(retAddr);
                if (m) retMod = m.name + '+' + hexAddr(retAddr.sub(m.base));
            } catch(e) {}

            var payload = {
                hit: sprintfHitCount,
                fmt: fmt,
                orig: SRC_IC,
                new: DST_IC,
                ret: hexAddr(retAddr),
                ret_mod: retMod,
                ebpD8_patched: PATCH_EBP_D8
            };
            pushEvent('sprintf_patch', payload);
            send({t: 'sprintf', n: sprintfHitCount, fmt: fmt,
                   orig: SRC_IC, new: DST_IC, ret: hexAddr(retAddr),
                   ret_mod: retMod, ebpD8: PATCH_EBP_D8});
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook @ MSVCR100.dll'});

// ==========================================
// 模块 C: 文件层观察 — CreateFileA
// ==========================================
var cfCount = 0;
var kernel32 = null;
try {
    kernel32 = Process.getModuleByName('kernel32.dll');
} catch(e) {
    send({t: 'step', msg: 'kernel32 获取失败: ' + e});
}

try {
    if (kernel32 !== null) {
        var CreateFileA = kernel32.getExportByName('CreateFileA');

        var VERBOSE_FILE_LOG = true;  // 临时开启：打印所有文件访问

        Interceptor.attach(CreateFileA, {
            onEnter: function(args) {
                try {
                    var path = readAscii(args[0], 512);

                    // 宽松模式：匹配任何包含 item/res/resource 的路径
                    var match = false;
                    if (path.indexOf('item') >= 0) match = true;
                    if (path.indexOf('res') >= 0) match = true;
                    if (path.indexOf('Resource') >= 0) match = true;
                    if (path.indexOf('.bml') >= 0) match = true;
                    if (path.indexOf('.pak') >= 0) match = true;
                    if (path.indexOf('customize') >= 0) match = true;

                    // 调试模式：打印所有文件访问
                    if (VERBOSE_FILE_LOG) {
                        cfCount++;
                        var short = path.replace(/\\/g, '/').split('/').pop();
                        send({t: 'file', n: cfCount, path: path, short: short, api: 'CreateFileA'});
                    } else if (match) {
                        cfCount++;
                        var short = path.replace(/\\/g, '/').split('/').pop();
                        var payload = {n: cfCount, short: short, path: path, api: 'CreateFileA'};
                        pushEvent('create_file', payload);
                        send({t: 'file', n: cfCount, path: path, short: short, api: 'CreateFileA'});
                    }
                } catch(e) {}
            }
        });
        send({t: 'step', msg: 'CreateFileA hook @ kernel32.dll'});
    }
} catch(e) {
    send({t: 'step', msg: 'CreateFileA hook FAILED: ' + e});
}

// ==========================================
// 模块 C: 文件层观察 — CreateFileW (Unicode)
// ==========================================
try {
    if (kernel32 !== null) {
        var CreateFileW = kernel32.getExportByName('CreateFileW');

        Interceptor.attach(CreateFileW, {
            onEnter: function(args) {
                try {
                    // Unicode 字符串读取
                    var pathBuf = args[0];
                    var path = '';
                    for (var i = 0; i < 512; i++) {
                        var ch = pathBuf.add(i * 2).readU16();
                        if (ch === 0) break;
                        path += String.fromCharCode(ch);
                    }

                    // 宽松模式：匹配任何包含 item/res/resource 的路径
                    var match = false;
                    if (path.indexOf('item') >= 0) match = true;
                    if (path.indexOf('res') >= 0) match = true;
                    if (path.indexOf('Resource') >= 0) match = true;
                    if (path.indexOf('.bml') >= 0) match = true;
                    if (path.indexOf('.pak') >= 0) match = true;
                    if (path.indexOf('customize') >= 0) match = true;

                    // 调试模式：打印所有文件访问
                    if (VERBOSE_FILE_LOG) {
                        cfCount++;
                        var short = path.replace(/\\/g, '/').split('/').pop();
                        send({t: 'file', n: cfCount, path: path, short: short, api: 'CreateFileW'});
                    } else if (match) {
                        cfCount++;
                        var short = path.replace(/\\/g, '/').split('/').pop();
                        var payload = {n: cfCount, short: short, path: path, api: 'CreateFileW'};
                        pushEvent('create_file', payload);
                        send({t: 'file', n: cfCount, path: path, short: short, api: 'CreateFileW'});
                    }
                } catch(e) {}
            }
        });
        send({t: 'step', msg: 'CreateFileW hook @ kernel32.dll'});
    }
} catch(e) {
    send({t: 'step', msg: 'CreateFileW hook FAILED: ' + e});
}

// ==========================================
// 模块 C: 文件层观察 — ReadFile (弱辅助)
// ==========================================
var rfCount = 0;
if (ENABLE_READFILE) {
    try {
        if (kernel32 !== null) {
            var ReadFile = kernel32.getExportByName('ReadFile');

            Interceptor.attach(ReadFile, {
                onEnter: function(args) {
                    this.rbuf = args[1];
                    this.brPtr = args[3];
                },
                onLeave: function(retval) {
                    if (retval.toInt32() === 0) return;
                    try {
                        var bytesRead = this.brPtr.readU32();
                        if (bytesRead < 8) return;
                        var buf = this.rbuf;

                        var tag = null;
                        var head = buf.readU32();
                        if (head === 0x464B5353) tag = 'SSKF';          // 'SSKF'
                        else if (head === 0x6F6F723C) tag = 'XML_ROOT'; // '<roo' 小端

                        if (!tag) return;

                        rfCount++;
                        var payload = {tag: tag, bytes: bytesRead, n: rfCount};
                        pushEvent('read_file_tag', payload);
                        send({t: 'read', n: rfCount, tag: tag, bytes: bytesRead});
                    } catch(e) {}
                }
            });
            send({t: 'step', msg: 'ReadFile hook @ kernel32.dll (弱辅助)'});
        }
    } catch(e) {
        send({t: 'step', msg: 'ReadFile hook FAILED: ' + e});
    }
}

// ==========================================
// 模块 D: 异常处理器 (核心) — 可选
// ==========================================
if (ENABLE_EXCEPTION_HANDLER) {
    Process.setExceptionHandler(function(details) {
        var phaseBeforeCrash = phase;
        setPhase('CRASH');

        var eip = details.context.pc;
        var mod = classifyModule(eip);
        var inst = '';
        var hasCC = false;

        try {
            var raw = new Uint8Array(eip.readByteArray(16));
            for (var i = 0; i < 16; i++) {
                inst += ('0' + raw[i].toString(16)).slice(-2) + ' ';
                if (raw[i] === 0xCC) hasCC = true;
            }
        } catch(e) {}

        var memAddr = 'N/A';
        var memOp = 'N/A';
        if (details.memory) {
            memAddr = details.memory.address ? hexAddr(details.memory.address) : 'N/A';
            memOp = details.memory.operation || 'N/A';
        }

        var memAddrSmall = false;
        if (details.memory && details.memory.address) {
            try {
                memAddrSmall = details.memory.address.toUInt32() < 0x1000;
            } catch(e) {}
        }

        var isLikelyNullAccess = memAddrSmall;

        // ---- verdict ----
        var verdict = 'UNKNOWN';
        if (mod === 'ApolloCT.dll' && hasCC)
            verdict = 'STRONG_APOLLO_SIGNAL';
        else if (mod === 'ApolloCT.dll')
            verdict = 'WEAK_APOLLO_SIGNAL';
        else if (mod === 'FreeStyle.exe' && isLikelyNullAccess)
            verdict = 'STRONG_BUSINESS_SIGNAL';
        else if (mod === 'FreeStyle.exe')
            verdict = 'WEAK_BUSINESS_SIGNAL';

        var backtrace = [];
        try {
            var bt = Thread.backtrace(details.context, Backtracer.ACCURATE);
            var apolloInBT = false;
            for (var i = 0; i < Math.min(bt.length, 10); i++) {
                var addr = bt[i];
                var m = Process.findModuleByAddress(addr);
                var modName = m ? m.name : '?';
                var rva = m ? hexAddr(addr.sub(m.base)) : '?';
                backtrace.push({mod: modName, rva: rva, addr: hexAddr(addr)});
                if (modName === 'ApolloCT.dll') apolloInBT = true;
            }

            if (verdict === 'WEAK_BUSINESS_SIGNAL' && apolloInBT)
                verdict = 'WEAK_APOLLO_SIGNAL';
            if (verdict === 'UNKNOWN' && apolloInBT)
                verdict = 'WEAK_APOLLO_SIGNAL';
        } catch(e) {}

        var lastEvents = events.slice(-8);

        send({
            t: 'CRASH',
            phase: phaseBeforeCrash,
            phase_now: phase,
            verdict: verdict,
            module: mod,
            eip: hexAddr(eip),
            rva: hexAddr(eip.sub(base)),
            inst: inst.trim(),
            hasCC: hasCC,
            crashType: details.type,
            memAddr: memAddr,
            memOp: memOp,
            eax: hexAddr(details.context.eax),
            ecx: hexAddr(details.context.ecx),
            edx: hexAddr(details.context.edx),
            ebx: hexAddr(details.context.ebx),
            esp: hexAddr(details.context.esp),
            ebp: hexAddr(details.context.ebp),
            backtrace: backtrace,
            last_events: lastEvents
        });

        return false;
    });

    send({t: 'step', msg: 'ExceptionHandler 已设置'});
} else {
    send({t: 'step', msg: 'ExceptionHandler 已禁用 (调试模式)'});
}

// ==========================================
// 就绪
// ==========================================
pushEvent('phase_change', {from: '', to: 'INJECTED'});
send({t: 'ready', src: SRC_IC, dst: DST_IC, ebpD8: PATCH_EBP_D8,
       readfile: ENABLE_READFILE});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            hits: sprintfHitCount,
            cfs: cfCount,
            rfs: rfCount,
            events: events.slice(-10)
        });
    },
    phase: function() { return phase; }
};
"""

JS_CODE = (
    JS_TEMPLATE
    .replace('__SRC_IC__', str(SRC_IC))
    .replace('__DST_IC__', str(DST_IC))
    .replace('__PATCH_EBP_D8__', 'true' if PATCH_EBP_D8 else 'false')
    .replace('__ENABLE_READFILE__', 'true' if ENABLE_READFILE else 'false')
    .replace('__ENABLE_EXCEPTION_HANDLER__', 'true' if ENABLE_EXCEPTION_HANDLER else 'false')
)


def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'===== 低干扰崩溃定性脚本 v2 =====')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
    log(f'PATCH_EBP_D8: {PATCH_EBP_D8}')
    log(f'ENABLE_READFILE: {ENABLE_READFILE}')
    log(f'ENABLE_VERBOSE_FILELOG: {ENABLE_VERBOSE_FILELOG}')
    log(f'日志: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'step':
                log(f'  [setup] {p["msg"]}')

            elif t == 'ready':
                log(f'  [ready] SRC={p["src"]} DST={p["dst"]} '
                    f'EBP_D8={p["ebpD8"]} ReadFile={p["readfile"]}')

            elif t == 'phase':
                log(f'')
                log(f'[phase] {p["from"]} -> {p["to"]}')
                log(f'')

            elif t == 'sprintf':
                log(f'[sprintf] #{p["n"]} fmt="{p["fmt"]}" '
                    f'{p["orig"]}->{p["new"]} ret={p["ret"]} ({p["ret_mod"]}) '
                    f'ebpD8={p["ebpD8"]}')

            elif t == 'file':
                if ENABLE_VERBOSE_FILELOG:
                    log(f'[file] {p["path"]}')
                else:
                    log(f'[file] {p["short"]}')

            elif t == 'read':
                log(f'[read] tag={p["tag"]} bytes={p["bytes"]}')

            elif t == 'CRASH':
                log('')
                log('===== CRASH SUMMARY =====')
                log(f'phase: {p["phase"]}')
                log(f'phase_now: {p["phase_now"]}')
                log(f'verdict: {p["verdict"]}')
                log(f'module: {p["module"]}')
                log(f'eip: {p["eip"]}')
                log(f'rva: {p["rva"]}')
                log(f'type: {p["crashType"]}')
                log(f'instruction: {p["inst"]}')
                log(f'memory: {p["memOp"]} @ {p["memAddr"]}')
                log(f'registers: eax={p["eax"]} ecx={p["ecx"]} '
                    f'edx={p["edx"]} ebx={p["ebx"]}')
                log(f'           esp={p["esp"]} ebp={p["ebp"]}')

                log(f'recent events:')
                for ev in p.get('last_events', []):
                    d = ev.get('data', {})
                    if ev['kind'] == 'sprintf_patch':
                        log(f'  [{ev["phase"]}] sprintf_patch #{d["hit"]} '
                            f'{d["orig"]}->{d["new"]} ret={d["ret"]} ({d["ret_mod"]})')
                    elif ev['kind'] == 'create_file':
                        log(f'  [{ev["phase"]}] create_file #{d["n"]} {d["short"]}')
                    elif ev['kind'] == 'read_file_tag':
                        log(f'  [{ev["phase"]}] read_file #{d["n"]} '
                            f'tag={d["tag"]} bytes={d["bytes"]}')
                    elif ev['kind'] == 'phase_change':
                        log(f'  [{ev["phase"]}] phase_change {d["from"]}->{d["to"]}')
                    else:
                        log(f'  [{ev["phase"]}] {ev["kind"]}')

                log(f'backtrace:')
                for bt in p.get('backtrace', []):
                    log(f'  {bt["mod"]}+{bt["rva"]} ({bt["addr"]})')

                log('=========================')
                log('')

                v = p['verdict']
                if 'APOLLO_SIGNAL' in v:
                    log('>>> 信号指向 Apollo。建议:')
                    log('>>>   1. 确认 ApolloProtect 已完全停止 (STATE 1)')
                    log('>>>   2. 或改用 debug_inject.py 方案')
                elif 'BUSINESS_SIGNAL' in v:
                    log('>>> 信号指向业务崩。建议:')
                    log('>>>   1. 进入第二阶段: 观察 Actor 类型 / motion type / 物理字段')
                    log('>>>   2. 或改用同类型 (静态→静态) 替换方案')
                else:
                    log('>>> 无法定性。建议:')
                    log('>>>   1. 检查 backtrace 确认模块归属')
                    log('>>>   2. 对比不同阶段日志差异')

            elif t == 'error':
                log(f'  [error] {p["msg"]}')
            else:
                log(f'  [other] {json.dumps(p, ensure_ascii=False)[:200]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")} '
                f'line={msg.get("lineNumber", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('操作:')
    log('  1. 进房间 → 触发第一次替换 (phase→ROOM_LOAD)')
    log('  2. 确认渲染成功')
    log('  3. 进练习场 → 触发第二次替换 (phase→PRACTICE_LOAD)')
    log('  4. 观察崩溃或正常')
    log('')
    log('命令: status | phase | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'phase':
                log(f'  phase={script.exports_sync.phase()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

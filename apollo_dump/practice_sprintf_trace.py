# practice_sprintf_trace.py
# 核心问题：练习场阶段 sprintf 走了什么 ItemCode？
# 既然 SRC_IC 没被清零，说明练习场要么不调 sprintf，要么用别的路径
#
# 策略：
#   1. hook sprintf 监控所有 customize/item 调用，不替换
#   2. 记录每次调用的返回地址（定位调用者）
#   3. 同时监控那12个地址的变化
#   4. ctx 命令读取任意地址上下文
import sys
import os
import time
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'practice_trace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461   # 美丽梦想(静态, pak767)
DST_IC = 50125711   # 紫色超赛(动态, pak768)

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

function hexAddr(p) {
    return '0x' + p.toString(16);
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

function getBacktrace(ctx) {
    try {
        return Thread.backtrace(ctx, Backtracer.ACCURATE)
            .map(function(addr) {
                var mod = '?';
                try {
                    var m = Process.findModuleByAddress(addr);
                    if (m) mod = m.name + '+0x' + addr.sub(m.base).toString(16);
                } catch(e) {}
                return hexAddr(addr) + '(' + mod + ')';
            });
    } catch(e) {
        return ['backtrace_failed'];
    }
}

var sprintfCount = 0;
var allSprintfCalls = [];  // 所有 customize/item sprintf 调用记录

// ==========================================
// 1. sprintf hook — 全量记录，不替换
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfCount++;

            var retAddr = this.returnAddress;
            var retMod = '?';
            try {
                var m = Process.findModuleByAddress(retAddr);
                if (m) retMod = m.name + '+0x' + retAddr.sub(m.base).toString(16);
            } catch(e) {}

            // 读调用栈上的 ebp 和对象指针
            var ebp = this.context.ebp;
            var objInfo = {};
            try {
                var outerPtr = ebp.sub(0x478c).readPointer();
                var subObjPtr = outerPtr.add(0x164).readPointer();
                var val7DC = subObjPtr.add(0x7DC).readU32();
                objInfo = {
                    outer: hexAddr(outerPtr),
                    subObj: hexAddr(subObjPtr),
                    val7DC: val7DC
                };
            } catch(e) {
                objInfo = {error: e.toString()};
            }

            var record = {
                n: sprintfCount,
                ic: ic,
                ret: hexAddr(retAddr),
                retMod: retMod,
                ebp: hexAddr(ebp),
                obj: objInfo,
                ts: Date.now()
            };

            allSprintfCalls.push(record);

            send({
                t: 'sprintf',
                n: sprintfCount,
                ic: ic,
                ret: hexAddr(retAddr),
                retMod: retMod,
                obj: objInfo
            });

        } catch(e) {
            send({t: 'error', msg: 'sprintf: ' + e});
        }
    }
});
send({t: 'step', msg: 'sprintf hook (monitor, no replace)'});

// ==========================================
// 2. 监控那12个已知地址的变化
// ==========================================
var watchedAddrs = [];
var lastWatchedVals = {};

function addWatch(addrHex) {
    try {
        var addr = ptr(addrHex);
        var val = addr.readU32();
        watchedAddrs.push(addr);
        lastWatchedVals[addrHex] = val;
    } catch(e) {}
}

var watchTimer = null;
function startWatching() {
    if (watchTimer) return;
    watchTimer = setInterval(function() {
        for (var i = 0; i < watchedAddrs.length; i++) {
            try {
                var addr = watchedAddrs[i];
                var key = hexAddr(addr);
                var val = addr.readU32();
                if (lastWatchedVals[key] !== val) {
                    send({
                        t: 'watch_change',
                        addr: key,
                        old: lastWatchedVals[key],
                        new: val
                    });
                    lastWatchedVals[key] = val;
                }
            } catch(e) {}
        }
    }, 200);
}

// ==========================================
// 3. CreateFileA/W — 监控 BML 文件访问
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');

Interceptor.attach(kernel32.getExportByName('CreateFileA'), {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 512);
            if (path.indexOf('50125') >= 0 || path.indexOf('.bml') >= 0) {
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', short: short, api: 'A'});
            }
        } catch(e) {}
    }
});

Interceptor.attach(kernel32.getExportByName('CreateFileW'), {
    onEnter: function(args) {
        try {
            var pathBuf = args[0];
            var path = '';
            for (var i = 0; i < 256; i++) {
                var ch = pathBuf.add(i * 2).readU16();
                if (ch === 0) break;
                path += String.fromCharCode(ch);
            }
            if (path.indexOf('50125') >= 0 || path.indexOf('.bml') >= 0) {
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', short: short, api: 'W'});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA/W hooks ready'});

// ==========================================
// 4. LoadItemFile hook — 禁用！会触发 Apollo
// ==========================================
// hook_practice_debug.py 已验证：LoadItemFile hook 导致崩溃
send({t: 'step', msg: 'LoadItemFile hook DISABLED (triggers Apollo)'});

// ==========================================
// RPC
// ==========================================
rpc.exports = {
    // 读取地址上下文（前后各16个dword = 128字节）
    ctx: function(addrHex) {
        try {
            var addr = ptr(addrHex);
            var lines = [];
            for (var off = -64; off <= 64; off += 4) {
                try {
                    var v = addr.add(off).readU32();
                    var marker = '';
                    if (v === SRC_IC) marker = ' <-- SRC_IC';
                    else if (v === DST_IC) marker = ' <-- DST_IC';
                    else if (v === 0) marker = ' (0)';
                    else if (v > 0x10000 && v < 0x90000000) marker = ' (ptr?)';
                    lines.push(hexAddr(addr.add(off)) + ' [' + (off >= 0 ? '+' : '') + '0x' + off.toString(16) + '] = 0x' + v.toString(16) + ' (' + v + ')' + marker);
                } catch(e) {
                    lines.push(hexAddr(addr.add(off)) + ' ERR');
                }
            }
            return lines.join('\n');
        } catch(e) {
            return 'ERROR: ' + e;
        }
    },

    // 添加地址到监控列表
    watch: function(addrHex) {
        addWatch(addrHex);
        startWatching();
        return 'watching ' + addrHex + ' (total ' + watchedAddrs.length + ')';
    },

    // 批量添加监控
    watchBatch: function(addrJson) {
        var addrs = JSON.parse(addrJson);
        for (var i = 0; i < addrs.length; i++) {
            addWatch(addrs[i]);
        }
        startWatching();
        return 'watching ' + watchedAddrs.length + ' addresses';
    },

    // 获取所有 sprintf 调用记录
    history: function() {
        return JSON.stringify(allSprintfCalls);
    },

    // 当前12个地址的值
    probe: function(addrJson) {
        var addrs = JSON.parse(addrJson);
        var results = [];
        for (var i = 0; i < addrs.length; i++) {
            try {
                var v = ptr(addrs[i]).readU32();
                results.push(addrs[i] + ' = ' + v + (v === SRC_IC ? ' (SRC)' : v === DST_IC ? ' (DST)' : v === 0 ? ' (ZERO)' : ''));
            } catch(e) {
                results.push(addrs[i] + ' = ERR');
            }
        }
        return results.join('\n');
    }
};

send({t: 'ready', src: SRC_IC, dst: DST_IC});
"""

JS_CODE = (
    JS_TEMPLATE
    .replace('__SRC_IC__', str(SRC_IC))
    .replace('__DST_IC__', str(DST_IC))
)

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe not running')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log('=== Practice sprintf Trace ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC} 美丽梦想(静态, pak767)')
    log(f'DST: {DST_IC} 紫色超赛(动态, pak768)')
    log(f'Log: {LOG_FILE}')
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
                log(f'  [ready]')

            elif t == 'sprintf':
                ic = p['ic']
                marker = ' <== SRC' if ic == SRC_IC else ' <== DST' if ic == DST_IC else ''
                obj = p.get('obj', {})
                log(f'[sprintf] #{p["n"]} ic={ic}{marker} ret={p["ret"]} ({p["retMod"]})')
                if 'subObj' in obj:
                    log(f'    subObj={obj["subObj"]} +0x7DC={obj["val7DC"]}')
                elif 'error' in obj:
                    log(f'    obj read err: {obj["error"]}')

            elif t == 'LoadItemFile':
                if 'error' in p:
                    log(f'[LoadItemFile] err: {p["error"]}')
                else:
                    log(f'[LoadItemFile] params={p["params"]} nearIC={p.get("nearIC",[])} ret={p.get("retAddr","")}')
                    for i, f in enumerate(p.get('backtrace', [])[:5]):
                        log(f'    [{i}] {f}')

            elif t == 'watch_change':
                marker = ''
                if p['new'] == SRC_IC: marker = ' (SRC)'
                elif p['new'] == DST_IC: marker = ' (DST)'
                elif p['new'] == 0: marker = ' (ZERO!)'
                log(f'  [watch] {p["addr"]}: {p["old"]} -> {p["new"]}{marker}')

            elif t == 'file':
                log(f'[file] {p["short"]} ({p["api"]})')

            elif t == 'error':
                log(f'  [error] {p["msg"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")} line={msg.get("lineNumber", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('流程:')
    log('  1. 进房间 → 观察 sprintf 和 LoadItemFile')
    log('  2. 进练习场 → 关键：看有没有新的 sprintf/LoadItemFile')
    log('  3. 如果没有 → 说明练习场根本不走 sprintf 路径')
    log('')
    log('命令:')
    log('  ctx <addr>         读取地址上下文')
    log('  watch <addr>       监控地址变化')
    log('  watchall           监控已知12个地址')
    log('  probe              读取12个地址当前值')
    log('  history            查看所有 sprintf 调用历史')
    log('  quit')
    log('')

    # 已知的12个地址（从上一次扫描结果）
    known_addrs = [
        '0x220cbef0', '0x25ad2a98', '0x4bc5f172', '0x64083248',
        '0x679bd108', '0x679bd4f0', '0x6cb8e048', '0x6d78195c',
        '0x82966748', '0x8616d854', '0x867599ac', '0x86e4acd8'
    ]

    try:
        while True:
            cmd = input('> ').strip()
            if cmd.lower() in ('quit', 'q', 'exit'):
                break

            elif cmd.lower() == 'probe':
                result = script.exports_sync.probe(json.dumps(known_addrs))
                for line in result.split('\n'):
                    log(f'  {line}')

            elif cmd.lower() == 'watchall':
                result = script.exports_sync.watchBatch(json.dumps(known_addrs))
                log(f'  {result}')

            elif cmd.lower().startswith('watch '):
                addr = cmd.split()[1]
                result = script.exports_sync.watch(addr)
                log(f'  {result}')

            elif cmd.lower().startswith('ctx '):
                addr = cmd.split()[1]
                result = script.exports_sync.ctx(addr)
                for line in result.split('\n'):
                    log(f'  {line}')

            elif cmd.lower() == 'history':
                result = script.exports_sync.history()
                calls = json.loads(result)
                log(f'  total: {len(calls)} calls')
                for c in calls:
                    ic = c['ic']
                    marker = ' SRC' if ic == SRC_IC else ' DST' if ic == DST_IC else ''
                    log(f'  #{c["n"]} ic={ic}{marker} ret={c["ret"]} ({c["retMod"]})')

    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('Done.')

if __name__ == '__main__':
    main()

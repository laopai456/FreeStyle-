# scan_itemcode_diff.py
# P0-改进：两次内存扫描对比，定位练习场阶段哪个对象的 ItemCode 被清零
#
# 流程：
#   1. 进房间，发型显示正常 → 输入 scan1 → 记录所有含 SRC_IC 的地址
#   2. 进练习场 → 输入 scan2 → 再次扫描，对比差异
#   3. 自动输出：哪些地址消失/变了/被清零
import sys
import os
import time
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'scan_diff_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461   # 美丽梦想(静态, pak767)
DST_IC = 50125711   # 紫色超赛(动态, pak768)
SRC_IC_HEX = struct.pack('<I', SRC_IC).hex() if False else ''  # just for reference

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

// ==========================================
// 内存扫描：找所有包含 target 值的地址
// 扫描范围：游戏主模块 + 堆区
// ==========================================
function scanMemory(target, phase_label) {
    var results = [];
    var TARGET = target;

    // 获取所有模块范围
    var modules = Process.enumerateModules();
    var scanRanges = [];

    for (var i = 0; i < modules.length; i++) {
        var m = modules[i];
        // 跳过系统DLL和太小的模块
        if (m.size < 0x1000) continue;
        if (m.name.toLowerCase().indexOf('apollo') >= 0) continue;  // 跳过Apollo避免触发
        if (m.name.toLowerCase().indexOf('ntdll') >= 0) continue;
        if (m.name.toLowerCase().indexOf('kernel32') >= 0) continue;
        if (m.name.toLowerCase().indexOf('kernelbase') >= 0) continue;
        if (m.name.toLowerCase().indexOf('user32') >= 0) continue;
        if (m.name.toLowerCase().indexOf('gdi32') >= 0) continue;
        if (m.name.toLowerCase().indexOf('msvcr') >= 0) continue;
        if (m.name.toLowerCase().indexOf('msvcp') >= 0) continue;
        if (m.name.toLowerCase().indexOf('frida') >= 0) continue;

        scanRanges.push({base: m.base, size: m.size, name: m.name});
    }

    // 也扫描堆区（通过 Memory.scanSync）
    // 先扫描模块
    for (var r = 0; r < scanRanges.length; r++) {
        var range = scanRanges[r];
        try {
            var pattern = TARGET.toString(16);
            // 补齐8位
            while (pattern.length < 8) pattern = '0' + pattern;
            // 转成 "50 12 54 61" 格式（小端序）
            var bytes = [];
            for (var b = 0; b < 4; b++) {
                var byteStr = pattern.substr(6 - b * 2, 2);
                bytes.push(byteStr);
            }
            var searchPattern = bytes.join(' ');

            var matches = Memory.scanSync(range.base, range.size, searchPattern);
            for (var j = 0; j < matches.length; j++) {
                var addr = matches[j].address;
                var offset = addr.sub(range.base).toInt32();
                results.push({
                    addr: hexAddr(addr),
                    module: range.name,
                    offset: '0x' + offset.toString(16),
                    value: TARGET
                });
            }
        } catch(e) {
            // 某些页面可能不可读，跳过
        }
    }

    // 扫描堆区：枚举所有可读写内存范围
    try {
        var pattern = TARGET.toString(16);
        while (pattern.length < 8) pattern = '0' + pattern;
        var bytes = [];
        for (var b = 0; b < 4; b++) {
            var byteStr = pattern.substr(6 - b * 2, 2);
            bytes.push(byteStr);
        }
        var searchPattern = bytes.join(' ');

        var allRanges = Process.enumerateRanges('rw-');
        for (var r = 0; r < allRanges.length; r++) {
            var range = allRanges[r];
            // 跳过栈区和太小的段
            if (range.size < 0x100) continue;
            if (range.size > 0x1000000) continue;  // 跳过超大段（>16MB）

            // 跳过已扫描的模块范围
            var isModule = false;
            for (var m = 0; m < scanRanges.length; m++) {
                if (range.base >= scanRanges[m].base &&
                    range.base < scanRanges[m].base.add(scanRanges[m].size)) {
                    isModule = true;
                    break;
                }
            }
            if (isModule) continue;

            try {
                var matches = Memory.scanSync(range.base, range.size, searchPattern);
                for (var j = 0; j < matches.length; j++) {
                    results.push({
                        addr: hexAddr(matches[j].address),
                        module: 'heap',
                        offset: '',
                        value: TARGET
                    });
                }
            } catch(e) {}
        }
    } catch(e) {
        send({t: 'scan_error', msg: 'heap scan error: ' + e});
    }

    return results;
}

// ==========================================
// 扫描 +0x7DC 附近的上下文
// 对找到的每个地址，读取前后字段帮助定位结构
// ==========================================
function scanWithContext(target, phase_label) {
    var results = scanMemory(target, phase_label);

    // 给每个结果加上下文（前后各8个dword）
    for (var i = 0; i < results.length; i++) {
        try {
            var addr = ptr(results[i].addr);
            var ctx = [];
            // 读 -32 到 +32 字节
            for (var off = -32; off <= 32; off += 4) {
                try {
                    var v = addr.add(off).readU32();
                    var marker = '';
                    if (v === target) marker = ' <--';
                    else if (v === DST_IC) marker = ' <-- DST';
                    else if (v === 0) marker = ' (0)';
                    ctx.push('0x' + off.toString(16) + '=' + v + marker);
                } catch(e) {
                    ctx.push('0x' + off.toString(16) + '=ERR');
                }
            }
            results[i].context = ctx;
        } catch(e) {
            results[i].context = ['context_error'];
        }
    }

    return results;
}

// ==========================================
// RPC 接口
// ==========================================
var scan1Results = null;
var scan2Results = null;

rpc.exports = {
    // 第一次扫描（房间阶段）
    scan1: function() {
        send({t: 'scan_start', n: 1, target: SRC_IC});
        scan1Results = scanWithContext(SRC_IC, 'room');
        send({t: 'scan_done', n: 1, count: scan1Results.length});
        return JSON.stringify(scan1Results.map(function(r) {
            return r.addr + ' (' + r.module + (r.offset ? '+' + r.offset : '') + ')';
        }));
    },

    // 第二次扫描（练习场阶段）
    scan2: function() {
        send({t: 'scan_start', n: 2, target: SRC_IC});
        scan2Results = scanWithContext(SRC_IC, 'practice');
        send({t: 'scan_done', n: 2, count: scan2Results.length});
        return JSON.stringify(scan2Results.map(function(r) {
            return r.addr + ' (' + r.module + (r.offset ? '+' + r.offset : '') + ')';
        }));
    },

    // 对比两次扫描
    diff: function() {
        if (!scan1Results || !scan2Results) {
            return 'ERROR: need scan1 and scan2 first';
        }

        var map1 = {};
        for (var i = 0; i < scan1Results.length; i++) {
            map1[scan1Results[i].addr] = scan1Results[i];
        }
        var map2 = {};
        for (var i = 0; i < scan2Results.length; i++) {
            map2[scan2Results[i].addr] = scan2Results[i];
        }

        var disappeared = [];  // scan1有但scan2没有（被清零/改写）
        var appeared = [];     // scan2有但scan1没有（新出现）
        var same = [];         // 两次都有

        for (var addr in map1) {
            if (!map2[addr]) {
                disappeared.push(map1[addr]);
            } else {
                same.push({addr: addr, ctx1: map1[addr].context, ctx2: map2[addr].context});
            }
        }
        for (var addr in map2) {
            if (!map1[addr]) {
                appeared.push(map2[addr]);
            }
        }

        // 对消失的地址，读取当前值
        var disappearedDetails = [];
        for (var i = 0; i < disappeared.length; i++) {
            try {
                var addr = ptr(disappeared[i].addr);
                var curVal = addr.readU32();
                disappearedDetails.push({
                    addr: disappeared[i].addr,
                    module: disappeared[i].module,
                    offset: disappeared[i].offset,
                    oldValue: SRC_IC,
                    curValue: curVal,
                    isZero: curVal === 0,
                    context: disappeared[i].context
                });
            } catch(e) {
                disappearedDetails.push({
                    addr: disappeared[i].addr,
                    module: disappeared[i].module,
                    offset: disappeared[i].offset,
                    oldValue: SRC_IC,
                    curValue: 'READ_ERR',
                    context: disappeared[i].context
                });
            }
        }

        return JSON.stringify({
            disappeared: disappearedDetails,
            appeared: appeared,
            sameCount: same.length
        });
    },

    // 也扫描 DST_IC
    scan_dst: function() {
        var results = scanMemory(DST_IC, 'extra');
        return JSON.stringify(results.map(function(r) {
            return r.addr + ' (' + r.module + (r.offset ? '+' + r.offset : '') + ')';
        }));
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
    log('=== Scan ItemCode Diff ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC} 美丽梦想(静态, pak767)')
    log(f'DST: {DST_IC} 紫色超赛(动态, pak768)')
    log(f'Scan target: SRC_IC (0x{SRC_IC:08X}) 小端序')
    log(f'Log: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'scan_start':
                log(f'[scan#{p["n"]}] scanning for 0x{p["target"]:08X}...')
            elif t == 'scan_done':
                log(f'[scan#{p["n"]}] done, found {p["count"]} hits')
            elif t == 'scan_error':
                log(f'  [scan_error] {p["msg"]}')
            elif t == 'ready':
                log(f'  [ready] SRC={p["src"]} DST={p["dst"]}')
            elif t == 'error':
                log(f'  [error] {p["msg"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")} line={msg.get("lineNumber", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('流程:')
    log('  1. 进房间，发型显示正常')
    log('  2. 输入 scan1  → 记录所有含 SRC_IC 的地址')
    log('  3. 进练习场')
    log('  4. 输入 scan2  → 再次扫描')
    log('  5. 输入 diff   → 对比差异，找出被清零的地址')
    log('')
    log('命令: scan1 | scan2 | diff | scan_dst | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'scan1':
                result = script.exports_sync.scan1()
                addrs = json.loads(result)
                log(f'  scan1: {len(addrs)} hits')
                for a in addrs:
                    log(f'    {a}')
            elif cmd == 'scan2':
                result = script.exports_sync.scan2()
                addrs = json.loads(result)
                log(f'  scan2: {len(addrs)} hits')
                for a in addrs:
                    log(f'    {a}')
            elif cmd == 'diff':
                result = script.exports_sync.diff()
                d = json.loads(result)

                log('')
                log(f'=== DIFF RESULTS ===')
                log(f'  disappeared: {len(d["disappeared"])}')
                log(f'  appeared: {len(d["appeared"])}')
                log(f'  same: {d["sameCount"]}')
                log('')

                if d['disappeared']:
                    log('--- DISAPPEARED (被清零/改写) ---')
                    for item in d['disappeared']:
                        marker = ' <== ZEROED!' if item.get('isZero') else ''
                        log(f'  {item["addr"]} ({item["module"]}+{item["offset"]})')
                        log(f'    old={item["oldValue"]} cur={item["curValue"]}{marker}')
                        if item.get('context'):
                            log(f'    context (scan1): {" ".join(item["context"][:8])}')
                    log('')

                if d['appeared']:
                    log('--- APPEARED (新出现) ---')
                    for item in d['appeared']:
                        log(f'  {item["addr"]} ({item["module"]}+{item["offset"]})')
                    log('')

            elif cmd == 'scan_dst':
                result = script.exports_sync.scan_dst()
                addrs = json.loads(result)
                log(f'  scan_dst (DST_IC={DST_IC}): {len(addrs)} hits')
                for a in addrs:
                    log(f'    {a}')

    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('Done.')

if __name__ == '__main__':
    main()

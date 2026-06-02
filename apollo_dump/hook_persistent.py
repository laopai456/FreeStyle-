"""
hook_persistent.py — 持续补丁: 服务器写入后立刻替换
策略:
  1. 扫描找到所有INT 50125461的地址 (只需一次)
  2. 启动高频定时器(10ms), 持续检查这些地址
  3. 如果服务器写入了50125461, 立刻替换为50125711
  4. 游戏读取时已经是50125711 → 走完整动态管线

为什么10ms够:
  从trace看, DynamicCreate1的第4次调用(发型)在进房间2秒后
  服务器数据和角色创建之间有明显间隔, 10ms定时器能轻松赶上
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'persistent_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var SRC_INT = 50125461;
var DST_INT = 50125711;
var SRC_STR = '50125461';
var DST_STR = '50125711';

var dstAsciiBytes = [];
for (var i = 0; i < DST_STR.length; i++) dstAsciiBytes.push(DST_STR.charCodeAt(i));

// Phase 1: 找到所有INT地址
var ranges = Process.enumerateRanges('rw-');
var watchAddrs = [];
var intAddrs = [];
var asciiAddrs = [];

for (var ri = 0; ri < ranges.length; ri++) {
    var r = ranges[ri];
    if (r.size < 8 || r.size > 200 * 1024 * 1024) continue;
    try { var mod = Process.findModuleByAddress(r.base); if (mod) continue; } catch(e) {}

    // 扫描INT
    try {
        var matches = Memory.scanSync(r.base, r.size, '95 da fc 02');
        for (var mi = 0; mi < matches.length; mi++) {
            intAddrs.push(matches[mi].address);
            watchAddrs.push({addr: matches[mi].address, type: 'int'});
        }
    } catch(e) {}

    // 扫描ASCII (记录每个的位置)
    try {
        var hexPat = '';
        for (var i = 0; i < SRC_STR.length; i++) hexPat += ('0' + SRC_STR.charCodeAt(i).toString(16)).slice(-2) + ' ';
        hexPat = hexPat.trim();
        var matches = Memory.scanSync(r.base, r.size, hexPat);
        for (var mi = 0; mi < matches.length; mi++) {
            asciiAddrs.push(matches[mi].address);
            watchAddrs.push({addr: matches[mi].address, type: 'ascii', len: SRC_STR.length});
        }
    } catch(e) {}
}

send({t: 'found', ints: intAddrs.length, asciis: asciiAddrs.length});

// 立即做一次替换
var initPatch = 0;
for (var i = 0; i < watchAddrs.length; i++) {
    var w = watchAddrs[i];
    if (w.type === 'int') {
        try { w.addr.writeU32(DST_INT); initPatch++; } catch(e) {}
    } else {
        try { for (var j = 0; j < dstAsciiBytes.length; j++) w.addr.add(j).writeU8(dstAsciiBytes[j]); initPatch++; } catch(e) {}
    }
}
send({t: 'init_patch', count: initPatch});

// Phase 2: 高频定时器持续替换
var timerFixes = 0;
var timerRunning = true;

var timer = setInterval(function() {
    if (!timerRunning) return;
    var fixed = 0;

    for (var i = 0; i < watchAddrs.length; i++) {
        var w = watchAddrs[i];
        try {
            if (w.type === 'int') {
                var val = w.addr.readU32();
                if (val === SRC_INT) {
                    w.addr.writeU32(DST_INT);
                    fixed++;
                    timerFixes++;
                }
            } else {
                var match = true;
                for (var j = 0; j < 8; j++) {
                    if (w.addr.add(j).readU8() !== dstAsciiBytes[j]) { match = false; break; }
                }
                if (!match) {
                    // 检查是否是SRC_STR被写了回来
                    var srcMatch = true;
                    for (var j = 0; j < SRC_STR.length; j++) {
                        if (w.addr.add(j).readU8() !== SRC_STR.charCodeAt(j)) { srcMatch = false; break; }
                    }
                    if (srcMatch) {
                        for (var j = 0; j < dstAsciiBytes.length; j++) {
                            w.addr.add(j).writeU8(dstAsciiBytes[j]);
                        }
                        fixed++;
                        timerFixes++;
                    }
                }
            }
        } catch(e) {
            // 地址可能被释放, 从监控列表移除
            watchAddrs.splice(i, 1);
            i--;
        }
    }

    if (fixed > 0) {
        send({t: 'timer_fix', fixed: fixed, total: timerFixes});
    }
}, 10);

// Phase 3: 也在新内存中搜索 (服务器可能分配新地址)
// 每2秒重新扫描一次堆内存
var scanTimer = setInterval(function() {
    if (!timerRunning) return;
    var ranges = Process.enumerateRanges('rw-');
    var newInts = 0;

    for (var ri = 0; ri < ranges.length; ri++) {
        var r = ranges[ri];
        if (r.size < 8 || r.size > 200 * 1024 * 1024) continue;
        try { var mod = Process.findModuleByAddress(r.base); if (mod) continue; } catch(e) {}

        try {
            var matches = Memory.scanSync(r.base, r.size, '95 da fc 02');
            for (var mi = 0; mi < matches.length; mi++) {
                var addr = matches[mi].address;
                // 检查是否已经在监控列表
                var known = false;
                for (var i = 0; i < watchAddrs.length; i++) {
                    if (watchAddrs[i].addr.equals(addr)) { known = true; break; }
                }
                if (!known) {
                    addr.writeU32(DST_INT);
                    watchAddrs.push({addr: addr, type: 'int'});
                    newInts++;
                }
            }
        } catch(e) {}
    }

    if (newInts > 0) {
        send({t: 'new_found', newInts: newInts, totalWatched: watchAddrs.length});
    }
}, 2000);

send({t: 'ready', msg: '持续补丁已激活. 进房间.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            watched: watchAddrs.length,
            timerFixes: timerFixes,
            running: timerRunning
        });
    },
    stop: function() {
        timerRunning = false;
        clearInterval(timer);
        clearInterval(scanTimer);
        return 'stopped';
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
    log(f'=== 持续补丁 === PID:{pid} ===')
    log(f'50125461(美丽梦想) → 50125711(紫色超赛)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'found':
                log(f'  找到: INT={p["ints"]}处 ASCII={p["asciis"]}处')
            elif t == 'init_patch':
                log(f'  初始替换: {p["count"]}处')
            elif t == 'timer_fix':
                log(f'  [定时器] 修复{p["fixed"]}处 (累计{p["total"]})')
            elif t == 'new_found':
                log(f'  [新扫描] 发现{p["newInts"]}处新INT (监控{p["totalWatched"]}处)')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            else:
                log(f'  {json.dumps(p)[:150]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('持续补丁运行中。进房间触发角色加载。')
    log('命令: status | stop | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'stop':
                script.exports_sync.stop()
                log('  定时器已停止')
    except (KeyboardInterrupt, EOFError):
        pass

    try:
        script.exports_sync.stop()
    except: pass
    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

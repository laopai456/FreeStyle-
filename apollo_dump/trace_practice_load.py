# trace_practice_load.py
# P0: 追踪练习场加载路径
#
# 目标：找出练习场阶段 AcquireSMD 的 ItemCode 来源
# 方法：
#   1. 监控所有安全的系统 DLL API（CreateFileA/W, ReadFile）
#   2. 记录练习场进房瞬间的文件访问序列
#   3. 对比房间阶段 vs 练习场阶段的差异
#   4. 推断练习场专用的数据入口
#
# 安全：只 hook 系统 DLL，不触游戏 .text
import sys
import os
import time
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'practice_load_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

function readUnicode(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i * 2).readU16();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

// 阶段追踪
var phase = 'INJECTED';
var phaseTime = 0;

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        phaseTime = Date.now();
        send({t: 'phase', from: old, to: p});
    }
}

// ==========================================
// 1. sprintf hook — 阶段检测 + ItemCode 记录
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var sprintfCount = 0;
var lastSprintfTime = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var ic = args[2].toInt32();
            sprintfCount++;
            lastSprintfTime = Date.now();

            var marker = '';
            if (ic === SRC_IC) marker = ' <== SRC';
            else if (ic === DST_IC) marker = ' <== DST';

            send({t: 'sprintf', n: sprintfCount, ic: ic, marker: marker, phase: phase});

            // 阶段推断：连续 sprintf 通常在房间加载
            if (sprintfCount <= 10) setPhase('ROOM_LOAD');
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 2. CreateFileA/W — 文件访问追踪
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var cfCount = 0;

// 关键文件模式
var patterns = [
    '50125',      // 目标 ItemCode
    '50122',      // 其他测试 ItemCode
    '.bml',       // BML 文件
    '.smd',       // SMD 网格
    'customize',  // 定制目录
    'res767',     // pak767 资源
    'res768',     // pak768 资源
    'character',  // 角色相关
    'motion'      // 动作相关
];

function matchPattern(s) {
    var s_lower = s.toLowerCase();
    for (var i = 0; i < patterns.length; i++) {
        if (s_lower.indexOf(patterns[i].toLowerCase()) >= 0) {
            return patterns[i];
        }
    }
    return null;
}

Interceptor.attach(kernel32.getExportByName('CreateFileA'), {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 512);
            var matched = matchPattern(path);
            if (matched) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, api: 'A', short: short, pattern: matched, phase: phase, full: path});
            }
        } catch(e) {}
    }
});

Interceptor.attach(kernel32.getExportByName('CreateFileW'), {
    onEnter: function(args) {
        try {
            var path = readUnicode(args[0], 256);
            var matched = matchPattern(path);
            if (matched) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, api: 'W', short: short, pattern: matched, phase: phase, full: path});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA/W hooks ready'});

// ==========================================
// 3. ReadFile — SMD/BML 数据读取追踪
// ==========================================
var rfCount = 0;

Interceptor.attach(kernel32.getExportByName('ReadFile'), {
    onEnter: function(args) {
        this.rbuf = args[1];
        this.rsize = args[2].toInt32();
        this.rbr = args[3];
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.rbr.readU32();
            if (bytesRead < 4) return;

            // 检查是否是 SSKF (SMD) 或 BML 数据
            var magic = this.rbuf.readU32();
            var magicStr = '';
            if (magic === 0x464B5353) { // 'SSKF'
                rfCount++;
                send({t: 'read', n: rfCount, type: 'SMD', bytes: bytesRead, phase: phase});
            } else if (bytesRead > 4) {
                // BML 是 XOR 0xFF 编码的 XML，检查特征
                var b0 = this.rbuf.readU8();
                var b1 = this.rbuf.add(1).readU8();
                // XOR 后的 '<?xml' = 0xFF^0x3C, 0xFF^0x3F = 0xC3, 0xC0
                if (b0 === 0xC3 && b1 === 0xC0) {
                    rfCount++;
                    send({t: 'read', n: rfCount, type: 'BML', bytes: bytesRead, phase: phase});
                }
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'ReadFile hook ready'});

// ==========================================
// 4. 内存扫描 — 定期检查 ItemCode 地址
// ==========================================
var knownAddresses = [];
var lastValues = {};

function scanItemCode() {
    var pattern = SRC_IC.toString(16);
    while (pattern.length < 8) pattern = '0' + pattern;
    // 小端序: "61 54 12 50"
    var bytes = [];
    for (var b = 0; b < 4; b++) {
        var byteStr = pattern.substr(6 - b * 2, 2);
        bytes.push(byteStr);
    }
    var searchPattern = bytes.join(' ');

    var newAddrs = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 0x100 || r.size > 0x1000000) continue;
        try {
            var matches = Memory.scanSync(r.base, r.size, searchPattern);
            for (var j = 0; j < matches.length; j++) {
                var addr = matches[j].address;
                var key = hexAddr(addr);
                if (knownAddresses.indexOf(key) < 0) {
                    knownAddresses.push(key);
                    newAddrs.push(key);
                }
            }
        } catch(e) {}
    }
    return newAddrs;
}

// ==========================================
// 5. 静默期检测 — 练习场阶段特征
// ==========================================
var silenceTimer = setInterval(function() {
    var now = Date.now();
    var silenceMs = now - lastSprintfTime;

    // 如果超过 5 秒没有 sprintf，且之前有加载过，说明进入练习场
    if (silenceMs > 5000 && sprintfCount > 0 && phase !== 'PRACTICE') {
        setPhase('PRACTICE');

        // 触发内存扫描
        var newAddrs = scanItemCode();
        if (newAddrs.length > 0) {
            send({t: 'scan', newAddrs: newAddrs, phase: phase});
        }
    }
}, 1000);
send({t: 'step', msg: 'silence detector started (5s threshold)'});

// ==========================================
// RPC
// ==========================================
rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            fileCount: cfCount,
            readCount: rfCount,
            knownAddrs: knownAddresses.length
        });
    },
    scan: function() {
        var newAddrs = scanItemCode();
        return JSON.stringify({newAddrs: newAddrs, total: knownAddresses.length});
    },
    setPhase: function(p) {
        setPhase(p);
        return phase;
    }
};

send({t: 'ready', msg: 'Practice load tracer ready'});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Practice Load Tracer === PID:{pid} ===')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
    log(f'目标: 追踪练习场加载路径')
    log(f'日志: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_TEMPLATE
        .replace('__SRC_IC__', str(SRC_IC))
        .replace('__DST_IC__', str(DST_IC))
    )

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'step':
                log(f'  [setup] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'phase':
                log('')
                log(f'[PHASE] {p["from"]} -> {p["to"]}')
                log('')
            elif t == 'sprintf':
                log(f'[sprintf] #{p["n"]} ic={p["ic"]}{p.get("marker","")} phase={p["phase"]}')
            elif t == 'file':
                log(f'[file] #{p["n"]} {p["short"]} ({p["api"]}, pattern={p["pattern"]}) phase={p["phase"]}')
                if p.get('full'):
                    log(f'        full: {p["full"]}')
            elif t == 'read':
                log(f'[read] #{p["n"]} type={p["type"]} bytes={p["bytes"]} phase={p["phase"]}')
            elif t == 'scan':
                log(f'[scan] new addresses: {p["newAddrs"]} phase={p["phase"]}')
            elif t == 'error':
                log(f'  [error] {p.get("msg", p)}')
            else:
                log(f'  [{t}] {str(p)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description","")} line={msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('测试流程:')
    log('1. 进房间 → 观察 sprintf 和文件访问')
    log('2. 进练习场 → 关键：看有没有新的文件访问')
    log('3. 观察 phase 变化（5秒无 sprintf 自动切换到 PRACTICE）')
    log('')
    log('命令: status | scan | phase <name> | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
            elif cmd == 'scan':
                result = script.exports_sync.scan()
                log(f'  {result}')
            elif cmd.startswith('phase '):
                new_phase = cmd.split(' ', 1)[1]
                result = script.exports_sync.set_phase(new_phase)
                log(f'  phase -> {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()
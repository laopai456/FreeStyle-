# hook_practice_debug.py
# 针对练习场阶段的调试脚本
# 目标：找出练习场阶段角色加载的 ItemCode 来源
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'practice_debug_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

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

var base = ptr('0x400000');
var phase = 'INJECTED';
var sprintfCount = 0;
var lastItemCodes = [];

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
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

// ==========================================
// 1. sprintf hook — 记录所有 ItemCode，不做替换
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 80);
            if (fmt.indexOf('customize') >= 0 && fmt.indexOf('item') >= 0) {
                var itemCode = args[2].toInt32();
                sprintfCount++;
                lastItemCodes.push(itemCode);
                if (lastItemCodes.length > 10) lastItemCodes.shift();

                var retAddr = this.returnAddress;
                var retMod = '?';
                try {
                    var m = Process.findModuleByAddress(retAddr);
                    if (m) retMod = m.name + '+' + hexAddr(retAddr.sub(m.base));
                } catch(e) {}

                send({t: 'sprintf', n: sprintfCount, ic: itemCode, fmt: fmt, ret: hexAddr(retAddr), ret_mod: retMod, phase: phase});

                // 阶段推断
                if (sprintfCount === 1) setPhase('ROOM_LOAD');
                else if (sprintfCount === 2) setPhase('PRACTICE_LOAD');
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'sprintf hook (monitor only)'});

// ==========================================
// 2. LoadItemFile hook — 禁用，会触发 Apollo
// ==========================================
// var lifAddr = base.add(0x1ACE1C0);
// var lifCount = 0;
// Interceptor.attach(lifAddr, { ... });
send({t: 'step', msg: 'LoadItemFile hook DISABLED (would trigger Apollo)'});

// ==========================================
// 3. 监控可能的 ItemCode 来源
// ==========================================

// 3.1 监控内存中 ItemCode 的读取点
// 基于之前的分析，ItemCode 可能从以下位置读取：
// - 配置表
// - 角色对象字段
// - 网络包

// 监控特定内存地址的读取（如果已知）
// var itemCodePtr = ptr('0x02A43CA4');  // 示例地址，需要确认

// ==========================================
// 4. CreateFileA/W — 监控文件访问
// ==========================================
var cfCount = 0;
var kernel32 = Process.getModuleByName('kernel32.dll');

// CreateFileA
var CreateFileA = kernel32.getExportByName('CreateFileA');
Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 512);
            if (path.indexOf('50125') >= 0 || path.indexOf('50122') >= 0 || path.indexOf('.bml') >= 0) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, short: short, api: 'A', phase: phase});
            }
        } catch(e) {}
    }
});

// CreateFileW
var CreateFileW = kernel32.getExportByName('CreateFileW');
Interceptor.attach(CreateFileW, {
    onEnter: function(args) {
        try {
            var pathBuf = args[0];
            var path = '';
            for (var i = 0; i < 256; i++) {
                var ch = pathBuf.add(i * 2).readU16();
                if (ch === 0) break;
                path += String.fromCharCode(ch);
            }
            if (path.indexOf('50125') >= 0 || path.indexOf('50122') >= 0 || path.indexOf('.bml') >= 0) {
                cfCount++;
                var short = path.replace(/\\/g, '/').split('/').pop();
                send({t: 'file', n: cfCount, short: short, api: 'W', phase: phase});
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA/W hooks'});

// ==========================================
// 5. 状态查询
// ==========================================
rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            lifCount: lifCount,
            lastItemCodes: lastItemCodes
        });
    },
    phase: function() { return phase; }
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
    log('=== Practice Debug Script ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
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
                log(f'  [ready] SRC={p["src"]} DST={p["dst"]}')

            elif t == 'phase':
                log(f'')
                log(f'[phase] {p["from"]} -> {p["to"]}')
                log(f'')

            elif t == 'sprintf':
                ic = p['ic']
                marker = ''
                if ic == SRC_IC:
                    marker = ' <== SRC_IC'
                elif ic == DST_IC:
                    marker = ' <== DST_IC'
                log(f'[sprintf] #{p["n"]} ic={ic}{marker} fmt="{p["fmt"]}" ret={p["ret"]} ({p["ret_mod"]}) phase={p["phase"]}')

            elif t == 'LoadItemFile':
                ic = p['ic']
                marker = ''
                if ic == SRC_IC:
                    marker = ' <== SRC_IC'
                elif ic == DST_IC:
                    marker = ' <== DST_IC'
                log(f'[LoadItemFile] #{p["n"]} ic={ic}{marker} fname="{p["fname"]}" phase={p["phase"]}')

            elif t == 'file':
                log(f'[file] {p["short"]} ({p["api"]}) phase={p["phase"]}')

            else:
                log(f'  [{t}] {str(p)[:200]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")} line={msg.get("lineNumber", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Instructions:')
    log('  1. Enter room -> observe sprintf/LoadItemFile')
    log('  2. Enter practice -> observe what ItemCode is used')
    log('  3. Exit practice -> observe changes')
    log('')
    log('Commands: status | phase | quit')
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
    print('Done.')

if __name__ == '__main__':
    main()
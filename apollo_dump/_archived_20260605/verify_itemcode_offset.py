# verify_itemcode_offset.py
# 验证静态逆向发现的精确偏移：[outer+0x164]+0x7DC = ItemCode
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'verify_offset_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var sprintfCount = 0;
var phase = 'INJECTED';
var outerPtr = null;       // [ebp-0x478c]
var subObjPtr = null;      // [outer+0x164]
var lastItemCode = null;   // [subObj+0x7DC]

function setPhase(p) {
    if (phase !== p) {
        var old = phase;
        phase = p;
        send({t: 'phase', from: old, to: p});
    }
}

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

// ==========================================
// sprintf hook — 捕获 outer 指针
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

            var ebp = this.context.ebp;

            // 尝试读取 outer = [ebp-0x478c]
            try {
                outerPtr = ebp.sub(0x478c).readPointer();
                // sub_obj = [outer+0x164]
                subObjPtr = outerPtr.add(0x164).readPointer();
                // ItemCode = [sub_obj+0x7DC]
                var itemCodeFromOffset = subObjPtr.add(0x7DC).readU32();

                var marker = '';
                if (ic === SRC_IC) marker = ' <== SRC_IC';
                else if (ic === DST_IC) marker = ' <== DST_IC';

                send({
                    t: 'sprintf',
                    n: sprintfCount,
                    ic: ic,
                    marker: marker,
                    phase: phase,
                    outer: hexAddr(outerPtr),
                    subObj: hexAddr(subObjPtr),
                    offset7DC: itemCodeFromOffset,
                    match: itemCodeFromOffset === ic
                });

                lastItemCode = itemCodeFromOffset;
            } catch(e) {
                send({t: 'sprintf', n: sprintfCount, ic: ic, phase: phase, error: e.toString()});
            }

            if (sprintfCount === 1) setPhase('ROOM_LOAD');
            else if (sprintfCount === 2) setPhase('PRACTICE_LOAD');

        } catch(e) {
            send({t: 'error', msg: e.toString()});
        }
    }
});
send({t: 'step', msg: 'sprintf hook ready'});

// ==========================================
// 定时监控精确偏移
// ==========================================
var monitorInterval = setInterval(function() {
    if (!subObjPtr) return;

    try {
        var currentIC = subObjPtr.add(0x7DC).readU32();
        if (lastItemCode !== currentIC) {
            send({
                t: 'change',
                phase: phase,
                outer: hexAddr(outerPtr),
                subObj: hexAddr(subObjPtr),
                old: lastItemCode,
                new: currentIC,
                isSRC: currentIC === SRC_IC,
                isDST: currentIC === DST_IC
            });
            lastItemCode = currentIC;
        }
    } catch(e) {}
}, 500);

send({t: 'step', msg: 'offset monitor started (500ms)'});

// ==========================================
// hook 0x173C601 — 练习场函数中读取 sub_obj
// 如果 itemCode = 0，修复为 DST_IC
// ==========================================
try {
    var practiceCallSite = base.add(0x173C601);
    Interceptor.attach(practiceCallSite, {
        onEnter: function(args) {
            try {
                // 这里是 call 0x1ee1f80 之后
                // 读取 outer = [ebp-0x478c]
                var ebp = this.context.ebp;
                var outer = ebp.sub(0x478c).readPointer();
                var subObj = outer.add(0x164).readPointer();
                var ic = subObj.add(0x7DC).readU32();

                var marker = '';
                var fixed = false;

                if (ic === SRC_IC) {
                    marker = ' <== SRC_IC (need fix)';
                    // 修复：写入 DST_IC
                    subObj.add(0x7DC).writeU32(DST_IC);
                    fixed = true;
                } else if (ic === DST_IC) {
                    marker = ' <== DST_IC (already correct)';
                } else if (ic === 0) {
                    marker = ' <== ZERO (fixing)';
                    // 修复：写入 DST_IC
                    subObj.add(0x7DC).writeU32(DST_IC);
                    fixed = true;
                }

                send({
                    t: 'practice',
                    phase: phase,
                    outer: hexAddr(outer),
                    subObj: hexAddr(subObj),
                    itemCode: ic,
                    marker: marker,
                    fixed: fixed,
                    newIC: fixed ? DST_IC : ic
                });
            } catch(e) {
                send({t: 'practice', error: e.toString()});
            }
        }
    });
    send({t: 'step', msg: 'practice function hook @ 0x173C601 (with auto-fix)'});
} catch(e) {
    send({t: 'step', msg: 'practice hook failed: ' + e});
}

send({t: 'ready', src: SRC_IC, dst: DST_IC});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            phase: phase,
            sprintfCount: sprintfCount,
            outer: outerPtr ? hexAddr(outerPtr) : null,
            subObj: subObjPtr ? hexAddr(subObjPtr) : null,
            currentIC: lastItemCode
        });
    }
};
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
    log('=== Verify ItemCode Offset ===')
    log(f'PID: {pid}')
    log(f'SRC: {SRC_IC}  DST: {DST_IC}')
    log(f'Target: [outer+0x164]+0x7DC')
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
                match = 'MATCH' if p.get('match') else 'MISMATCH'
                marker = p.get('marker', '')
                log(f'[sprintf] #{p["n"]} ic={p["ic"]}{marker} phase={p["phase"]}')
                if 'outer' in p:
                    log(f'    outer={p["outer"]} subObj={p["subObj"]} +0x7DC={p["offset7DC"]} ({match})')
                elif 'error' in p:
                    log(f'    error: {p["error"]}')

            elif t == 'change':
                marker = ''
                if p.get('isSRC'): marker = ' <== SRC_IC'
                elif p.get('isDST'): marker = ' <== DST_IC'
                log(f'')
                log(f'=== OFFSET CHANGE @ {p["phase"]} ===')
                log(f'  [subObj+0x7DC]: {p["old"]} -> {p["new"]}{marker}')
                log(f'  outer={p["outer"]} subObj={p["subObj"]}')
                log('')

            elif t == 'practice':
                marker = p.get('marker', '')
                fixed = p.get('fixed', False)
                log(f'')
                if fixed:
                    log(f'[practice hook] itemCode={p["itemCode"]}{marker} -> FIXED to {p["newIC"]}')
                else:
                    log(f'[practice hook] itemCode={p["itemCode"]}{marker}')
                if 'outer' in p:
                    log(f'    outer={p["outer"]} subObj={p["subObj"]}')

            elif t == 'error':
                log(f'  [error] {p["msg"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Instructions:')
    log('  1. Enter room -> check if offset matches sprintf ic')
    log('  2. Enter practice -> watch for OFFSET CHANGE')
    log('  3. Exit practice -> watch for OFFSET CHANGE')
    log('')
    log('Commands: status | quit')
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
    print('Done.')

if __name__ == '__main__':
    main()
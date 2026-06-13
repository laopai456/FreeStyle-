# monitor_effect.py
# 发型替换 + 特效内存地址监控
# 用 50122931(粉色另类半扎发型, effect=1479) 替换 50125461(美丽梦想发型, 无特效)
# 同时全堆扫描特效编号 1479，观察特效数据的内存分布
#
# 用法:
#   python monitor_effect.py                  # 默认监控
#   python monitor_effect.py <src> <dst>      # 自定义 ItemCode

import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

# 默认: 美丽梦想发型(无特效) -> 粉色另类半扎发型(特效1479)
SRC_IC = 50125461
DST_IC = 50122931
EFFECT_ID = 1479  # 50122931 的特效编号

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'effect_monitor_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def int_to_le_hex(val):
    """整数转小端 hex pattern, 如 1479 -> 'c7 05 00 00'"""
    return ' '.join(f'{(val >> (i*8)) & 0xFF:02x}' for i in range(4))

def create_js(src_ic, dst_ic, effect_id):
    src_str = str(src_ic)
    dst_str = str(dst_ic)
    effect_hex = int_to_le_hex(effect_id)

    return r"""
'use strict';

var SRC_IC = """ + str(src_ic) + """;
var DST_IC = """ + str(dst_ic) + """;
var EFFECT_ID = """ + str(effect_id) + """;
var SRC_STR = '""" + src_str + r"""';
var DST_STR = '""" + dst_str + r"""';
var EFFECT_HEX = '""" + effect_hex + r"""';

var patchCount = 0;
var dwordScanDone = false;
var effectScanDone = false;

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function replaceStr(buf, src, dst) {
    var content = readAscii(buf, 120);
    var idx = content.indexOf(src);
    if (idx < 0) return false;
    var replaced = content.substring(0, idx) + dst + content.substring(idx + src.length);
    for (var i = 0; i < replaced.length; i++) buf.add(i).writeU8(replaced.charCodeAt(i));
    buf.add(replaced.length).writeU8(0);
    return true;
}

function intToLeHex(val) {
    var buf = Memory.alloc(4);
    buf.writeU32(val);
    var hex = '';
    for (var i = 0; i < 4; i++) hex += ('0' + buf.add(i).readU8().toString(16)).slice(-2) + ' ';
    return hex.trim();
}

function autoReplaceEbp(ebp) {
    var count = 0;
    for (var off = -0x300; off <= 0x300; off += 4) {
        try {
            if (ebp.add(off).readU32() === SRC_IC) {
                ebp.add(off).writeU32(DST_IC);
                count++;
            }
        } catch(e){}
    }
    return count;
}

function replaceAllDwords() {
    var ranges = Process.enumerateRanges('rw-');
    var count = 0;
    var srcHex = intToLeHex(SRC_IC);
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, srcHex);
            for (var j = 0; j < found.length; j++) {
                try { found[j].address.writeU32(DST_IC); count++; } catch(e){}
            }
        } catch(e){}
    }
    return count;
}

// ==========================================
// 特效编号内存扫描
// ==========================================
function scanEffect() {
    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    var effectHex = intToLeHex(EFFECT_ID);

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, effectHex);
            for (var j = 0; j < found.length; j++) {
                try {
                    // 读取周围上下文: 前16字节 + 后16字节
                    var addr = found[j].address;
                    var ctx_before = [];
                    var ctx_after = [];
                    for (var k = -4; k < 0; k++) {
                        try { ctx_before.push(addr.add(k*4).readU32()); } catch(e) { ctx_before.push(-1); }
                    }
                    for (var k = 1; k <= 4; k++) {
                        try { ctx_after.push(addr.add(k*4).readU32()); } catch(e) { ctx_after.push(-1); }
                    }
                    hits.push({
                        addr: addr.toString(),
                        before: ctx_before,
                        after: ctx_after
                    });
                } catch(e){}
            }
        } catch(e){}
    }

    send({t: 'effect_scan', effect: EFFECT_ID, count: hits.length, hits: hits.slice(0, 50)});
    return hits.length;
}

// 扫描特效编号的字符串形式 "1479"
function scanEffectString() {
    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    var effectStr = EFFECT_ID.toString();
    var pattern = '';
    for (var i = 0; i < effectStr.length; i++) {
        pattern += ('0' + effectStr.charCodeAt(i).toString(16)).slice(-2) + ' ';
    }

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, pattern.trim());
            for (var j = 0; j < found.length; j++) {
                try {
                    var addr = found[j].address;
                    // 读前后上下文
                    var ctx = readAscii(addr.sub(16), 80);
                    hits.push({ addr: addr.toString(), context: ctx });
                } catch(e){}
            }
        } catch(e){}
    }

    send({t: 'effect_str_scan', effect_str: effectStr, count: hits.length, hits: hits.slice(0, 30)});
    return hits.length;
}

// ==========================================
// sprintf hook — 替换 + 触发扫描
// ==========================================
var msvcr = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = null;
var strcpyAddr = null;
var exports = msvcr.enumerateExports();
for (var i = 0; i < exports.length; i++) {
    if (exports[i].name === 'sprintf') sprintfAddr = exports[i].address;
    if (exports[i].name === 'strcpy') strcpyAddr = exports[i].address;
}

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();

            // 收集: 打印所有 sprintf 的 ItemCode
            send({t:'sprintf_all', ic: itemCode, n: patchCount+1});

            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var ebpHits = autoReplaceEbp(this.context.ebp);
                patchCount++;
                send({t:'sprintf_replace', n: patchCount, ebp: ebpHits});

                // 首次触发: DWORD 扫描 + 特效扫描
                if (!dwordScanDone) {
                    send({t:'scanning_dword'});
                    var dwordCount = replaceAllDwords();
                    send({t:'dword_scan', count: dwordCount});
                    dwordScanDone = true;
                }

                if (!effectScanDone) {
                    send({t:'scanning_effect'});
                    scanEffect();
                    scanEffectString();
                    effectScanDone = true;
                }
            }
        } catch(e) {}
    }
});

// ==========================================
// strcpy hook — 练习场路径替换 + 重新扫描特效
// ==========================================
if (strcpyAddr) {
    Interceptor.attach(strcpyAddr, {
        onEnter: function(args) {
            try {
                var src = readAscii(args[1], 120);
                if (src.indexOf('customize') < 0 || src.indexOf(SRC_STR) < 0) return;

                // 练习场: 重新 DWORD 扫描 + 特效扫描
                send({t:'scanning_practice'});
                replaceAllDwords();
                replaceStr(args[1], SRC_STR, DST_STR);
                this._do = true;
                this._dst = args[0];
                patchCount++;

                // 练习场重新扫描特效
                send({t:'scanning_effect_practice'});
                scanEffect();
                scanEffectString();
            } catch(e) {}
        },
        onLeave: function(retval) {
            if (!this._do) return;
            replaceStr(this._dst, SRC_STR, DST_STR);
        }
    });
}

// ==========================================
// 定时轮询: 监控特效地址变化
// ==========================================
var effectAddrs = [];  // [{addr, val}]
var pollInterval = setInterval(function() {
    if (effectAddrs.length === 0) return;
    var changes = [];
    for (var i = 0; i < effectAddrs.length; i++) {
        try {
            var val = effectAddrs[i].addr.readU32();
            if (val !== effectAddrs[i].val) {
                changes.push({
                    addr: effectAddrs[i].addr.toString(),
                    old: effectAddrs[i].val,
                    new: val
                });
                effectAddrs[i].val = val;
            }
        } catch(e) {
            changes.push({
                addr: effectAddrs[i].addr.toString(),
                old: effectAddrs[i].val,
                new: 'FREED'
            });
        }
    }
    if (changes.length > 0) {
        send({t: 'effect_change', changes: changes});
    }
}, 1000);

// RPC: 手动触发特效扫描
rpc.exports = {
    scanEffect: function() {
        return scanEffect();
    },
    scanEffectString: function() {
        return scanEffectString();
    },
    addEffectWatch: function(addrStr) {
        try {
            var addr = ptr(addrStr);
            var val = addr.readU32();
            effectAddrs.push({addr: addr, val: val});
            return 'watching ' + addrStr + ' = ' + val;
        } catch(e) {
            return 'error: ' + e;
        }
    },
    count: function() { return patchCount; }
};

send({t: 'ready', src: SRC_IC, dst: DST_IC, effect: EFFECT_ID});
"""

def main():
    global SRC_IC, DST_IC, EFFECT_ID, LOG_F

    if len(sys.argv) >= 3:
        SRC_IC = int(sys.argv[1])
        DST_IC = int(sys.argv[2])
        # 从 itemshop.json 查 effect
        itemshop_path = os.path.join(SCRIPT_DIR, '..', '2.0', 'data', 'itemshop.json')
        if os.path.exists(itemshop_path):
            with open(itemshop_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            item = data.get(str(DST_IC), {})
            eff = item.get('effect', '0')
            try:
                EFFECT_ID = int(eff)
            except ValueError:
                EFFECT_ID = 0
                log(f'WARNING: effect "{eff}" is not a number, using 0')

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')

    log('=== Effect Memory Monitor ===')
    log(f'SRC: {SRC_IC} (美丽梦想发型, 无特效)')
    log(f'DST: {DST_IC} (粉色另类半扎发型, 特效={EFFECT_ID})')
    log(f'Effect ID hex: {int_to_le_hex(EFFECT_ID)}')
    log(f'Log: {LOG_FILE}')
    log('')

    pid = find_pid()
    if not pid:
        log('FreeStyle.exe not running!')
        return

    log(f'PID: {pid}')

    session = frida.attach(pid)
    script = session.create_script(create_js(SRC_IC, DST_IC, EFFECT_ID))

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'ready':
                log(f'  [ready] SRC={p["src"]} DST={p["dst"]} EFFECT={p["effect"]}')

            elif t == 'sprintf_all':
                ic = p['ic']
                marker = ''
                if ic == SRC_IC: marker = ' <== SRC (will replace)'
                elif ic == DST_IC: marker = ' <== DST'
                log(f'  [sprintf] #{p["n"]} ItemCode={ic}{marker}')

            elif t == 'sprintf_replace':
                log(f'  [REPLACE] sprintf #{p["n"]} ebp hits={p["ebp"]}')

            elif t == 'scanning_dword':
                log('  [scan] DWORD scan (behind loading screen)...')

            elif t == 'dword_scan':
                log(f'  [scan] DWORD replaced: {p["count"]}')

            elif t == 'scanning_effect':
                log('  [scan] Effect scan (first time)...')

            elif t == 'scanning_effect_practice':
                log('  [scan] Effect scan (practice range)...')

            elif t == 'effect_scan':
                count = p['count']
                effect = p['effect']
                log(f'')
                log(f'=== EFFECT SCAN (int {effect}) ===')
                log(f'  Found {count} occurrences of {effect} (0x{effect:X}) in heap')
                hits = p.get('hits', [])
                if hits:
                    # 按地址前缀分组
                    regions = {}
                    for h in hits:
                        prefix = h['addr'][:8]
                        regions.setdefault(prefix, []).append(h)
                    log(f'  Distribution:')
                    for prefix, items in sorted(regions.items()):
                        log(f'    {prefix}xxxxxx: {len(items)} hits')
                    log(f'')
                    log(f'  Top hits with context (addr | -16B | VALUE | +16B):')
                    for h in hits[:20]:
                        before = ' '.join(f'{v:08X}' for v in h['before'])
                        after = ' '.join(f'{v:08X}' for v in h['after'])
                        log(f'    {h["addr"]}: [{before}] {effect:08X} [{after}]')
                log('')

            elif t == 'effect_str_scan':
                count = p['count']
                effect_str = p['effect_str']
                log(f'')
                log(f'=== EFFECT STRING SCAN ("{effect_str}") ===')
                log(f'  Found {count} occurrences of string "{effect_str}" in heap')
                hits = p.get('hits', [])
                if hits:
                    regions = {}
                    for h in hits:
                        prefix = h['addr'][:8]
                        regions.setdefault(prefix, []).append(h)
                    log(f'  Distribution:')
                    for prefix, items in sorted(regions.items()):
                        log(f'    {prefix}xxxxxx: {len(items)} hits')
                    log(f'')
                    log(f'  Top hits with context:')
                    for h in hits[:15]:
                        log(f'    {h["addr"]}: ...{h["context"]}...')
                log('')

            elif t == 'effect_change':
                log(f'')
                log(f'=== EFFECT VALUE CHANGED ===')
                for c in p['changes']:
                    old_s = f'{c["old"]}' if isinstance(c["old"], int) else str(c["old"])
                    new_s = f'{c["new"]}' if isinstance(c["new"], int) else str(c["new"])
                    log(f'  {c["addr"]}: {old_s} -> {new_s}')
                log('')

            elif t == 'scanning_practice':
                log('  [practice] DWORD + Effect re-scan...')

            elif t == 'strcpy':
                log(f'  [practice] strcpy #{p["n"]}')

        elif msg['type'] == 'error':
            log(f'  [JS error] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('Instructions:')
    log('  1. Enter room -> observe sprintf + effect scan results')
    log('  2. Watch for effect memory addresses')
    log('  3. Enter practice -> watch for effect re-scan')
    log('')
    log('Commands: scan | scanstr | watch <addr> | count | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip()
            if not cmd:
                continue
            parts = cmd.lower().split()

            if parts[0] in ('quit', 'q', 'exit'):
                break
            elif parts[0] == 'scan':
                count = script.exports_sync.scan_effect()
                log(f'  Effect int scan: {count} hits')
            elif parts[0] == 'scanstr':
                count = script.exports_sync.scan_effect_string()
                log(f'  Effect string scan: {count} hits')
            elif parts[0] == 'watch' and len(parts) >= 2:
                result = script.exports_sync.add_effect_watch(parts[1])
                log(f'  {result}')
            elif parts[0] == 'count':
                log(f'  patches: {script.exports_sync.count()}')
    except (KeyboardInterrupt, EOFError):
        import time as _t
        log('(stdin closed, daemon mode)')
        while True:
            _t.sleep(1)

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    log('Done.')

if __name__ == '__main__':
    main()

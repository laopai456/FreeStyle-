# scan_effect_now.py
# 立即扫描特效编号在内存中的位置，不需要替换触发
# 用法: python scan_effect_now.py [effect_id]

import sys, os, time, frida
sys.stdout.reconfigure(encoding='utf-8')

EFFECT_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1479
ITEM_CODE = 50122931  # 粉色另类半扎发型

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'effect_scan_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = open(LOG_FILE, 'w', encoding='utf-8')

def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    LOG_F.write(line + '\n')
    LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def int_to_le_hex(val):
    return ' '.join(f'{(val >> (i*8)) & 0xFF:02x}' for i in range(4))

def create_js(effect_id, item_code):
    return r"""
'use strict';

var EFFECT_ID = """ + str(effect_id) + """;
var ITEM_CODE = """ + str(item_code) + """;

function intToLeHex(val) {
    var buf = Memory.alloc(4);
    buf.writeU32(val);
    var hex = '';
    for (var i = 0; i < 4; i++) hex += ('0' + buf.add(i).readU8().toString(16)).slice(-2) + ' ';
    return hex.trim();
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

// 扫描 int 值，带丰富上下文
function scanInt(val, label) {
    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    var hex = intToLeHex(val);

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, hex);
            for (var j = 0; j < found.length; j++) {
                try {
                    var addr = found[j].address;
                    // 读取前后各 8 个 DWORD (32 字节)
                    var before = [];
                    var after = [];
                    for (var k = -8; k < 0; k++) {
                        try { before.push(addr.add(k*4).readU32()); } catch(e) { before.push(null); }
                    }
                    for (var k = 1; k <= 8; k++) {
                        try { after.push(addr.add(k*4).readU32()); } catch(e) { after.push(null); }
                    }
                    hits.push({
                        addr: addr.toString(),
                        before: before,
                        after: after
                    });
                } catch(e){}
            }
        } catch(e){}
    }

    send({t: 'int_scan', label: label, val: val, count: hits.length, hits: hits.slice(0, 80)});
    return hits.length;
}

// 扫描字符串形式
function scanString(str, label) {
    var ranges = Process.enumerateRanges('rw-');
    var hits = [];
    var pattern = '';
    for (var i = 0; i < str.length; i++) {
        pattern += ('0' + str.charCodeAt(i).toString(16)).slice(-2) + ' ';
    }

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, pattern.trim());
            for (var j = 0; j < found.length; j++) {
                try {
                    var addr = found[j].address;
                    var ctx = readAscii(addr.sub(32), 128);
                    hits.push({ addr: addr.toString(), context: ctx });
                } catch(e){}
            }
        } catch(e){}
    }

    send({t: 'str_scan', label: label, str: str, count: hits.length, hits: hits.slice(0, 50)});
    return hits.length;
}

// 关键：同时扫描 ItemCode 和 Effect，然后找"邻近"的命中
function scanProximity() {
    var ranges = Process.enumerateRanges('rw-');
    var itemHits = [];
    var effectHits = [];
    var itemHex = intToLeHex(ITEM_CODE);
    var effectHex = intToLeHex(EFFECT_ID);

    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var items = Memory.scanSync(r.base, r.size, itemHex);
            for (var j = 0; j < items.length; j++) itemHits.push(items[j].address);

            var effects = Memory.scanSync(r.base, r.size, effectHex);
            for (var j = 0; j < effects.length; j++) effectHits.push(effects[j].address);
        } catch(e){}
    }

    // 找 ItemCode 和 Effect 在同一页内(距离 < 0x200)的
    var nearby = [];
    for (var i = 0; i < itemHits.length; i++) {
        for (var j = 0; j < effectHits.length; j++) {
            var diff = itemHits[i].sub(effectHits[j]).toInt32();
            var absDiff = diff < 0 ? -diff : diff;
            if (absDiff < 0x200) {
                // 读 ItemCode 周围的完整上下文
                var base = itemHits[i].sub(0x40);
                var ctx = [];
                for (var k = 0; k < 0x80; k += 4) {
                    try { ctx.push(base.add(k).readU32()); } catch(e) { ctx.push(null); }
                }
                nearby.push({
                    itemAddr: itemHits[i].toString(),
                    effectAddr: effectHits[j].toString(),
                    offset: diff,
                    context: ctx
                });
            }
        }
    }

    send({
        t: 'proximity',
        itemCount: itemHits.length,
        effectCount: effectHits.length,
        nearby: nearby.slice(0, 30)
    });
}

// 立即执行扫描
send({t: 'start', effect: EFFECT_ID, item: ITEM_CODE});
scanInt(EFFECT_ID, 'Effect int');
scanInt(ITEM_CODE, 'ItemCode int');
scanString(EFFECT_ID.toString(), 'Effect string');
scanString(ITEM_CODE.toString(), 'ItemCode string');
scanProximity();
send({t: 'done'});

"""

def fmt_u32(v):
    if v is None:
        return '________??'
    return f'{v:08X}'

def main():
    log(f'=== Effect Scan (immediate) ===')
    log(f'Effect ID: {EFFECT_ID} (0x{EFFECT_ID:X}) hex: {int_to_le_hex(EFFECT_ID)}')
    log(f'Item Code: {ITEM_CODE} (0x{ITEM_CODE:X}) hex: {int_to_le_hex(ITEM_CODE)}')
    log(f'Log: {LOG_FILE}')

    pid = find_pid()
    if not pid:
        log('FreeStyle.exe not found!')
        return
    log(f'PID: {pid}')

    session = frida.attach(pid)
    script = session.create_script(create_js(EFFECT_ID, ITEM_CODE))

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'start':
                log(f'Scanning...')

            elif t == 'int_scan':
                label = p['label']
                val = p['val']
                count = p['count']
                log(f'')
                log(f'=== {label} SCAN (int {val} / 0x{val:X}) ===')
                log(f'  Total hits: {count}')
                hits = p.get('hits', [])
                if hits:
                    # 按地址前缀分组
                    regions = {}
                    for h in hits:
                        prefix = h['addr'][:10]
                        regions.setdefault(prefix, []).append(h)
                    log(f'  Distribution by region:')
                    for prefix, items in sorted(regions.items()):
                        log(f'    {prefix}...: {len(items)} hits')
                    log(f'')
                    log(f'  Hits with context (-32B | VALUE | +32B):')
                    for h in hits[:30]:
                        before = ' '.join(fmt_u32(v) for v in h['before'][-4:])
                        after = ' '.join(fmt_u32(v) for v in h['after'][:4])
                        log(f'    {h["addr"]}: [{before}] {val:08X} [{after}]')
                log('')

            elif t == 'str_scan':
                label = p['label']
                s = p['str']
                count = p['count']
                log(f'')
                log(f'=== {label} SCAN (string "{s}") ===')
                log(f'  Total hits: {count}')
                hits = p.get('hits', [])
                if hits:
                    regions = {}
                    for h in hits:
                        prefix = h['addr'][:10]
                        regions.setdefault(prefix, []).append(h)
                    log(f'  Distribution:')
                    for prefix, items in sorted(regions.items()):
                        log(f'    {prefix}...: {len(items)} hits')
                    log(f'')
                    log(f'  Context:')
                    for h in hits[:20]:
                        log(f'    {h["addr"]}: ...{h["context"]}...')
                log('')

            elif t == 'proximity':
                ic = p['itemCount']
                ec = p['effectCount']
                nearby = p['nearby']
                log(f'')
                log(f'=== PROXIMITY ANALYSIS ===')
                log(f'  ItemCode {ITEM_CODE} hits: {ic}')
                log(f'  Effect {EFFECT_ID} hits: {ec}')
                log(f'  Nearby pairs (within 0x200): {len(nearby)}')
                if nearby:
                    for n in nearby:
                        offset = n['offset']
                        direction = '+' if offset >= 0 else ''
                        log(f'')
                        log(f'  --- ItemCode @ {n["itemAddr"]}  Effect @ {n["effectAddr"]}  offset={direction}{offset} (0x{abs(offset):X}) ---')
                        # 打印完整上下文
                        ctx = n['context']
                        base_addr = int(n['itemAddr'], 16) - 0x40
                        for idx in range(0, len(ctx), 4):
                            row_addr = base_addr + idx * 4
                            vals = ' '.join(fmt_u32(ctx[idx+k]) if idx+k < len(ctx) else '________??' for k in range(4))
                            # 标记 ItemCode 和 Effect 的位置
                            markers = []
                            for k in range(4):
                                actual_addr = row_addr + k * 4
                                if actual_addr == int(n['itemAddr'], 16):
                                    markers.append('<-- ItemCode')
                                elif actual_addr == int(n['effectAddr'], 16):
                                    markers.append('<-- Effect')
                            marker_str = ' '.join(markers)
                            log(f'    {row_addr:016X}: {vals}  {marker_str}')
                log('')

            elif t == 'done':
                log('Scan complete.')

        elif msg['type'] == 'error':
            log(f'[JS error] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    # 等扫描完成
    import time
    time.sleep(8)

    script.unload()
    session.detach()
    LOG_F.close()
    log(f'Log saved: {LOG_FILE}')

if __name__ == '__main__':
    main()
_EOF = LOG_F.close()

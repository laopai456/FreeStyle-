"""
hook_equip_scan2.py — 物品替换 Phase 1 v2: 多形式搜索
ItemCode在内存中可能是整数(0x02FCDA95)、ASCII字符串、或UTF-16
全部搜一遍

搜索目标:
  1. 整数 50125461 = 0x02FCDA95 (little-endian: 95 DA FC 02)
  2. ASCII "50125461"
  3. ASCII "i50125461" (BML文件名格式)
  4. UTF-16 "50125461" (Windows宽字符)
"""
import sys, os, time, json, struct
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = 50125461
DST = 50125711

LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_scan2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

# JS: 搜索多种形式
JS_CODE = r"""
'use strict';

var SRC_STR = '50125461';
var SRC_STR_I = 'i50125461';
// 整数 little-endian: 95 DA FC 02
var SRC_INT_HEX = '95 da fc 02';
// UTF-16LE "50125461": 35 00 30 00 31 00 32 00 35 00 34 00 36 00 31 00
var SRC_UTF16_HEX = '35 00 30 00 31 00 32 00 35 00 34 00 36 00 31 00';

var searches = [
    {name: 'INT_LE', pattern: SRC_INT_HEX, desc: '整数 0x02FCDA95 (LE)'},
    {name: 'ASCII', pattern: asciiToHex(SRC_STR), desc: 'ASCII "50125461"'},
    {name: 'ASCII_I', pattern: asciiToHex(SRC_STR_I), desc: 'ASCII "i50125461"'},
    {name: 'UTF16', pattern: SRC_UTF16_HEX, desc: 'UTF-16 "50125461"'},
];

function asciiToHex(s) {
    var hex = [];
    for (var i = 0; i < s.length; i++) {
        hex.push(('0' + s.charCodeAt(i).toString(16)).slice(-2));
    }
    return hex.join(' ');
}

var allResults = {};
var ranges = Process.enumerateRanges('r--');
// 过滤: 只保留堆/数据区, 跳过模块
var heapRanges = [];
for (var i = 0; i < ranges.length; i++) {
    var r = ranges[i];
    if (r.size < 4 || r.size > 200 * 1024 * 1024) continue;
    try {
        var mod = Process.findModuleByAddress(r.base);
        if (mod) continue;  // 跳过模块
    } catch(e) {}
    heapRanges.push(r);
}

send({t: 'info', msg: '堆内存区域: ' + heapRanges.length + ' 个'});

for (var si = 0; si < searches.length; si++) {
    var search = searches[si];
    var found = [];

    for (var ri = 0; ri < heapRanges.length; ri++) {
        var range = heapRanges[ri];
        try {
            var matches = Memory.scanSync(range.base, range.size, search.pattern);
            for (var mi = 0; mi < matches.length; mi++) {
                var addr = matches[mi].address;
                var ctx = readContext(addr);
                found.push({
                    addr: addr.toString(),
                    ctxHex: ctx.hex,
                    ctxStr: ctx.str,
                    nearby: ctx.nearby
                });
            }
        } catch(e) {}
    }

    allResults[search.name] = found;
    send({t: 'search', name: search.name, desc: search.desc, found: found.length});
}

// 也搜索模块的 .data/.rdata 段
send({t: 'info', msg: '搜索模块数据段...'});
var fsMod = Process.getModuleByName('FreeStyle.exe');
var modRanges = Process.enumerateRanges('r--');
for (var si = 0; si < searches.length; si++) {
    var search = searches[si];
    var modFound = [];
    for (var ri = 0; ri < modRanges.length; ri++) {
        var range = modRanges[ri];
        // 只搜索模块范围内的
        var rStart = range.base;
        var rEnd = range.base.add(range.size);
        var mStart = fsMod.base;
        var mEnd = fsMod.base.add(fsMod.size);
        if (rStart.compare(mEnd) >= 0 || rEnd.compare(mStart) <= 0) continue;
        try {
            var matches = Memory.scanSync(range.base, range.size, search.pattern);
            for (var mi = 0; mi < matches.length; mi++) {
                var addr = matches[mi].address;
                var rva = addr.sub(fsMod.base);
                modFound.push({
                    addr: addr.toString(),
                    rva: '0x' + rva.toString(16),
                    ctxStr: tryReadString(addr.sub(16), 80)
                });
            }
        } catch(e) {}
    }
    if (modFound.length > 0) {
        send({t: 'mod_search', name: search.name, found: modFound.length, results: modFound});
    }
}

send({t: 'done', results: allResults});

function readContext(addr) {
    var hex = '', str = '', nearby = [];
    try {
        var buf = addr.sub(16).readByteArray(80);
        var bytes = new Uint8Array(buf);
        for (var i = 0; i < bytes.length; i++) {
            hex += ('0' + bytes[i].toString(16)).slice(-2) + ' ';
        }
        // 尝试读字符串
        for (var start = 0; start < 60; start += 4) {
            var s = tryReadString(addr.sub(16).add(start), 40);
            if (s && s.length > 3) nearby.push({off: start - 16, str: s});
        }
    } catch(e) {}
    return {hex: hex, str: str, nearby: nearby};
}

function tryReadString(addr, maxLen) {
    try {
        return addr.readAnsiString(maxLen);
    } catch(e) { return ''; }
}
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Phase 1 v2: 多形式搜索 === PID:{pid} ===')
    log(f'目标: {SRC} (0x{SRC:08X}) → {DST} (0x{DST:08X})')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    all_results = {}

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'info':
                log(f'  {p.get("msg","")}')
            elif t == 'search':
                name = p.get('name','')
                desc = p.get('desc','')
                count = p.get('found', 0)
                log(f'  [{name}] {desc}: {count} 处')
            elif t == 'mod_search':
                name = p.get('name','')
                count = p.get('found', 0)
                results = p.get('results', [])
                log(f'  [模块.{name}] {count} 处:')
                for r in results[:10]:
                    log(f'    {r["addr"]} RVA={r.get("rva","")} ctx="{r.get("ctxStr","")[:60]}"')
            elif t == 'done':
                results = p.get('results', {})
                log('')
                log('=== 汇总 ===')
                for name, hits in results.items():
                    log(f'  {name}: {len(hits)} 处')
                    for i, h in enumerate(hits[:5]):
                        log(f'    #{i+1} {h["addr"]}')
                        for nb in h.get('nearby', [])[:3]:
                            log(f'      off={nb["off"]}: "{nb["str"]}"')
                    if len(hits) > 5:
                        log(f'    ... 还有 {len(hits)-5} 处')

                # 保存JSON
                json_path = LOG_FILE.replace('.txt', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                log(f'JSON: {json_path}')
            else:
                log(json.dumps(p, ensure_ascii=False)[:200])
        elif msg['type'] == 'error':
            log(f'[JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    try:
        input('按回车退出...')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('完成。')

if __name__ == '__main__':
    main()

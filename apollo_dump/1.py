# 1.py
# 统一发型替换 — 房间(sprintf) + 练习场(strcpy+DWORD scan)
# 零维护: ebp auto-scan, DWORD scan on first sprintf hit
#
# 用法:
#   python 1.py                    # 默认: 美丽梦想 -> 紫色超赛
#   python 1.py <itemcode>         # 指定目标发型
#   python 1.py list               # 列出可用发型
#   python 1.py <name keyword>     # 按名称搜索

import sys
import os
import json
import frida

sys.stdout.reconfigure(encoding='utf-8')

HAIR_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hair_styles.json')
SRC_IC = 50125461

def load_hair_table():
    if os.path.exists(HAIR_JSON):
        with open(HAIR_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['name']: (item['itemCode'], item['pak']) for item in data}
    return {}

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def list_hairs(hair_table):
    print('\n可用发型:')
    print('-' * 50)
    for name, (code, pak) in sorted(hair_table.items(), key=lambda x: x[1][0]):
        print(f'  {code}: {name} (pak{pak})')
    print('-' * 50)
    print(f'\n默认源发型: {SRC_IC} (美丽梦想发型)')
    print('\n用法: python 1.py <itemcode>')
    print('例如: python 1.py 50125711  # 紫色超赛')

def create_js(src_code, dst_code):
    src_str = str(src_code)
    dst_str = str(dst_code)
    return r"""
'use strict';

var SRC_IC = """ + str(src_code) + """;
var DST_IC = """ + str(dst_code) + """;
var SRC_STR = '""" + src_str + r"""';
var DST_STR = '""" + dst_str + r"""';

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

var srcLeBuf = Memory.alloc(4);
srcLeBuf.writeU32(SRC_IC);
var srcHex = '';
for (var i = 0; i < 4; i++) srcHex += ('0' + srcLeBuf.add(i).readU8().toString(16)).slice(-2) + ' ';

var msvcr = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = null;
var strcpyAddr = null;
var exports = msvcr.enumerateExports();
for (var i = 0; i < exports.length; i++) {
    if (exports[i].name === 'sprintf') sprintfAddr = exports[i].address;
    if (exports[i].name === 'strcpy') strcpyAddr = exports[i].address;
}

var patchCount = 0;
var dwordScanDone = false;

// Full memory DWORD replace - called once on first sprintf hit (during room loading)
function replaceAllDwords() {
    var ranges = Process.enumerateRanges('rw-');
    var count = 0;
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size > 200*1024*1024) continue;
        try {
            var found = Memory.scanSync(r.base, r.size, srcHex.trim());
            for (var j = 0; j < found.length; j++) {
                try { found[j].address.writeU32(DST_IC); count++; } catch(e){}
            }
        } catch(e){}
    }
    send({t:'dword_scan', count: count});
    return count;
}

// Auto-scan ebp for SRC_IC (no hardcoded offset)
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

// sprintf hook - room + trigger DWORD scan
Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;
            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var ebpHits = autoReplaceEbp(this.context.ebp);
                if (!dwordScanDone) {
                    send({t:'scanning'});
                    replaceAllDwords();
                    dwordScanDone = true;
                }
                patchCount++;
                send({t: 'sprintf', n: patchCount, ebp: ebpHits});
            }
        } catch(e) {}
    }
});

// strcpy hook - practice range path
if (strcpyAddr) {
    Interceptor.attach(strcpyAddr, {
        onEnter: function(args) {
            try {
                var src = readAscii(args[1], 120);
                if (src.indexOf('customize') < 0 || src.indexOf(SRC_STR) < 0) return;
                // Always re-scan: practice range creates new instances after room loading
                send({t:'scanning_practice'});
                replaceAllDwords();
                replaceStr(args[1], SRC_STR, DST_STR);
                this._do = true;
                this._dst = args[0];
                patchCount++;
                send({t: 'strcpy', n: patchCount});
            } catch(e) {}
        },
        onLeave: function(retval) {
            if (!this._do) return;
            replaceStr(this._dst, SRC_STR, DST_STR);
        }
    });
}

send({t: 'ready', src: SRC_IC, dst: DST_IC});

rpc.exports = {
    count: function() { return patchCount; }
};
"""

def main():
    hair_table = load_hair_table()
    code_to_name = {v[0]: k for k, v in hair_table.items()}

    dst_code = 50125711

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'list':
            list_hairs(hair_table)
            return
        try:
            dst_code = int(arg)
        except ValueError:
            found = False
            for name, (code, pak) in hair_table.items():
                if arg in name:
                    dst_code = code
                    print(f'found: {name} ({code})')
                    found = True
                    break
            if not found:
                print(f'not found: "{arg}"')
                list_hairs(hair_table)
                return

    src_name = code_to_name.get(SRC_IC, f'ItemCode {SRC_IC}')
    dst_name = code_to_name.get(dst_code, f'ItemCode {dst_code}')

    print('=== Hair Replacement (room + practice range) ===')
    print(f'{SRC_IC} ({src_name}) -> {dst_code} ({dst_name})')
    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe not running')
        return

    print(f'PID: {pid}')

    session = frida.attach(pid)
    script = session.create_script(create_js(SRC_IC, dst_code))

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'ready: {p["src"]} -> {p["dst"]}')
            elif t == 'sprintf':
                ebp = f' ebp={p["ebp"]}' if 'ebp' in p else ''
                print(f'[room] sprintf #{p["n"]}{ebp}')
            elif t == 'strcpy':
                print(f'[practice] strcpy #{p["n"]}')
            elif t == 'scanning':
                print('[room] DWORD scan (behind loading screen)...')
            elif t == 'scanning_practice':
                print('[practice] DWORD scan (fallback, ~3 sec)...')
            elif t == 'dword_scan':
                print(f'[room] DWORD replaced: {p["count"]}')

    script.on('message', on_msg)
    script.load()

    print('')
    print('Commands: quit | count | list')
    print('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'count':
                print(f'patches: {script.exports_sync.count()}')
            elif cmd == 'list':
                list_hairs(hair_table)
    except (KeyboardInterrupt, EOFError):
        import time
        print('(stdin closed, daemon mode)')
        while True:
            time.sleep(1)

    script.unload()
    session.detach()
    print('detached.')

if __name__ == '__main__':
    main()

"""
hook_equip_diag2.py — 替换 + 存活验证
1. 替换所有 50125461 → 50125711
2. 立即验证: 扫描残留的50125461
3. 用户进房间
4. 再次验证: 补丁是否被覆盖
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'patch_diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
var srcAsciiBytes = [];
for (var i = 0; i < SRC_STR.length; i++) srcAsciiBytes.push(SRC_STR.charCodeAt(i));

function scanCount(pattern) {
    var ranges = Process.enumerateRanges('rw-');
    var total = 0;
    for (var i = 0; i < ranges.length; i++) {
        var r = ranges[i];
        if (r.size < 8 || r.size > 200 * 1024 * 1024) continue;
        try {
            var mod = Process.findModuleByAddress(r.base);
            if (mod) continue;
        } catch(e) {}
        try {
            var m = Memory.scanSync(r.base, r.size, pattern);
            total += m.length;
        } catch(e) {}
    }
    return total;
}

function doPatch() {
    var ranges = Process.enumerateRanges('rw-');
    var intPatched = 0, asciiPatched = 0;

    for (var ri = 0; ri < ranges.length; ri++) {
        var r = ranges[ri];
        if (r.size < 8 || r.size > 200 * 1024 * 1024) continue;
        try { var mod = Process.findModuleByAddress(r.base); if (mod) continue; } catch(e) {}

        // Patch INT
        try {
            var matches = Memory.scanSync(r.base, r.size, '95 da fc 02');
            for (var mi = 0; mi < matches.length; mi++) {
                matches[mi].address.writeU32(DST_INT);
                intPatched++;
            }
        } catch(e) {}

        // Patch ASCII
        try {
            var hex = srcAsciiBytes.map(function(b){ return ('0'+b.toString(16)).slice(-2); }).join(' ');
            var matches = Memory.scanSync(r.base, r.size, hex);
            for (var mi = 0; mi < matches.length; mi++) {
                var addr = matches[mi].address;
                for (var j = 0; j < dstAsciiBytes.length; j++) {
                    addr.add(j).writeU8(dstAsciiBytes[j]);
                }
                asciiPatched++;
            }
        } catch(e) {}
    }
    return {intPatched: intPatched, asciiPatched: asciiPatched};
}

rpc.exports = {
    patch: function() {
        var result = doPatch();
        return JSON.stringify(result);
    },
    check: function() {
        // 检查50125461残留和50125711数量
        var srcInt = scanCount('95 da fc 02');
        var dstInt = scanCount('8f db fc 02');
        var srcAscii = scanCount('35 30 31 32 35 34 36 31');
        var dstAscii = scanCount('35 30 31 32 35 37 31 31');
        return JSON.stringify({
            src_int_remaining: srcInt,
            dst_int_count: dstInt,
            src_ascii_remaining: srcAscii,
            dst_ascii_count: dstAscii
        });
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
    log(f'=== 替换诊断 === PID:{pid} ===')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'error':
            log(f'[JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    # Step 1: 补丁前检查
    log('Step 1: 补丁前检查...')
    before = json.loads(script.exports_sync.check())
    log(f'  50125461 INT: {before["src_int_remaining"]}, ASCII: {before["src_ascii_remaining"]}')
    log(f'  50125711 INT: {before["dst_int_count"]}, ASCII: {before["dst_ascii_count"]}')

    # Step 2: 执行替换
    log('Step 2: 执行替换...')
    result = json.loads(script.exports_sync.patch())
    log(f'  替换: INT={result["intPatched"]}, ASCII={result["asciiPatched"]}')

    # Step 3: 替换后验证
    log('Step 3: 替换后验证...')
    after = json.loads(script.exports_sync.check())
    log(f'  50125461 残留 INT: {after["src_int_remaining"]}, ASCII: {after["src_ascii_remaining"]}')
    log(f'  50125711 现有 INT: {after["dst_int_count"]}, ASCII: {after["dst_ascii_count"]}')

    log('')
    log('=== 现在进房间，加载完角色后输入 check ===')
    log('命令: check | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
                break
            elif cmd == 'check':
                check = json.loads(script.exports_sync.check())
                log(f'  50125461 残留 INT: {check["src_int_remaining"]}, ASCII: {check["src_ascii_remaining"]}')
                log(f'  50125711 现有 INT: {check["dst_int_count"]}, ASCII: {check["dst_ascii_count"]}')
                if check['src_int_remaining'] > 0:
                    log(f'  !!! 补丁被覆盖! 服务器重新写入了50125461')
                else:
                    log(f'  补丁仍然存活')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')

if __name__ == '__main__':
    main()

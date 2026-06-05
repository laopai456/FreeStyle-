"""
hook_equip_patcher.py — 全面内存替换 (无运行时hook)
在角色加载前, 把堆内存中所有 50125461 替换为 50125711。
不保留任何hook, 避免运行时崩溃。

替换内容:
  1. INT 50125461 (0x02FCDA95) → 50125711 (0x02FCDB8F) — 所有堆内存
  2. ASCII "50125461" → "50125711" — 所有堆内存
  3. UTF-16 "50125461" → "50125711" — 所有堆内存
  4. 文件路径中 "res767" → "res768" — 确保路径指向正确的pak

替换完后脚本自动退出, 游戏无hook运行。
然后进房间, 游戏读到新ItemCode, 从res768.pak加载动态发型。

用法:
  1. 游戏运行, 角色穿着美丽梦想发型
  2. py hook_equip_patcher.py
  3. 看到"替换完成"后进房间
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'full_patch_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// 字节准备
var dstAsciiBytes = [];
for (var i = 0; i < DST_STR.length; i++) dstAsciiBytes.push(DST_STR.charCodeAt(i));
var srcAsciiBytes = [];
for (var i = 0; i < SRC_STR.length; i++) srcAsciiBytes.push(SRC_STR.charCodeAt(i));

var stats = {intPatched: 0, asciiPatched: 0, utf16Patched: 0, pathPatched: 0};

// 获取所有可读写堆内存区域
var ranges = Process.enumerateRanges('rw-');
var heapRanges = [];
for (var i = 0; i < ranges.length; i++) {
    var r = ranges[i];
    if (r.size < 8 || r.size > 200 * 1024 * 1024) continue;
    try {
        var mod = Process.findModuleByAddress(r.base);
        if (mod) continue;
    } catch(e) {}
    heapRanges.push(r);
}

send({t: 'info', msg: '堆区域: ' + heapRanges.length + ' 个'});

// === Pass 1: 替换 INT ===
var intPattern = '95 da fc 02';  // 50125461 LE
var intTotal = 0;

for (var ri = 0; ri < heapRanges.length; ri++) {
    var range = heapRanges[ri];
    try {
        var matches = Memory.scanSync(range.base, range.size, intPattern);
        for (var mi = 0; mi < matches.length; mi++) {
            var addr = matches[mi].address;
            addr.writeU32(DST_INT);
            intTotal++;
            stats.intPatched++;

            // 读取上下文用于日志
            var ctx = '';
            try {
                var bytes = new Uint8Array(addr.sub(8).readByteArray(24));
                for (var j = 0; j < bytes.length; j++) ctx += ('0' + bytes[j].toString(16)).slice(-2) + ' ';
            } catch(e) {}
            send({t: 'int', addr: addr.toString(), ctx: ctx});
        }
    } catch(e) {}
}

send({t: 'info', msg: 'INT替换: ' + intTotal + ' 处'});

// === Pass 2: 替换 ASCII "50125461" ===
var asciiPattern = srcAsciiBytes.map(function(b){ return ('0'+b.toString(16)).slice(-2); }).join(' ');
var asciiTotal = 0;

for (var ri = 0; ri < heapRanges.length; ri++) {
    var range = heapRanges[ri];
    try {
        var matches = Memory.scanSync(range.base, range.size, asciiPattern);
        for (var mi = 0; mi < matches.length; mi++) {
            var addr = matches[mi].address;

            // 读取前后上下文判断是数据还是文件路径
            var prefix = '';
            try { prefix = addr.sub(1).readAnsiString(1); } catch(e) {}
            var suffix = '';
            try { suffix = addr.add(8).readAnsiString(1); } catch(e) {}
            var before = '';
            try { before = addr.sub(16).readAnsiString(20); } catch(e) {}

            // 替换ASCII
            for (var j = 0; j < dstAsciiBytes.length; j++) {
                addr.add(j).writeU8(dstAsciiBytes[j]);
            }
            asciiTotal++;
            stats.asciiPatched++;

            send({t: 'ascii', addr: addr.toString(), before: before.substring(0, 40)});
        }
    } catch(e) {}
}

send({t: 'info', msg: 'ASCII替换: ' + asciiTotal + ' 处'});

// === Pass 3: 替换 UTF-16 "50125461" ===
// 35 00 30 00 31 00 32 00 35 00 34 00 36 00 31 00
var utf16Pattern = '35 00 30 00 31 00 32 00 35 00 34 00 36 00 31 00';
var utf16Replace = [0x33,0x00, 0x35,0x00, 0x31,0x00, 0x32,0x00, 0x35,0x00, 0x37,0x00, 0x31,0x00, 0x31,0x00];
var utf16Total = 0;

for (var ri = 0; ri < heapRanges.length; ri++) {
    var range = heapRanges[ri];
    try {
        var matches = Memory.scanSync(range.base, range.size, utf16Pattern);
        for (var mi = 0; mi < matches.length; mi++) {
            var addr = matches[mi].address;
            for (var j = 0; j < utf16Replace.length; j++) {
                addr.add(j).writeU8(utf16Replace[j]);
            }
            utf16Total++;
            stats.utf16Patched++;
            send({t: 'utf16', addr: addr.toString()});
        }
    } catch(e) {}
}

send({t: 'info', msg: 'UTF-16替换: ' + utf16Total + ' 处'});

// === Pass 4: 替换文件路径中的 pak 号 ===
// "res767" → "res768" (在包含50125711的路径附近)
var pakSrc = '72 65 73 37 36 37';  // "res767"
var pakDst = [0x72, 0x65, 0x73, 0x37, 0x36, 0x38];  // "res768"
var pakTotal = 0;

for (var ri = 0; ri < heapRanges.length; ri++) {
    var range = heapRanges[ri];
    try {
        var matches = Memory.scanSync(range.base, range.size, pakSrc);
        for (var mi = 0; mi < matches.length; mi++) {
            var addr = matches[mi].address;
            // 只替换包含50125711路径附近的res767
            try {
                var ctx = addr.sub(4).readAnsiString(40);
                if (ctx && ctx.indexOf('50125711') >= 0) {
                    for (var j = 0; j < pakDst.length; j++) {
                        addr.add(j).writeU8(pakDst[j]);
                    }
                    pakTotal++;
                    stats.pathPatched++;
                    send({t: 'pak', addr: addr.toString(), ctx: ctx.substring(0, 50)});
                }
            } catch(e) {}
        }
    } catch(e) {}
}

send({t: 'info', msg: 'PAK路径替换: ' + pakTotal + ' 处'});

// === 汇总 ===
send({t: 'done', stats: stats});
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 全面内存替换 === PID:{pid} ===')
    log(f'50125461(美丽梦想 pak767) → 50125711(紫色超赛 pak768)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'info':
                log(f'  {p["msg"]}')
            elif t == 'int':
                log(f'  [INT] {p["addr"]} ctx: {p["ctx"]}')
            elif t == 'ascii':
                log(f'  [ASCII] {p["addr"]} before: "{p.get("before","")}"')
            elif t == 'utf16':
                log(f'  [UTF16] {p["addr"]}')
            elif t == 'pak':
                log(f'  [PAK路径] {p["addr"]} "{p.get("ctx","")}"')
            elif t == 'done':
                s = p['stats']
                log('')
                log('=== 替换完成 ===')
                log(f'  INT:   {s["intPatched"]} 处')
                log(f'  ASCII: {s["asciiPatched"]} 处')
                log(f'  UTF16: {s["utf16Patched"]} 处')
                log(f'  PAK:   {s["pathPatched"]} 处')
                log(f'  总计:  {s["intPatched"]+s["asciiPatched"]+s["utf16Patched"]+s["pathPatched"]} 处')
                log('')
                log('现在可以进房间了。脚本将自动退出。')
            else:
                log(f'  {json.dumps(p)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    # 等待替换完成
    try:
        input('按回车退出...')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。无hook残留。')

if __name__ == '__main__':
    main()

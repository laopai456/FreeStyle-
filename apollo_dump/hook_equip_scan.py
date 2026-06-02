"""
hook_equip_scan.py — 物品替换 Phase 1: 内存探测
扫描游戏内存中 "50125461" 出现的所有位置，理解数据分布

逻辑:
  游戏在内存中存储物品记录，每条记录包含 ItemCode(字符串)、PakNum 等。
  我们要找到这些记录，看清楚结构，为下一步替换做准备。

  为什么是字符串不是整数？
  - ItemCode 在内存中以 ASCII 字符串形式存储 (如 "50125461")
  - 因为游戏源码中 LoadItemFile 接收字符串文件名，内部用字符串比较

  扫描范围:
  - 只扫描堆内存 (游戏运行时数据区)
  - 不扫描代码段 (.text) — 那里的字符串是编译时常量

用法:
  1. 游戏运行中，角色穿着美丽梦想发型
  2. py hook_equip_scan.py
  3. 查看输出，找到 item record 位置

输出:
  - 每个找到的位置 + 前后上下文 (hex dump)
  - 保存到 hook_equip_scan_log.txt
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = '50125461'
DST = '50125711'

LOG_FILE = os.path.join(SCRIPT_DIR, f'equip_scan_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

# Frida JS: 扫描内存找目标字符串
JS_CODE = r"""
'use strict';

var SRC = '50125461';
var SRC_BYTES = [];
for (var i = 0; i < SRC.length; i++) SRC_BYTES.push(SRC.charCodeAt(i));

// 也搜索整数形式: 50125461 = 0x02FD8E55 (little-endian: 55 8E FD 02)
var SRC_INT = [0x35, 0x34, 0x31, 0x32, 0x35, 0x34, 0x36, 0x31]; // "50125461" ASCII

var results = [];

// 扫描所有可读内存区域
send({t: 'status', msg: 'Scanning memory for "' + SRC + '"...'});

var ranges = Process.enumerateRanges('r--');
var totalRanges = ranges.length;
var scanned = 0;
var found = 0;

for (var ri = 0; ri < ranges.length; ri++) {
    var range = ranges[ri];
    // 跳过太小或太大的区域
    if (range.size < 8 || range.size > 100 * 1024 * 1024) {
        scanned++;
        continue;
    }
    // 跳过模块区域 (代码段) — 只扫描堆/数据
    try {
        var mod = Process.findModuleByAddress(range.base);
        if (mod) {
            scanned++;
            continue;
        }
    } catch(e) {}

    try {
        var matches = Memory.scanSync(range.base, range.size, SRC);
        for (var mi = 0; mi < matches.length; mi++) {
            found++;
            var addr = matches[mi].address;
            // 读取前后上下文 (前32字节, 后64字节)
            var ctxBefore = '';
            var ctxAfter = '';
            var ctxStr = '';
            try {
                var before = addr.sub(32).readByteArray(32);
                var after = addr.add(8).readByteArray(64);
                ctxBefore = hexDump(before);
                ctxAfter = hexDump(after);
                // 尝试读周围字符串
                ctxStr = tryReadString(addr.sub(32), 128);
            } catch(e) {}

            results.push({
                addr: addr.toString(),
                offset: '0x' + addr.sub(Process.getModuleByName('FreeStyle.exe').base).toString(16),
                ctxBefore: ctxBefore,
                ctxAfter: ctxAfter,
                ctxStr: ctxStr
            });
        }
    } catch(e) {}
    scanned++;
}

send({t: 'done', found: found, scanned: scanned, total: totalRanges, results: results});

function hexDump(buf) {
    if (!buf) return '';
    var bytes = new Uint8Array(buf);
    var hex = '';
    for (var i = 0; i < bytes.length; i++) {
        hex += ('0' + bytes[i].toString(16)).slice(-2) + ' ';
    }
    return hex.trim();
}

function tryReadString(addr, maxLen) {
    try {
        var s = addr.readAnsiString(maxLen);
        if (s) {
            // 只保留可打印字符
            var clean = '';
            for (var i = 0; i < s.length && i < maxLen; i++) {
                var c = s.charCodeAt(i);
                if (c >= 0x20 && c < 0x7F) clean += s[i];
                else clean += '.';
            }
            return clean;
        }
    } catch(e) {}
    return '';
}
"""

def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 物品替换 Phase 1: 内存探测 === PID:{pid} ===')
    log(f'目标: "{SRC}" → "{DST}"')
    log(f'日志: {LOG_FILE}')
    log('')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'status':
                log(p.get('msg', ''))

            elif t == 'done':
                found = p.get('found', 0)
                scanned = p.get('scanned', 0)
                results = p.get('results', [])

                log(f'扫描完成: {scanned} 个内存区域, 找到 {found} 处 "{SRC}"')
                log('')

                for i, r in enumerate(results):
                    log(f'--- #{i+1} @ {r["addr"]} (RVA {r.get("offset","?")}) ---')
                    if r.get('ctxStr'):
                        log(f'  字符串上下文: {r["ctxStr"]}')
                    if r.get('ctxBefore'):
                        log(f'  前32B: {r["ctxBefore"]}')
                    if r.get('ctxAfter'):
                        log(f'  后64B: {r["ctxAfter"]}')
                    log('')

                # 同时写JSON方便后续分析
                json_path = LOG_FILE.replace('.txt', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                log(f'JSON数据: {json_path}')

            else:
                log(json.dumps(p, ensure_ascii=False)[:200])

        elif msg['type'] == 'error':
            log(f'[JS错误] {msg.get("description", "")}')

    script.on('message', on_msg)
    script.load()

    # 等待扫描完成
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

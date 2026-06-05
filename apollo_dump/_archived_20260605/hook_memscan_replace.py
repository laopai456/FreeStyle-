"""
hook_memscan_replace.py — 内存扫描替换ItemCode，零hook方案
扫描进程可写内存，将所有50125461替换为50125711
不使用Interceptor，不修改代码，Apollo无法检测

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'memscan_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767) — 要被替换的
DST_IC = 50125711  # 紫色超赛发型 (pak768) — 替换目标

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

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;

// 50125461 = 0x02FD6A55 (LE: 55 6A FD 02)
// 50125711 = 0x02FD6E5F (LE: 5F 6E FD 02)

function scanAndReplace() {
    var srcBytes = [0x55, 0x6A, 0xFD, 0x02];
    var dstBytes = [0x5F, 0x6E, 0xFD, 0x02];
    var totalReplaced = 0;
    var details = [];

    // 扫描所有模块的可写内存段
    var modules = Process.enumerateModules();
    var base = ptr('0x400000');

    // 扫描主模块(.data段) + 堆内存
    var ranges = Process.enumerateRanges('rw-');
    log('扫描 ' + ranges.length + ' 个可写内存区域...');

    function log(msg) {
        send({t: 'log', msg: msg});
    }

    for (var ri = 0; ri < ranges.length; ri++) {
        var range = ranges[ri];
        // 跳过太小或太大的区域
        if (range.size < 4 || range.size > 50 * 1024 * 1024) continue;
        // 跳过不可执行的区域（代码段不扫）
        if (range.protection.indexOf('x') >= 0) continue;

        try {
            var buf = new Uint8Array(range.base.readByteArray(range.size));
            for (var i = 0; i <= buf.length - 4; i++) {
                if (buf[i] === srcBytes[0] && buf[i+1] === srcBytes[1] &&
                    buf[i+2] === srcBytes[2] && buf[i+3] === srcBytes[3]) {
                    var addr = range.base.add(i);
                    // 写入新值
                    addr.writeU32(DST_IC);
                    totalReplaced++;
                    if (totalReplaced <= 30) {
                        details.push(addr.toString() + ' (in ' + getModuleName(addr) + ')');
                    }
                }
            }
        } catch(e) {
            // 某些区域不可读，跳过
        }
    }

    return {total: totalReplaced, details: details};
}

function getModuleName(addr) {
    try {
        var mod = Process.findModuleByAddress(addr);
        return mod ? mod.name : 'heap';
    } catch(e) {
        return 'unknown';
    }
}

rpc.exports = {
    scan: function() {
        return JSON.stringify(scanAndReplace());
    },
    // 快速检查某个地址范围的值
    peek: function(addrHex) {
        try {
            var addr = ptr(addrHex);
            var val = addr.readU32();
            return '0x' + addrHex + ' = ' + val + ' (0x' + val.toString(16) + ')';
        } catch(e) {
            return '0x' + addrHex + ' = ERROR: ' + e;
        }
    }
};

send({t: 'ready', msg: '内存扫描就绪 — 零hook'});
"""


def main():
    global LOG_F
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 内存扫描替换 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'log':
                log(f'  {p["msg"]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('流程:')
    log('  1. 进房间等角色加载完成')
    log('  2. 输入 scan → 扫描替换所有50125461→50125711')
    log('  3. 重新进房间/练习场触发加载 → 用新值')
    log('命令: scan | peek <addr> | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'scan':
                log('  扫描中...')
                result = json.loads(script.exports_sync.scan())
                total = result['total']
                log(f'  替换完成: {total} 处 {SRC_IC} → {DST_IC}')
                for d in result.get('details', []):
                    log(f'    {d}')
                if total > 30:
                    log(f'    ... (只显示前30处)')
            elif cmd.startswith('peek '):
                addr = cmd.split()[1]
                result = script.exports_sync.peek(addr)
                log(f'  {result}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

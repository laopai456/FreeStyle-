"""
hook_entry_diag.py — §104 装备入口函数定位
目标: 找到 SetCharacterFeature / LoadItemFile 在二进制中的位置

策略:
  1. 搜索.rdata中的字符串引用 ("customize", "item", ".xml", ".bml")
  2. Hook AcquireSMD, 当加载i50125461时捕获Thread.backtrace
  3. 分析调用链, 找到装备入口函数

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'entry_diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// 读取字符串的辅助函数
function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});

// ==========================================
// 1. 搜索 .rdata 中的关键字符串
// ==========================================
var base = ptr('0x400000');
var mod = Process.getModuleByName('FreeStyle.exe');

// 搜索 .rdata 段中的字符串
var searchPatterns = [
    {name: 'customize_item', pattern: '63 75 73 74 6f 6d 69 7a 65 5c 69 74 65 6d'},  // "customize\item"
    {name: 'pct4d_xml', pattern: '25 34 64 2e 78 6d 6c'},  // "%4d.xml"
    {name: 'pctd_xml', pattern: '25 64 2e 78 6d 6c'},       // "%d.xml"
    {name: 'item_bml', pattern: '69 74 65 6d'},              // "item"
    {name: 'dot_bml', pattern: '2e 62 6d 6c'},               // ".bml"
    {name: 'i_face_xml', pattern: '63 25 64 2e 78 6d 6c'},   // "c%d.xml" (face filename pattern)
];

// 只搜索 .rdata 段 (通常是可读不可执行)
var sections = mod.enumerateSections();
var rdataRange = null;
for (var si = 0; si < sections.length; si++) {
    if (sections[si].name === '.rdata') {
        rdataRange = {base: sections[si].base, size: sections[si].size};
        send({t: 'step', msg: '.rdata: base=' + sections[si].base + ' size=' + sections[si].size});
        break;
    }
}

if (!rdataRange) {
    // 如果没找到.rdata段, 用整个模块
    rdataRange = {base: mod.base, size: mod.size};
    send({t: 'step', msg: '.rdata未找到, 使用整个模块'});
}

for (var pi = 0; pi < searchPatterns.length; pi++) {
    var sp = searchPatterns[pi];
    try {
        var matches = Memory.scanSync(rdataRange.base, rdataRange.size, sp.pattern);
        for (var mi = 0; mi < matches.length && mi < 10; mi++) {
            var addr = matches[mi].address;
            var rva = addr.sub(base).toInt32();
            // 读上下文字符串
            var ctx = '';
            try { ctx = readAscii(addr.sub(4), 60); } catch(e) {}
            var ctxAfter = '';
            try { ctxAfter = readAscii(addr, 60); } catch(e) {}
            send({t: 'string', name: sp.name, addr: addr.toString(), rva: '0x' + rva.toString(16),
                  str: ctxAfter.substring(0, 80)});
        }
        if (matches.length > 10) {
            send({t: 'string_summary', name: sp.name, count: matches.length});
        }
    } catch(e) {
        send({t: 'string_error', name: sp.name, error: e.toString()});
    }
}

// ==========================================
// 2. Hook AcquireSMD — 捕获i50125461的调用栈
// ==========================================
var acquireSMD = base.add(0x01EEC130);
var acquireCaller = base.add(0x01EEBA30);
var callCount = 0;
var targetBacktrace = null;

Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        callCount++;
        this.callNum = callCount;

        // 读ecx+0x10 (SMD路径指针)
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            this.smdPath = path;

            if (path.indexOf('50125461') >= 0) {
                // 捕获完整调用栈
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                var btStrs = [];
                for (var bi = 0; bi < bt.length; bi++) {
                    var rva = bt[bi].sub(base).toInt32();
                    btStrs.push('0x' + rva.toString(16));
                }
                targetBacktrace = btStrs;
                send({t: 'target_trace', callNum: callCount, path: path,
                      backtrace: btStrs});
            }
        } catch(e) {
            send({t: 'error', msg: 'acquireCaller onEnter: ' + e});
        }
    }
});

// ==========================================
// 3. Hook DynamicCreate1 — 对比调用栈
// ==========================================
var dynamicCreate1 = base.add(0x01E99730);
var dynCallCount = 0;

Interceptor.attach(dynamicCreate1, {
    onEnter: function(args) {
        dynCallCount++;
        var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
        var btStrs = [];
        for (var bi = 0; bi < bt.length; bi++) {
            var rva = bt[bi].sub(base).toInt32();
            btStrs.push('0x' + rva.toString(16));
        }
        send({t: 'dyn_trace', callNum: dynCallCount, backtrace: btStrs});
    }
});

send({t: 'ready', msg: '§104诊断就绪 — 搜索字符串 + 调用栈捕获'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            acquireCalls: callCount,
            dynCalls: dynCallCount,
            targetBT: targetBacktrace
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
    log(f'=== §104 装备入口函数定位 === PID:{pid} ===')
    log(f'前置: sc.exe stop ApolloProtect')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'string':
                log(f'  [字符串] {p["name"]}: RVA={p["rva"]} "{p["str"]}"')
            elif t == 'string_summary':
                log(f'  [字符串] {p["name"]}: {p["count"]} 处匹配 (只显示前10)')
            elif t == 'string_error':
                log(f'  [字符串搜索错误] {p["name"]}: {p["error"]}')
            elif t == 'target_trace':
                log(f'  [目标调用栈] call #{p["callNum"]} path="{p["path"]}"')
                for i, addr in enumerate(p['backtrace']):
                    log(f'    [{i}] {addr}')
            elif t == 'dyn_trace':
                log(f'  [DynamicCreate调用栈] call #{p["callNum"]}')
                for i, addr in enumerate(p['backtrace']):
                    log(f'    [{i}] {addr}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。')
    log('命令: status | quit')
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
    print('已断开。')


if __name__ == '__main__':
    main()

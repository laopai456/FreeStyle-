"""
hook_diag_group_read.py — 只读Group信息，不hook文件打开函数
策略: 只hook LoadItemFile入口(安全) + sprintf(安全)
从LoadItemFile的ecx(this)读取 this->0x7E4 和 this->0x7E8 获取Group值

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_group_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461  # 美丽梦想发型 (pak767)
DST_IC = 50125711  # 紫色超赛发型 (pak768)

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
var base = ptr('0x400000');
var patchCount = 0;

// ==========================================
// 1. Hook LoadItemFile入口 — 读this对象的Group字段
// ==========================================
var loadItemFileAddr = base.add(0x1ACE1C0);
var lifCount = 0;

Interceptor.attach(loadItemFileAddr, {
    onEnter: function(args) {
        var iItemCode = args[0].toInt32();
        var szFilename = readAscii(args[1], 80);
        var thisPtr = this.context.ecx;

        lifCount++;

        // 读 this 对象的关键字段
        // 文件打开函数用: this->0x7E4 (flag==0) 或 this->0x7E8 (flag!=0)
        var g7E4 = 0, g7E8 = 0;
        try { g7E4 = thisPtr.add(0x7E4).readU32(); } catch(e) {}
        try { g7E8 = thisPtr.add(0x7E8).readU32(); } catch(e) {}

        // 尝试把这些值当指针读字符串
        var g7E4str = '', g7E8str = '';
        try { g7E4str = readAscii(ptr(g7E4), 32); } catch(e) {}
        try { g7E8str = readAscii(ptr(g7E8), 32); } catch(e) {}

        // 也尝试把 this->0x7E4 和 this->0x7E8 本身当字符串读
        var g7E4direct = '', g7E8direct = '';
        try { g7E4direct = readAscii(thisPtr.add(0x7E4), 32); } catch(e) {}
        try { g7E8direct = readAscii(thisPtr.add(0x7E8), 32); } catch(e) {}

        // dump this对象0x7C0-0x800区域，看附近有没有字符串指针或Group名
        var dumpLines = [];
        try {
            for (var off = 0x7C0; off <= 0x7F8; off += 4) {
                var val = thisPtr.add(off).readU32();
                var asStr = '';
                try { asStr = readAscii(ptr(val), 16); } catch(e) {}
                dumpLines.push({
                    off: '0x' + off.toString(16),
                    val: '0x' + val.toString(16),
                    str: asStr
                });
            }
        } catch(e) {}

        send({t: 'lif', n: lifCount, ic: iItemCode, fname: szFilename,
              thisPtr: thisPtr.toString(),
              g7E4: g7E4, g7E8: g7E8,
              g7E4str: g7E4str, g7E8str: g7E8str,
              g7E4direct: g7E4direct, g7E8direct: g7E8direct,
              dump: dumpLines});
    }
});
send({t: 'step', msg: 'LoadItemFile hook已设置 (含Group读取)'});

// ==========================================
// 2. sprintf + [ebp-0xD8] 双重替换
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;
            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);
                patchCount++;
                send({t: 'patched', n: patchCount});
            }
        } catch(e) {}
    }
});

// ==========================================
// 3. AcquireSMD监控
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;
Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            if (path.indexOf('50125') >= 0 || path.indexOf('768') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'Group读取诊断就绪 — 只hook安全入口'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, lifs: lifCount, acquires: acquireCount});
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
    log(f'=== Group读取诊断 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')
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
            elif t == 'lif':
                log(f'  [LoadItemFile] #{p["n"]} ic={p["ic"]} '
                    f'fname="{p["fname"]}" this={p["thisPtr"]}')
                log(f'    Group7E4=0x{p["g7E4"]:08X} ptr→"{p["g7E4str"]}" '
                    f'direct→"{p["g7E4direct"]}"')
                log(f'    Group7E8=0x{p["g7E8"]:08X} ptr→"{p["g7E8str"]}" '
                    f'direct→"{p["g7E8direct"]}"')
                if p.get('dump'):
                    log(f'    this对象 0x7C0-0x7F8:')
                    for d in p['dump']:
                        s = f'      {d["off"]}: {d["val"]}'
                        if d['str']:
                            s += f' → "{d["str"]}"'
                        log(s)
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}"')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")}')

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

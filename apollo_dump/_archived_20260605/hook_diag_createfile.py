"""
hook_diag_createfile.py — 诊断CreateFileA路径，看游戏怎么找BML
同时保留sprintf替换

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'diag_createfile_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

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
// 1. Hook CreateFileA — 看游戏打开什么文件
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var CreateFileA = kernel32.getExportByName('CreateFileA');
var fileCount = 0;

Interceptor.attach(CreateFileA, {
    onEnter: function(args) {
        try {
            var path = readAscii(args[0], 256);
            // 只看 BML/XML/PAK 相关
            if (path.indexOf('50125') >= 0 || path.indexOf('item') >= 0 ||
                path.indexOf('.bml') >= 0 || path.indexOf('.pak') >= 0 ||
                path.indexOf('customize') >= 0) {
                fileCount++;
                if (fileCount <= 30) {
                    var disp = args[5].toInt32();
                    var dispStr = disp === 1 ? 'READ' : disp === 2 ? 'WRITE' : 'disp=' + disp;
                    send({t: 'createfile', n: fileCount, path: path, disp: dispStr});
                }
            }
        } catch(e) {}
    }
});
send({t: 'step', msg: 'CreateFileA hook已设置'});

// ==========================================
// 2. Hook _chdir — 看游戏切换到什么目录
// ==========================================
var msvcrt = Process.getModuleByName('msvcrt.dll');
var _chdir = null;
try { _chdir = msvcrt.getExportByName('_chdir'); } catch(e) {}
if (_chdir) {
    Interceptor.attach(_chdir, {
        onEnter: function(args) {
            try {
                var path = readAscii(args[0], 256);
                send({t: 'chdir', path: path});
            } catch(e) {}
        }
    });
    send({t: 'step', msg: '_chdir hook已设置'});
}

// ==========================================
// 3. sprintf + [ebp-0xD8] 替换
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
// 4. AcquireSMD监控
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

send({t: 'ready', msg: 'CreateFileA诊断就绪'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, files: fileCount, acquires: acquireCount});
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
    log(f'=== CreateFileA诊断 === PID:{pid} ===')
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
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]}')
            elif t == 'createfile':
                log(f'  [CreateFile] #{p["n"]} path="{p["path"]}" {p["disp"]}')
            elif t == 'chdir':
                log(f'  [chdir] → "{p["path"]}"')
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

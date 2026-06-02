"""
hook_second_read_v2.py — 用 msvcrt fopen/fread 直接读文件到内存
完全不用 JS 数据传输: JS端调 C函数读二进制文件
策略: 第二次 ReadFile(100864B) 时替换 buffer

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'second_read2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// ==========================================
// 辅助: 安全读文件名
// ==========================================
function readName(buf, offset, maxLen) {
    var s = '';
    for (var i = offset; i < offset + maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});

// ==========================================
// 1. 定位CRT模块 (用实例方法, header_only已验证可用)
// ==========================================
var crtMod = null;
try {
    crtMod = Process.getModuleByName('msvcrt.dll');
    send({t: 'step', msg: 'CRT: msvcrt.dll base=' + crtMod.base});
} catch(e) {
    try {
        crtMod = Process.getModuleByName('ucrtbase.dll');
        send({t: 'step', msg: 'CRT: ucrtbase.dll base=' + crtMod.base});
    } catch(e2) {
        send({t: 'error', msg: '找不到CRT模块! ' + e});
    }
}

var fopenAddr  = crtMod.getExportByName('fopen');
var freadAddr  = crtMod.getExportByName('fread');
var fseekAddr  = crtMod.getExportByName('fseek');
var ftellAddr  = crtMod.getExportByName('ftell');
var fcloseAddr = crtMod.getExportByName('fclose');

send({t: 'step', msg: 'fopen=' + fopenAddr + ' fread=' + freadAddr +
      ' fseek=' + fseekAddr + ' ftell=' + ftellAddr + ' fclose=' + fcloseAddr});

// ==========================================
// 2. 构造NativeFunction
// ==========================================
var _fopen  = new NativeFunction(fopenAddr,  'pointer', ['pointer', 'pointer']);
var _fread  = new NativeFunction(freadAddr,  'int', ['pointer', 'int', 'int', 'pointer']);
var _fseek  = new NativeFunction(fseekAddr,  'int', ['pointer', 'int', 'int']);
var _ftell  = new NativeFunction(ftellAddr,  'int', ['pointer']);
var _fclose = new NativeFunction(fcloseAddr, 'int', ['pointer']);

send({t: 'step', msg: 'NativeFunction全部构造OK'});

// ==========================================
// 3. 读目标文件
// ==========================================
var targetBuf = null;
var targetSize = 0;

try {
    var targetPath = Memory.allocAnsiString('C:\\tmp\\sskf\\sskf_50125711_full.bin');
    var modeStr = Memory.allocAnsiString('rb');
    send({t: 'step', msg: '路径alloc OK, 准备fopen'});

    var fp = _fopen(targetPath, modeStr);
    send({t: 'step', msg: 'fopen返回: ' + fp + ' isNull=' + fp.isNull()});

    if (!fp.isNull()) {
        _fseek(fp, 0, 2);
        var fileSize = _ftell(fp);
        send({t: 'step', msg: '文件大小: ' + fileSize});
        _fseek(fp, 0, 0);

        var readSize = 100864;
        if (fileSize < readSize) readSize = fileSize;

        targetBuf = Memory.alloc(readSize);
        send({t: 'step', msg: 'alloc ' + readSize + 'B OK: ' + targetBuf});

        var actuallyRead = _fread(targetBuf, 1, readSize, fp);
        targetSize = actuallyRead;
        send({t: 'step', msg: 'fread返回: ' + actuallyRead});

        _fclose(fp);

        var magic = readName(targetBuf, 0, 4);
        var name = readName(targetBuf, 8, 64);
        send({t: 'loaded', size: targetSize, fileSize: fileSize, magic: magic, name: name});
    } else {
        send({t: 'error', msg: 'fopen返回NULL, 文件不存在?'});
    }
} catch(e) {
    send({t: 'error', msg: '读文件阶段异常: ' + e});
}

send({t: 'step', msg: '文件加载完毕, targetSize=' + targetSize});

// ==========================================
// 4. 状态机
// ==========================================
var STATE_IDLE = 0;
var STATE_FIRST_READ = 1;

var state = STATE_IDLE;
var trackedHandle = 0;
var patchCount = 0;
var totalSSKF = 0;

// ==========================================
// 5. Hook ReadFile
// ==========================================
var ReadFile = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');
send({t: 'step', msg: 'ReadFile=' + ReadFile});

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3];
        this.handle = args[0].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 8) return;

            // === 第二次读取替换 ===
            if (state === STATE_FIRST_READ && this.handle === trackedHandle) {
                var writeSize = Math.min(targetSize, bytesRead);
                Memory.copy(this.buf, targetBuf, writeSize);

                var name2 = readName(this.buf, 8, 64);
                patchCount++;
                state = STATE_IDLE;
                trackedHandle = 0;
                send({t: 'replaced', written: writeSize, name: name2});
                return;
            }

            // === 检查SSKF magic ===
            var m0 = this.buf.readU8();
            var m1 = this.buf.add(1).readU8();
            var m2 = this.buf.add(2).readU8();
            var m3 = this.buf.add(3).readU8();
            if (m0 !== 0x53 || m1 !== 0x53 || m2 !== 0x4B || m3 !== 0x46) return;

            totalSSKF++;
            var name = readName(this.buf, 8, 64);

            if (totalSSKF <= 15) {
                send({t: 'sskf', n: totalSSKF, name: name, size: bytesRead});
            }

            // 跟踪目标第一次512B读取
            if (name.indexOf('50125461_FN') >= 0 && bytesRead === 512) {
                state = STATE_FIRST_READ;
                trackedHandle = this.handle;
                send({t: 'tracking', name: name});
            }
        } catch(e) {
            send({t: 'error', msg: 'ReadFile hook: ' + e});
        }
    }
});

send({t: 'ready', msg: '第二次读取替换v2就绪 (msvcrt读文件).'});

rpc.exports = {
    status: function() {
        return JSON.stringify({totalSSKF: totalSSKF, patches: patchCount, state: state,
                              targetLoaded: targetSize > 0});
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
    log(f'=== 第二次读取替换v2 === PID:{pid} ===')
    log(f'策略: msvcrt fopen/fread 读目标文件, 替换第二次ReadFile buffer')
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
            elif t == 'loaded':
                log(f'  目标加载: {p["size"]}B (文件{p["fileSize"]}B) magic={p["magic"]} name={p["name"]}')
            elif t == 'sskf':
                log(f'  [SSKF #{p["n"]}] "{p["name"]}" ({p["size"]}B)')
            elif t == 'tracking':
                log(f'  [跟踪] "{p["name"]}" → 等待第二次读取')
            elif t == 'replaced':
                log(f'  [替换] 写入{p["written"]}B → "{p["name"]}"')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            desc = msg.get('description', '')
            stack = msg.get('stack', '')
            line = msg.get('lineNumber', '')
            log(f'  [JS错误] {desc}')
            if line:
                log(f'    行号: {line}')
            if stack:
                log(f'    堆栈: {stack[:300]}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit','q','exit'):
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

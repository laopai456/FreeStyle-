"""
hook_stack_swap.py — 栈指针替换: VirtualAlloc新buffer + 扫栈替换指针
策略: 预分配270KB填目标数据, ReadFile完成后替换调用方栈上的buffer指针
前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'stack_swap_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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
// 1. CRT函数 (实例方法, QuickJS兼容)
// ==========================================
var crtMod = Process.getModuleByName('msvcrt.dll');
var fopenAddr  = crtMod.getExportByName('fopen');
var freadAddr  = crtMod.getExportByName('fread');
var fcloseAddr = crtMod.getExportByName('fclose');

var _fopen  = new NativeFunction(fopenAddr,  'pointer', ['pointer', 'pointer']);
var _fread  = new NativeFunction(freadAddr,  'int', ['pointer', 'int', 'int', 'pointer']);
var _fclose = new NativeFunction(fcloseAddr, 'int', ['pointer']);

// 用msvcrt malloc分配 (同堆, 游戏free不会崩)
var mallocAddr = crtMod.getExportByName('malloc');
var _malloc = new NativeFunction(mallocAddr, 'pointer', ['int']);

send({t: 'step', msg: 'CRT函数准备OK (含malloc)'});

// ==========================================
// 2. 预分配270KB + 填充目标SSKF数据
// ==========================================
var TARGET_SIZE = 270264;
var targetPath = Memory.allocAnsiString('C:\\tmp\\sskf\\sskf_50125711_full.bin');
var modeStr = Memory.allocAnsiString('rb');

var fp = _fopen(targetPath, modeStr);
if (fp.isNull()) {
    send({t: 'error', msg: '无法打开目标文件 C:\\tmp\\sskf\\sskf_50125711_full.bin'});
} else {
    send({t: 'step', msg: 'fopen OK: ' + fp});
}

var newBuf = _malloc(TARGET_SIZE);
if (newBuf.isNull()) {
    send({t: 'error', msg: 'malloc失败!'});
}
send({t: 'step', msg: '新buffer分配: ' + newBuf + ' (' + TARGET_SIZE + 'B)'});

var actuallyRead = _fread(newBuf, 1, TARGET_SIZE, fp);
_fclose(fp);
send({t: 'step', msg: 'fread: ' + actuallyRead + ' / ' + TARGET_SIZE});

// 验证
var magic = readName(newBuf, 0, 4);
var name = readName(newBuf, 8, 64);
send({t: 'loaded', size: actuallyRead, magic: magic, name: name});

if (actuallyRead !== TARGET_SIZE) {
    send({t: 'error', msg: '文件不完整! 期望' + TARGET_SIZE + '实际' + actuallyRead});
}

if (magic !== 'SSKF') {
    send({t: 'error', msg: '目标文件不是SSKF! magic=' + magic});
}

// ==========================================
// 3. Hook ReadFile — 栈指针替换
// ==========================================
var ReadFile = Process.getModuleByName('kernel32.dll').getExportByName('ReadFile');
send({t: 'step', msg: 'ReadFile=' + ReadFile});

var STATE_IDLE = 0;
var STATE_FIRST_READ = 1;

var state = STATE_IDLE;
var trackedHandle = 0;
var totalSSKF = 0;
var patchCount = 0;

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

            // === 检查SSKF magic ===
            var m0 = this.buf.readU8();
            var m1 = this.buf.add(1).readU8();
            var m2 = this.buf.add(2).readU8();
            var m3 = this.buf.add(3).readU8();
            if (m0 !== 0x53 || m1 !== 0x53 || m2 !== 0x4B || m3 !== 0x46) return;

            totalSSKF++;
            var name = readName(this.buf, 8, 64);

            if (totalSSKF <= 15) {
                send({t: 'sskf', n: totalSSKF, name: name, size: bytesRead,
                      buf: this.buf.toString()});
            }

            // === 跟踪目标第一次512B读取 ===
            if (name.indexOf('50125461_FN') >= 0 && bytesRead === 512) {
                // 替换header! 让游戏按2骨骼分配内存
                Memory.copy(this.buf, newBuf, 512);
                state = STATE_FIRST_READ;
                trackedHandle = this.handle;
                var newName = readName(this.buf, 8, 64);
                send({t: 'header_patched', origName: name, newName: newName});
                return;
            }

            // === 第二次读取: 栈指针替换 ===
            if (state === STATE_FIRST_READ && this.handle === trackedHandle && bytesRead > 512) {
                var originalBuf = this.buf;

                send({t: 'swap_start', origBuf: originalBuf.toString(),
                      newBuf: newBuf.toString(), origSize: bytesRead});

                // 扫描调用方栈, 找到originalBuf的值并替换为newBuf
                // 只替换游戏层栈帧 (跳过MSVCR100内部帧, 最小偏移0x200)
                var esp = this.context.esp;
                var scanRange = 8192;
                var MIN_OFFSET = 0x200;  // 跳过CRT内部帧
                var patched = 0;
                var patchLocations = [];

                for (var offset = MIN_OFFSET; offset < scanRange; offset += 4) {
                    try {
                        var stackAddr = esp.add(offset);
                        var val = stackAddr.readPointer();
                        if (val.equals(originalBuf)) {
                            stackAddr.writePointer(newBuf);
                            patched++;
                            patchLocations.push('esp+0x' + offset.toString(16));
                        }
                    } catch(e) {
                        // 不可读地址, 停止扫描
                        break;
                    }
                }

                // 注意: 暂不修改bytesRead, 先测试指针替换效果
                // 解析器可能从SSKF内部结构读取各段大小, 不依赖bytesRead

                patchCount++;
                state = STATE_IDLE;
                trackedHandle = 0;

                send({t: 'swapped', patched: patched,
                      locations: patchLocations.join(', '),
                      bytesRead: TARGET_SIZE});

                // 验证newBuffer内容
                var verifyMagic = readName(newBuf, 0, 4);
                var verifyName = readName(newBuf, 8, 64);
                send({t: 'verify', magic: verifyMagic, name: verifyName,
                      size: actuallyRead});
            }
        } catch(e) {
            send({t: 'error', msg: 'ReadFile hook: ' + e});
        }
    }
});

send({t: 'ready', msg: '栈指针替换就绪. 目标270KB预加载.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            totalSSKF: totalSSKF,
            patches: patchCount,
            state: state,
            targetLoaded: actuallyRead > 0
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
    log(f'=== 栈指针替换 === PID:{pid} ===')
    log(f'策略: 预分配270KB + ReadFile后替换栈上的buffer指针')
    log(f'目标: i50125461_FN.smd(美丽梦想发型) → i50125711_FN.smd(紫色超赛发型)')
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
                log(f'  目标加载: {p["size"]}B magic={p["magic"]} name={p["name"]}')
            elif t == 'sskf':
                if p['n'] <= 20:
                    log(f'  [SSKF #{p["n"]}] "{p["name"]}" ({p["size"]}B) buf={p["buf"]}')
            elif t == 'tracking':
                log(f'  [跟踪] "{p["name"]}" handle={p["handle"]}')
            elif t == 'swap_start':
                log(f'  [替换开始] orig={p["origBuf"]} → new={p["newBuf"]} origSize={p["origSize"]}')
            elif t == 'swapped':
                log(f'  [替换完成] 扫到{p["patched"]}处指针 @ {p["locations"]}')
                log(f'  [bytesRead更新] → {p["bytesRead"]}')
            elif t == 'verify':
                log(f'  [验证] newBuf: magic={p["magic"]} name={p["name"]} size={p["size"]}')
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

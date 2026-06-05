"""
dump_acquire.py — 一次性Frida脚本，dump AcquireSMD函数机器码
用法: python dump_acquire.py
输出: acquire_smd.bin (hex string), dump_acquire_时间戳.txt (日志)
"""
import sys
import os
import time
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_PATH = os.path.join(SCRIPT_DIR, "acquire_smd.bin")
# msvcrt fopen不支持中文路径, 用C:\tmp临时路径
BIN_TMP = "C:\\tmp\\acquire_smd.bin"
TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
LOG_PATH = os.path.join(SCRIPT_DIR, f"dump_acquire_{TIMESTAMP}.txt")

# ── 日志 ──────────────────────────────────────────────
log_file = open(LOG_PATH, "w", encoding="utf-8")

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()

# ── 找PID ─────────────────────────────────────────────
import psutil

pid = None
for proc in psutil.process_iter(['pid', 'name']):
    if proc.info['name'] and proc.info['name'].lower() == 'freestyle.exe':
        pid = proc.info['pid']
        break

if pid is None:
    log("错误: 未找到 FreeStyle.exe 进程")
    sys.exit(1)

log(f"找到 FreeStyle.exe PID={pid}")

# ── Frida JS ──────────────────────────────────────────
JS_CODE = r"""
'use strict';

// 所有步骤用send日志输出
send({type: 'step', msg: 'JS脚本开始执行'});

// 用实例方法获取模块base，不用Module静态方法
var mod = Process.getModuleByName('FreeStyle.exe');
send({type: 'step', msg: '获取模块: ' + mod.name + ' base=' + mod.base});

var base = mod.base;
var rva = 0x01EEC130;
var funcAddr = base.add(rva);
send({type: 'step', msg: 'AcquireSMD地址: ' + funcAddr});

var dumpSize = 16384;
send({type: 'step', msg: '准备读取 ' + dumpSize + ' 字节'});

// 读取内存
var buf = funcAddr.readByteArray(dumpSize);
if (buf === null) {
    send({type: 'error', msg: '读取内存失败, 地址不可访问: ' + funcAddr});
} else {
    send({type: 'step', msg: '读取完成, ' + dumpSize + '字节'});
}

// 转hex string
var bytes = new Uint8Array(buf);
var hexChars = [];
for (var i = 0; i < bytes.length; i++) {
    var b = bytes[i];
    hexChars.push(('0' + b.toString(16)).slice(-2));
}
var hexStr = hexChars.join('');

send({type: 'step', msg: 'hex string长度=' + hexStr.length});

// 打印前512字节hex dump到控制台 (16字节一行)
send({type: 'step', msg: '--- 前512字节hex dump ---'});
var dumpLimit = Math.min(512, bytes.length);
for (var row = 0; row < dumpLimit; row += 16) {
    var hexPart = [];
    var asciiPart = [];
    for (var col = 0; col < 16; col++) {
        var idx = row + col;
        var b = bytes[idx];
        hexPart.push(('0' + b.toString(16)).slice(-2));
        var ch = (b >= 0x20 && b <= 0x7e) ? String.fromCharCode(b) : '.';
        asciiPart.push(ch);
    }
    var addr = ('00000000' + row.toString(16)).slice(-8);
    send({type: 'step', msg: addr + '  ' + hexPart.join(' ') + '  ' + asciiPart.join('')});
}
send({type: 'step', msg: '--- hex dump结束 ---'});

// 搜索关键常量: 0x189A0 (100864) 的LE表示
var searchPatterns = [
    {name: '100864 (0x189A0)', bytes: [0xA0, 0x89, 0x01, 0x00]},
    {name: '512 (0x200)', bytes: [0x00, 0x02, 0x00, 0x00]},
    {name: 'ReadFile IAT call (FF15)', bytes: [0xFF, 0x15]}
];
for (var si = 0; si < searchPatterns.length; si++) {
    var pat = searchPatterns[si];
    var found = [];
    for (var pi = 0; pi < bytes.length - pat.bytes.length; pi++) {
        var match = true;
        for (var bi = 0; bi < pat.bytes.length; bi++) {
            if (bytes[pi + bi] !== pat.bytes[bi]) { match = false; break; }
        }
        if (match) {
            var ctx = [];
            for (var ci = Math.max(0, pi - 4); ci < Math.min(bytes.length, pi + pat.bytes.length + 8); ci++) {
                ctx.push(('0' + bytes[ci].toString(16)).slice(-2));
            }
            found.push('off=' + pi.toString(16) + ': ' + ctx.join(' '));
        }
    }
    send({type: 'step', msg: '搜索 ' + pat.name + ': ' + found.length + '处 ' +
          (found.length > 0 ? found.slice(0, 5).join(' | ') : '')});
}

// 用msvcrt fopen/fwrite写文件
var msvcrt = Process.getModuleByName('msvcrt.dll');
send({type: 'step', msg: '获取msvcrt: ' + msvcrt.name});

var fopenPtr = msvcrt.getExportByName('fopen');
var fwritePtr = msvcrt.getExportByName('fwrite');
var fclosePtr = msvcrt.getExportByName('fclose');

send({type: 'step', msg: 'fopen=' + fopenPtr + ' fwrite=' + fwritePtr + ' fclose=' + fclosePtr});

var fopen = new NativeFunction(fopenPtr, 'pointer', ['pointer', 'pointer']);
var fwrite = new NativeFunction(fwritePtr, 'int', ['pointer', 'int', 'int', 'pointer']);
var fclose = new NativeFunction(fclosePtr, 'int', ['pointer']);

var filePath = Memory.allocUtf8String("`BIN_PATH`");
var mode = Memory.allocUtf8String("wb");

var fp = fopen(filePath, mode);
if (fp.isNull()) {
    send({type: 'error', msg: 'fopen失败'});
} else {
    send({type: 'step', msg: '文件打开成功'});

    // 写hex string
    var hexBuf = Memory.allocUtf8String(hexStr);
    var written = fwrite(hexBuf, 1, hexStr.length, fp);
    send({type: 'step', msg: '写入 ' + written + ' 字节 (hex string)'});

    fclose(fp);
    send({type: 'step', msg: '文件关闭完成'});
}

send({type: 'step', msg: 'dump完成，准备退出'});
"""

# 替换路径占位符（注意反斜杠转义）
JS_CODE = JS_CODE.replace("`BIN_PATH`", BIN_TMP.replace("\\", "\\\\"))

# ── 注入 ──────────────────────────────────────────────
log(f"日志文件: {LOG_PATH}")
log(f"输出文件: {BIN_PATH}")
log("正在附加进程...")

session = frida.attach(pid)
done = False

def on_msg(message, data):
    global done
    if message['type'] == 'send':
        payload = message['payload']
        if payload['type'] == 'step':
            log(f"[JS] {payload['msg']}")
        elif payload['type'] == 'error':
            log(f"[JS错误] {payload['msg']}")
            done = True
    elif message['type'] == 'error':
        log(f"[Frida错误] {message['stack']}")
        done = True

script = session.create_script(JS_CODE)
script.on('message', on_msg)
script.load()
log("脚本已注入，等待完成...")

# 等待完成（最多30秒）
import threading
evt = threading.Event()

def wait_done():
    global done
    for _ in range(300):  # 30秒超时
        if done:
            break
        time.sleep(0.1)
    evt.set()

t = threading.Thread(target=wait_done, daemon=True)
t.start()
evt.wait(timeout=35)

# 清理
try:
    script.unload()
except:
    pass
session.detach()

# 验证输出文件
if os.path.exists(BIN_TMP):
    size = os.path.getsize(BIN_TMP)
    log(f"临时文件验证: {BIN_TMP} 大小={size} 字节")
    # 复制到最终路径
    import shutil
    shutil.copy2(BIN_TMP, BIN_PATH)
    log(f"已复制到: {BIN_PATH}")
else:
    log(f"错误: 临时文件不存在 {BIN_TMP}")

log_file.close()
print(f"\n完成。日志: {LOG_PATH}")

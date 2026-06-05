"""
hook_acquire_replace3.py — 精确匹配 + 完整诊断
修复: 只在包含ItemCode 50125461时才替换, 不再宽匹配res767
诊断: 记录所有13次调用的详细信息, 包括指针读取失败的

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_replace3_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

var base = Process.getModuleByName('FreeStyle.exe').base;

var SRC_CODE = '50125461';  // 美丽梦想发型 (pak767)
var DST_CODE = '50125711';  // 紫色超赛发型 (pak768)
var SRC_PAK = 'res767';
var DST_PAK = 'res768';

var srcCodeBytes = [];
var dstCodeBytes = [];
for (var i = 0; i < SRC_CODE.length; i++) {
    srcCodeBytes.push(SRC_CODE.charCodeAt(i));
    dstCodeBytes.push(DST_CODE.charCodeAt(i));
}
var srcPakBytes = [];
var dstPakBytes = [];
for (var i = 0; i < SRC_PAK.length; i++) {
    srcPakBytes.push(SRC_PAK.charCodeAt(i));
    dstPakBytes.push(DST_PAK.charCodeAt(i));
}

var totalCalls = 0;
var patchCount = 0;

// ==========================================
// Hook 调用者入口 0x1EEBA30
// ==========================================
var callerEntry = base.add(0x01EEBA30);

Interceptor.attach(callerEntry, {
    onEnter: function(args) {
        totalCalls++;
        var idx = totalCalls;

        var ecx = this.context.ecx;
        var ecxVal = ecx.toInt32() >>> 0;

        // === 尝试多种方式读字符串 ===

        // 方法1: ecx+0x10 是指针, 读指针→读字符串
        var strPtr = null;
        var filename = '';
        var method = '';
        var ptrVal = 0;

        try {
            ptrVal = ecx.add(0x10).readU32();
            if (ptrVal >= 0x10000) {  // FreeStyle是LARGEADDRESSAWARE, 堆可到0x8xxxxxxx
                strPtr = ptr(ptrVal);
                filename = strPtr.readAnsiString(80);
                method = 'ptr_deref';
            }
        } catch(e) {}

        // 方法2: ecx+0x10 直接是内联字符串
        if (!filename || filename.length < 3) {
            try {
                filename = ecx.add(0x10).readAnsiString(80);
                strPtr = ecx.add(0x10);
                method = 'inline';
            } catch(e) {}
        }

        // 方法3: ecx+0x14 偏移 (SString可能是 +0x0C=len +0x10=capacity +0x14=data_ptr)
        if (!filename || filename.length < 3) {
            try {
                var ptrVal14 = ecx.add(0x14).readU32();
                if (ptrVal14 >= 0x10000) {
                    var tmp = ptr(ptrVal14).readAnsiString(80);
                    if (tmp && tmp.length > 3 && /[a-zA-Z0-9_\\]/.test(tmp)) {
                        filename = tmp;
                        strPtr = ptr(ptrVal14);
                        method = 'ptr_0x14';
                    }
                }
            } catch(e) {}
        }

        // 方法4: 读ecx+0x08 偏移
        if (!filename || filename.length < 3) {
            try {
                var ptrVal08 = ecx.add(0x08).readU32();
                if (ptrVal08 >= 0x10000) {
                    var tmp = ptr(ptrVal08).readAnsiString(80);
                    if (tmp && tmp.length > 3 && /[a-zA-Z0-9_\\]/.test(tmp)) {
                        filename = tmp;
                        strPtr = ptr(ptrVal08);
                        method = 'ptr_0x08';
                    }
                }
            } catch(e) {}
        }

        // 方法5: ecx+0x0C 偏移
        if (!filename || filename.length < 3) {
            try {
                var ptrVal0C = ecx.add(0x0C).readU32();
                if (ptrVal0C >= 0x10000) {
                    var tmp = ptr(ptrVal0C).readAnsiString(80);
                    if (tmp && tmp.length > 3 && /[a-zA-Z0-9_\\]/.test(tmp)) {
                        filename = tmp;
                        strPtr = ptr(ptrVal0C);
                        method = 'ptr_0x0C';
                    }
                }
            } catch(e) {}
        }

        // 记录所有调用 (前30次) — 无论是否读到字符串
        if (idx <= 30) {
            // dump ecx对象前0x20字节的原始值
            var hexdump = '';
            try {
                for (var off = 0; off < 0x20; off += 4) {
                    var v = ecx.add(off).readU32();
                    hexdump += ('00000000' + v.toString(16)).slice(-8) + ' ';
                }
            } catch(e) { hexdump = 'read_error'; }

            send({
                t: 'call',
                idx: idx,
                ecx: '0x' + ecxVal.toString(16),
                ptrAt10: '0x' + ('00000000' + ptrVal.toString(16)).slice(-8),
                method: method || 'none',
                file: (filename && filename.length > 0) ? filename.substring(0, 80) : '',
                hex: hexdump.trim()
            });
        }

        if (!filename || filename.length < 5) return;

        // === 精确匹配: 只在包含ItemCode时替换 ===
        var hasCode = filename.indexOf(SRC_CODE) >= 0;
        if (!hasCode) return;

        send({t: 'target_found', idx: idx, file: filename, method: method});

        // === 替换 ===
        var strLen = filename.length;
        var replaceCount = 0;

        try {
            // 替换 ItemCode "50125461" → "50125711"
            for (var pos = 0; pos <= strLen - srcCodeBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcCodeBytes.length; j++) {
                    if (strPtr.add(pos + j).readU8() !== srcCodeBytes[j]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    for (var j = 0; j < dstCodeBytes.length; j++) {
                        strPtr.add(pos + j).writeU8(dstCodeBytes[j]);
                    }
                    replaceCount++;
                    send({t: 'replace', type: 'ItemCode', pos: pos});
                }
            }

            // 替换 Pak路径 "res767" → "res768" (仅在同时包含ItemCode的文件中)
            for (var pos = 0; pos <= strLen - srcPakBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcPakBytes.length; j++) {
                    if (strPtr.add(pos + j).readU8() !== srcPakBytes[j]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    for (var j = 0; j < dstPakBytes.length; j++) {
                        strPtr.add(pos + j).writeU8(dstPakBytes[j]);
                    }
                    replaceCount++;
                    send({t: 'replace', type: 'PakPath', pos: pos});
                }
            }
        } catch(e) {
            send({t: 'error', msg: '写入失败: ' + e});
            return;
        }

        if (replaceCount > 0) {
            patchCount++;
            var newFilename = '';
            try { newFilename = strPtr.readAnsiString(80); } catch(e) {}
            send({t: 'patched', idx: idx, from: filename, to: newFilename, count: replaceCount});
        }
    }
});

// ==========================================
// SSKF 监控
// ==========================================
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var sskfCount = 0;

Interceptor.attach(ReadFile, {
    onEnter: function(args) { this.buf = args[1]; this.brPtr = args[3]; },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.brPtr.readU32();
            if (n < 4) return;
            var magic = this.buf.readU32();
            if (magic === 0x464B5353) {  // "SSKF" LE
                sskfCount++;
                var flag = this.buf.add(0x2C).readU8();
                var meshSize = this.buf.add(0x04).readU32();
                send({t: 'sskf', n: sskfCount, size: n, meshSize: meshSize, flag: '0x' + flag.toString(16)});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: '替换hook v3就绪 (精确匹配+完整诊断). 进房间.'});

rpc.exports = {
    status: function() {
        return JSON.stringify({total: totalCalls, patches: patchCount, sskf: sskfCount});
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
    log(f'=== AcquireSMD 替换v3 === PID:{pid} ===')
    log(f'50125461(美丽梦想发型 pak767) → 50125711(紫色超赛发型 pak768)')
    log(f'精确匹配: 只在包含ItemCode时替换, 完整诊断所有调用')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'call':
                file_info = f' "{p["file"]}"' if p.get('file') else ' (无字符串)'
                method_info = f' [{p["method"]}]' if p.get('method') != 'none' else ''
                log(f'  [#{p["idx"]}] ecx={p["ecx"]} ptr@10={p["ptrAt10"]}{method_info}{file_info}')
                log(f'        hex: {p["hex"]}')
            elif t == 'target_found':
                log(f'  [目标 #{p["idx"]}] "{p["file"]}" (方法: {p["method"]})')
            elif t == 'replace':
                log(f'    替换 {p["type"]} @+{p["pos"]}')
            elif t == 'patched':
                log(f'  [补丁 #{p["idx"]}] "{p["from"]}" → "{p["to"]}" ({p["count"]}处)')
            elif t == 'sskf':
                log(f'  [SSKF #{p["n"]}] total={p["size"]} mesh={p["meshSize"]} flag={p["flag"]}')
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

"""
hook_acquire_replace2.py — 修复: 正确跟随指针替换字符串
ecx+0x10 是一个指针, 指向堆上的字符串数据
需要: 1.读指针 2.读指针目标字符串 3.匹配则替换指针目标的字节

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_replace2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

        // ecx+0x10 是指针 → 指向堆上的字符串数据
        var strPtr;
        try {
            var ptrVal = ecx.add(0x10).readU32();
            if (ptrVal < 0x10000 || ptrVal >= 0x80000000) return;
            strPtr = ptr(ptrVal);
        } catch(e) { return; }

        // 读字符串
        var filename = '';
        try {
            filename = strPtr.readAnsiString(80);
        } catch(e) { return; }

        if (!filename || filename.length < 5) return;

        // 检查是否包含目标
        var hasCode = filename.indexOf(SRC_CODE) >= 0;
        var hasPak = filename.indexOf(SRC_PAK) >= 0;

        // 记录所有调用 (前20次)
        if (idx <= 20) {
            send({t: 'load', idx: idx, file: filename, hasCode: hasCode, hasPak: hasPak});
        }

        if (!hasCode && !hasPak) return;

        // === 替换 ===
        // 在strPtr指向的字符串数据中替换字节
        var strLen = filename.length;
        var replaceCount = 0;

        try {
            // 替换 ItemCode
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

            // 替换 Pak路径
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
            // 读回确认
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

send({t: 'ready', msg: '替换hook v2就绪 (指针跟随). 进房间.'});

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
    log(f'=== AcquireSMD 替换v2 === PID:{pid} ===')
    log(f'50125461(美丽梦想 pak767) → 50125711(紫色超赛 pak768)')
    log(f'修复: ecx+0x10是指针, 跟随指针到堆数据再替换')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'load':
                code = ' ★' if p.get('hasCode') else ''
                pak = ' ★' if p.get('hasPak') else ''
                log(f'  [#{p["idx"]}] "{p["file"]}"{code}{pak}')
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

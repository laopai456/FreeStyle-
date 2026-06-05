"""
hook_acquire_replace.py — AcquireSMD调用者替换
在调用者 0x1EEBA30 入口处, 检查 this+0x10 的SMD文件名
如果包含 "50125461" (美丽梦想发型), 替换为 "50125711" (紫色超赛发型)
同时替换 "res767" → "res768"

两个字符串等长(25字符), 可原地替换, 不改变SString结构

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json
import frida

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'acquire_replace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
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

// 字节准备
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

        // 读取 this+0x10 的SMD文件名
        var ecx = this.context.ecx;
        var filename = '';
        var filenameAddr;
        try {
            // this+0x10 是SString对象, 需要判断是内联还是堆分配
            // SString布局: [length(4)] [capacity/flags(4)] [data_ptr_or_inline(...)]
            // 简化: 直接读ecx+0x10看是不是指针或内联字符串
            // 从日志看, readAnsiString能直接读到文件名, 说明0x10就是字符串起始
            filenameAddr = ecx.add(0x10);
            filename = filenameAddr.readAnsiString(64);
        } catch(e) {
            try {
                // 可能SString是指针, 读0x10处的指针再读字符串
                var strPtr = ecx.add(0x10).readPointer();
                filename = strPtr.readAnsiString(64);
                filenameAddr = strPtr;
            } catch(e2) {
                filename = '';
            }
        }

        if (!filename || filename.length < 5) return;

        // 只在包含50125461时输出和处理
        var hasTargetCode = filename.indexOf(SRC_CODE) >= 0;
        var hasTargetPak = filename.indexOf(SRC_PAK) >= 0;

        if (hasTargetCode || hasTargetPak) {
            send({
                t: 'match',
                idx: idx,
                original: filename,
                hasCode: hasTargetCode,
                hasPak: hasTargetPak,
                addr: filenameAddr.toString()
            });
        }

        if (!hasTargetCode && !hasTargetPak) return;

        // === 执行替换 ===
        // 需要找到确切的字符串地址
        // readAnsiString返回的是JS字符串, 我们需要原地修改内存
        // 从ecx+0x10开始搜索并替换

        var replaceCount = 0;

        // 方法: 扫描ecx+0x10开始的256字节, 找到目标字节序列并替换
        var scanBase = ecx.add(0x10);
        var scanLen = 128;

        try {
            var buf = new Uint8Array(scanBase.readByteArray(scanLen));
            var bytes = Array.prototype.slice.call(buf);

            // 替换 ItemCode "50125461" → "50125711"
            for (var pos = 0; pos <= scanLen - srcCodeBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcCodeBytes.length; j++) {
                    if (bytes[pos + j] !== srcCodeBytes[j]) { match = false; break; }
                }
                if (match) {
                    for (var j = 0; j < dstCodeBytes.length; j++) {
                        scanBase.add(pos + j).writeU8(dstCodeBytes[j]);
                    }
                    replaceCount++;
                    send({t: 'replace', type: 'ItemCode', pos: '0x' + (0x10 + pos).toString(16)});
                }
            }

            // 替换 Pak路径 "res767" → "res768"
            for (var pos = 0; pos <= scanLen - srcPakBytes.length; pos++) {
                var match = true;
                for (var j = 0; j < srcPakBytes.length; j++) {
                    if (bytes[pos + j] !== srcPakBytes[j]) { match = false; break; }
                }
                if (match) {
                    for (var j = 0; j < dstPakBytes.length; j++) {
                        scanBase.add(pos + j).writeU8(dstPakBytes[j]);
                    }
                    replaceCount++;
                    send({t: 'replace', type: 'PakPath', pos: '0x' + (0x10 + pos).toString(16)});
                }
            }
        } catch(e) {
            send({t: 'error', msg: '替换失败: ' + e});
        }

        if (replaceCount > 0) {
            patchCount++;
            // 读回替换后的文件名确认
            var newFilename = '';
            try { newFilename = scanBase.readAnsiString(64); } catch(e) {}
            send({t: 'patched', idx: idx, newFilename: newFilename, replaces: replaceCount});
        }
    }
});

// ==========================================
// SSKF 监控 (确认SMD确实加载了)
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
            var b0 = this.buf.readU8(), b1 = this.buf.add(1).readU8();
            var b2 = this.buf.add(2).readU8(), b3 = this.buf.add(3).readU8();
            if (b0 === 0x53 && b1 === 0x53 && b2 === 0x4B && b3 === 0x46) {
                sskfCount++;
                var flag = this.buf.add(0x2C).readU8();
                send({t: 'sskf', n: sskfCount, size: n, flag: '0x' + flag.toString(16)});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'AcquireSMD替换hook就绪. 进房间.'});

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
    log(f'=== AcquireSMD 替换 === PID:{pid} ===')
    log(f'50125461(美丽梦想 pak767) → 50125711(紫色超赛 pak768)')
    log(f'Hook: 调用者 0x1EEBA30, 替换 this+0x10 的SMD文件名')
    log(f'日志: {LOG_FILE}')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')

            if t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'match':
                log(f'  [匹配 #{p["idx"]}] "{p["original"]}"')
                if p.get('hasCode'): log(f'    包含ItemCode {SRC_CODE}')
                if p.get('hasPak'): log(f'    包含pak路径 {SRC_PAK}')
            elif t == 'replace':
                log(f'    替换 {p["type"]} @this+{p["pos"]}')
            elif t == 'patched':
                log(f'  [补丁 #{p["idx"]}] → "{p["newFilename"]}" ({p["replaces"]}处)')
            elif t == 'sskf':
                log(f'  [SSKF #{p["n"]}] size={p["size"]} flag={p["flag"]}')
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

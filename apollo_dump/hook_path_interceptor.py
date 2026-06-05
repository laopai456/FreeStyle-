"""
hook_path_interceptor.py — 统一路径拦截器 v2
安全边界: 只 hook DLL 导出函数, 零 .text hook, 零 Apollo 代码
房间: sprintf("customize\\item\\i%d.xml", ItemCode) → 改参数+ebp-0xDC
练习场: strcpy(dst, "customize\\item\\i50125461.xml") → 改dst内容(LEAVE)

v2 修复:
- 删掉 AcquireSMD hook (.text 段 → L2b 杀进程, v1 死因)
- strstr 加 NULL guard (scan 证明安全, 但加保险)
- Apollo 防护交给外部 apollo_all_kill.py --l1-only

钉死三件事:
1. 极热过滤: strcpy=44万/strstr=96万, 回调第一行必须最廉价判断
2. 改dst不改src: LEAVE改写dst(往下流的拷贝), 不动src(可能只读)
3. 等长替换: 50125461→50125711 同为8位, 无长度问题

成功判据: hook后日志 strstr 必须出现 res767/i50125711_FN.smd
         如果仍是 50125461 → 这份copy没被消费, 需挖上游builder

前置: sc.exe stop ApolloProtect
      python apollo_all_kill.py --l1-only
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'path_intercept_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

# ── 配置 ──
SRC_IC = 50125461   # 美丽梦想发型 (pak767, 静态)
DST_IC = 50125671   # 少年漫主角发型 (pak767, 动态, 同pak!)

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
var SRC_PREFIX = 'i' + '""" + str(SRC_IC) + """';   // "i50125461" — 10字节
var DST_PREFIX = 'i' + '""" + str(DST_IC) + """';   // "i50125671" — 10字节

// ── 工具 ──
function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

// NULL-safe readU8: 返回 -1 表示无效指针
function safeReadU8(ptr) {
    try {
        if (ptr.isNull()) return -1;
        return ptr.readU8();
    } catch(e) {
        return -1;
    }
}

// 极廉价: 扫描缓冲区找 "i50125461" 前缀
// 返回: -1=不匹配, >=0=匹配起始偏移
function findItemPrefix(strBuf, maxScan) {
    for (var i = 0; i < maxScan - 10; i++) {
        if (strBuf.add(i).readU8() !== 0x69) continue;    // 'i'
        if (strBuf.add(i+1).readU8() !== 0x35) continue;  // '5'
        if (strBuf.add(i+2).readU8() !== 0x30) continue;  // '0'
        if (strBuf.add(i+3).readU8() !== 0x31) continue;  // '1'
        if (strBuf.add(i+4).readU8() !== 0x32) continue;  // '2'
        if (strBuf.add(i+5).readU8() !== 0x35) continue;  // '5'
        if (strBuf.add(i+6).readU8() !== 0x36) continue;  // '6'
        if (strBuf.add(i+7).readU8() !== 0x37) continue;  // '7'
        if (strBuf.add(i+8).readU8() !== 0x31) continue;  // '1'
        var next = strBuf.add(i+9).readU8();
        if (next >= 0x30 && next <= 0x39) continue;
        return i;
    }
    return -1;
}

// 等长原地替换
function replaceInPlace(buf, pos) {
    for (var j = 0; j < DST_PREFIX.length; j++) {
        buf.add(pos + j).writeU8(DST_PREFIX.charCodeAt(j));
    }
}

send({t: 'step', msg: 'JS开始执行'});

var sprintfPatches = 0;
var strcpyPatches = 0;

// ══════════════════════════════════════════════
// 1. sprintf hook — 房间路径拼接 (DLL函数 ✓)
// ══════════════════════════════════════════════
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
send({t: 'step', msg: 'sprintf=' + sprintfAddr});

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = args[1];
            var c0 = safeReadU8(fmt);
            if (c0 !== 0x63) return;  // 'c'
            var fmtStr = readAscii(fmt, 50);
            if (fmtStr.indexOf('customize') < 0) return;
            if (fmtStr.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();

            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);

                var callerEbp = this.context.ebp;
                try {
                    callerEbp.sub(0xDC).writeU32(DST_IC);
                    callerEbp.sub(0xD8).writeU32(DST_IC);
                } catch(e) {}

                sprintfPatches++;
                send({t: 'sprintf_patch', n: sprintfPatches,
                      orig: SRC_IC, new: DST_IC,
                      result: 'i' + DST_IC + '.xml'});
            }
        } catch(e) {
            send({t: 'error', msg: 'sprintf: ' + e});
        }
    }
});

// ══════════════════════════════════════════════
// 2. strcpy / lstrcpyA hook — 练习场路径拷贝 (DLL函数 ✓)
//    LEAVE 改 dst, 不碰 src
// ══════════════════════════════════════════════
var kernel32 = Process.getModuleByName('kernel32.dll');

function hookStrcpy(module, funcName) {
    var addr;
    try {
        addr = module.getExportByName(funcName);
    } catch(e) {
        send({t: 'skip', msg: funcName + ' not found in ' + module.name});
        return;
    }

    send({t: 'step', msg: funcName + '=' + addr + ' (' + module.name + ')'});

    Interceptor.attach(addr, {
        onEnter: function(args) {
            var src = args[1];

            // NULL guard
            var c0 = safeReadU8(src);
            if (c0 < 0) return;

            // 首字符快速过滤: 'c'/'i'/'r' 才可能命中
            if (c0 !== 0x63 && c0 !== 0x69 && c0 !== 0x72) return;

            this.dst = args[0];
            this.needCheck = true;
        },

        onLeave: function(retval) {
            if (!this.needCheck) return;

            try {
                var dst = this.dst;
                var pos = findItemPrefix(dst, 200);
                if (pos < 0) return;

                replaceInPlace(dst, pos);

                var after = readAscii(dst, 200);
                strcpyPatches++;

                send({t: 'strcpy_patch', func: funcName, n: strcpyPatches,
                      pos: pos, after: after.substring(0, 80)});
            } catch(e) {
                send({t: 'error', msg: funcName + ' LEAVE: ' + e});
            }
        }
    });
}

hookStrcpy(msvcr100, 'strcpy');
hookStrcpy(kernel32, 'lstrcpyA');

// ══════════════════════════════════════════════
// 3. strstr 观察 — 验证替换是否被消费 (DLL函数 ✓)
//    不做替换, 只读 haystack 判 SUCCESS/FAIL
//    NULL guard: scan 证明安全, 但加保险
// ══════════════════════════════════════════════
var strstrAddr = msvcr100.getExportByName('strstr');
var strstrTotalCalls = 0;       // 无条件全局计数: hook活性铁证
var strstrTargetHits = 0;
var strstrSamples = 0;          // 前10个needle样本

Interceptor.attach(strstrAddr, {
    onEnter: function(args) {
        strstrTotalCalls++;     // 无条件+1, 确认hook活着

        // 前10个样本: 不管内容, 直接采样证明hook在工作
        if (strstrSamples < 10) {
            try {
                var sampleNeedle = readAscii(args[1], 30);
                strstrSamples++;
                send({t: 'strstr_sample', n: strstrSamples,
                      total: strstrTotalCalls, needle: sampleNeedle});
            } catch(e) {}
        }

        var needle = args[1];
        var n0 = safeReadU8(needle);
        if (n0 !== 0x72) return;  // 'r' — res767

        var needleStr = readAscii(needle, 60);
        if (needleStr.indexOf('res767') < 0) return;

        var haystack = args[0];
        var h0 = safeReadU8(haystack);
        if (h0 < 0) return;

        var hayStr = readAscii(haystack, 80);

        var hasTarget = hayStr.indexOf(DST_PREFIX) >= 0;
        var hasSource = hayStr.indexOf(SRC_PREFIX) >= 0;

        if (hasTarget || hasSource) {
            strstrTargetHits++;
            send({t: 'strstr_verify', n: strstrTargetHits,
                  needle: needleStr.substring(0, 40),
                  haystack_preview: hayStr.substring(0, 80),
                  hasTarget: hasTarget,
                  hasSource: hasSource,
                  VERDICT: hasTarget ? 'SUCCESS' : 'FAIL'});
        }
    }
});

// ══════════════════════════════════════════════
// 4. ReadFile 观察: 游戏实际读了 PAK 的什么数据
//    只读不改, 确认 strcpy 替换后游戏读的是 50125461 还是 50125671
// ══════════════════════════════════════════════
var ReadFile = kernel32.getExportByName('ReadFile');
var readfileHits = 0;

// 预计算 XOR 编码的搜索字节 (BML 是 XOR 0xFF)
function makeXorPattern(ascii) {
    var result = [];
    for (var i = 0; i < ascii.length; i++) {
        result.push(ascii.charCodeAt(i) ^ 0xFF);
    }
    return result;
}

var xorSrcPrefix = makeXorPattern(SRC_PREFIX); // i50125461 XOR'd
var xorDstPrefix = makeXorPattern(DST_PREFIX); // i50125671 XOR'd

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.brPtr = args[3];
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var bytesRead = this.brPtr.readU32();
            if (bytesRead < 10 || bytesRead > 100000) return;

            var buf = this.buf;
            var firstByte = buf.readU8();

            // BML 文件: XOR 0xFF 后以 <root> 开头
            // <root> = 0x3C 0x72 0x6F 0x6F 0x74 0x3E
            // XOR后   = 0xC3 0x8D 0x90 0x90 0x8B 0xC1
            var isBML = (firstByte === 0xC3 &&
                         buf.add(1).readU8() === 0x8D &&
                         buf.add(2).readU8() === 0x90);

            // SSKF 文件: 以 "SSKF" 开头 = 0x53 0x53 0x4B 0x46
            var isSSKF = (firstByte === 0x53 &&
                          buf.add(1).readU8() === 0x53 &&
                          buf.add(2).readU8() === 0x4B);

            if (!isBML && !isSSKF) return;

            // 在缓冲区中搜索 XOR 编码的 item 前缀
            var raw = new Uint8Array(buf.readByteArray(Math.min(bytesRead, 4096)));
            var foundSrc = false, foundDst = false;
            var scanLen = raw.length - 10;

            for (var i = 0; i < scanLen; i++) {
                if (!foundSrc) {
                    var match = true;
                    for (var j = 0; j < xorSrcPrefix.length; j++) {
                        if (raw[i + j] !== xorSrcPrefix[j]) { match = false; break; }
                    }
                    if (match) foundSrc = true;
                }
                if (!foundDst) {
                    var match2 = true;
                    for (var j = 0; j < xorDstPrefix.length; j++) {
                        if (raw[i + j] !== xorDstPrefix[j]) { match2 = false; break; }
                    }
                    if (match2) foundDst = true;
                }
                if (foundSrc && foundDst) break;
            }

            // 也搜索明文版本 (SMD 文件路径不是 XOR 编码)
            if (!foundSrc || !foundDst) {
                var text = '';
                for (var i = 0; i < Math.min(bytesRead, 2000); i++) {
                    var c = buf.add(i).readU8();
                    if (c >= 0x20 && c < 0x7F) text += String.fromCharCode(c);
                }
                if (text.indexOf(SRC_PREFIX) >= 0) foundSrc = true;
                if (text.indexOf(DST_PREFIX) >= 0) foundDst = true;
            }

            if (foundSrc || foundDst) {
                readfileHits++;
                var fileType = isBML ? 'BML' : 'SSKF';
                send({t: 'readfile', n: readfileHits, type: fileType,
                      bytes: bytesRead,
                      hasSrc: foundSrc, hasDst: foundDst,
                      WHAT: foundDst ? 'READ_TARGET' : 'READ_SOURCE'});
            }
        } catch(e) {}
    }
});

// ══════════════════════════════════════════════
// 定期状态报告
// ══════════════════════════════════════════════
setInterval(function() {
    send({t: 'report',
          sprintfPatches: sprintfPatches,
          strcpyPatches: strcpyPatches,
          strstrTotalCalls: strstrTotalCalls,
          strstrTargetHits: strstrTargetHits,
          readfileHits: readfileHits});
}, 10000);

send({t: 'ready', msg: 'v2 就绪: ' + SRC_IC + ' → ' + DST_IC +
      ' | 仅DLL hook: sprintf+strcpy+lstrcpyA+strstr | 零.text | NULL guard'});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            sprintf: sprintfPatches,
            strcpy: strcpyPatches,
            strstr_hits: strstrTargetHits
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
    log(f'=== 统一路径拦截器 v2 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想发型) → {DST_IC}(紫色超赛发型)')
    log(f'等长: {len(str(SRC_IC))}位 → {len(str(DST_IC))}位 ✓' if len(str(SRC_IC)) == len(str(DST_IC))
        else f'⚠ 长度不等! SRC={len(str(SRC_IC))} DST={len(str(DST_IC))}')
    log(f'钩子: sprintf + strcpy + lstrcpyA (全部DLL函数)')
    log(f'验证: strstr 观察 (不改)')
    log(f'安全: 零.text hook | NULL guard | Apollo交给外部')
    log(f'日志: {LOG_FILE}')

    if len(str(SRC_IC)) != len(str(DST_IC)):
        log('⚠⚠⚠ 长度不等, 等长替换假设不成立!')
        return

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'ready':
                log(f'  ★ {p["msg"]}')
            elif t == 'sprintf_patch':
                log(f'  [sprintf替换] #{p["n"]} → {p["result"]}')
            elif t == 'strcpy_patch':
                log(f'  [strcpy替换] #{p["n"]} ({p["func"]}) pos={p["pos"]}')
                log(f'    → {p["after"]}')
            elif t == 'strstr_verify':
                verdict = p['VERDICT']
                mark = '✅' if verdict == 'SUCCESS' else '❌'
                log(f'  [strstr验证] {mark} {verdict} | needle={p["needle"]}')
                log(f'    haystack: {p["haystack_preview"]}')
            elif t == 'strstr_sample':
                log(f'  [strstr样本] #{p["n"]} total={p["total"]} needle="{p["needle"]}"')
            elif t == 'readfile':
                what = '✅读目标' if p['WHAT'] == 'READ_TARGET' else '❌读源码'
                log(f'  [ReadFile] #{p["n"]} {p["type"]} {p["bytes"]}B {what} src={p["hasSrc"]} dst={p["hasDst"]}')
            elif t == 'report':
                log(f'  [状态] sprintf={p["sprintfPatches"]} strcpy={p["strcpyPatches"]} readfile={p["readfileHits"]} strstr总={p["strstrTotalCalls"]} 命中={p["strstrTargetHits"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            elif t == 'warn' or t == 'skip':
                log(f'  [跳过] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('后台常驻。进练习场测试。')
    log('')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

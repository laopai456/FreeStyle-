// combined_attack_v2.js — 组合攻击 v2 (诊断增强版)
// BML itemcode替换 + SSKF加载监控 + CreateFile pak监控
// 所有输出同时写日志文件
'use strict';

var SRC_CODE = '50125461';  // 美丽梦想(静态)
var DST_CODE = '50125711';  // 紫色超赛(动态)
var LOG_FILE = 'combined_attack_log.txt';

// === 日志 ===
var logBuf = [];
function log(obj) {
    var ts = new Date().toISOString().substr(11, 12);
    var line = ts + ' ' + JSON.stringify(obj);
    logBuf.push(line);
    send({t: 'log', line: line});
}

// === 模块信息 ===
var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;
fsMod.enumerateSections().forEach(function(s) {
    if (s.name === '.text') textSection = s;
});
if (!textSection) throw new Error('.text not found');
var textStart = textSection.address;
var textEnd = textStart.add(textSection.size);
log({event: 'module', base: base.toString(), textStart: textStart.toString(), textSize: textSection.size});

// === Apollo 欺骗 ===
function inTextRange(addr) {
    return addr.compare(textStart) >= 0 && addr.compare(textEnd) < 0;
}

var ntdll = Process.getModuleByName('ntdll.dll');
var VQ_LIES = 0, VP_FAKES = 0;

Interceptor.attach(ntdll.getExportByName('NtQueryVirtualMemory'), {
    onEnter: function(args) { this.memInfo = args[3]; this.infoClass = args[2]; },
    onLeave: function(retval) {
        if (retval.toInt32() !== 0 || this.infoClass.toInt32() !== 0) return;
        try {
            var a = this.memInfo.readPointer();
            if (inTextRange(a)) {
                this.memInfo.add(8).writeU32(0x20);
                this.memInfo.add(20).writeU32(0x20);
                VQ_LIES++;
            }
        } catch(e) {}
    }
});

Interceptor.attach(ntdll.getExportByName('NtProtectVirtualMemory'), {
    onEnter: function(args) { this.basePtr = args[1]; this.oldPtr = args[4]; },
    onLeave: function(retval) {
        try {
            var a = this.basePtr.readPointer();
            if (inTextRange(a) && !this.oldPtr.isNull()) {
                this.oldPtr.writeU32(0x20);
                retval.replace(0);
                VP_FAKES++;
            }
        } catch(e) {}
    }
});

log({event: 'apollo_deception', msg: 'active'});

// === CreateFileW 监控: pak文件打开 ===
var kernel32 = Process.getModuleByName('kernel32.dll');
var OPENED_PAKS = {};

Interceptor.attach(kernel32.getExportByName('CreateFileW'), {
    onEnter: function(args) {
        try {
            var path = args[0].readUtf16String();
            if (path && path.indexOf('.pak') !== -1) {
                var short = path.split('\\').pop().split('/').pop();
                if (!OPENED_PAKS[short]) {
                    OPENED_PAKS[short] = true;
                    log({event: 'pak_open', file: short, handle: args[0].toString()});
                }
            }
        } catch(e) {}
    }
});

// === ReadFile hook ===
var ReadFile = kernel32.getExportByName('ReadFile');
var BML_COUNT = 0;
var SSKF_COUNT = 0;
var PATCH_COUNT = 0;
var SSKF_LOG = [];     // 记录所有SSKF文件名
var BML_LOG = [];      // 记录所有BML
var PATCH_LOG = [];    // 记录替换详情

// XOR预计算
var encSrc = [];
for (var i = 0; i < SRC_CODE.length; i++) encSrc.push(SRC_CODE.charCodeAt(i) ^ 0xFF);
var encDst = [];
for (var i = 0; i < DST_CODE.length; i++) encDst.push(DST_CODE.charCodeAt(i) ^ 0xFF);

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.bytesReadPtr = args[3];
        this.toRead = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.bytesReadPtr.readU32();
            if (n < 4) return;

            // 先检查SSKF magic (前4字节)
            var first4 = this.buf.readByteArray(4);
            if (first4) {
                var m4 = new Uint8Array(first4);
                if (m4[0] === 0x53 && m4[1] === 0x53 && m4[2] === 0x4B && m4[3] === 0x46) {
                    SSKF_COUNT++;
                    // 扫描栈找文件名
                    var fname = scanStackForFilename(this.context.esp);
                    var entry = {event: 'sskf', n: SSKF_COUNT, size: n, fname: fname || '(unknown)'};
                    SSKF_LOG.push(entry);
                    log(entry);

                    // 检查是否是50125711的SMD
                    if (fname && fname.indexOf(DST_CODE) !== -1) {
                        log({event: 'sskf_target', msg: '!!! 50125711 SMD loaded !!!', fname: fname, size: n});
                    }
                    // 检查是否是50125461的SMD
                    if (fname && fname.indexOf(SRC_CODE) !== -1) {
                        log({event: 'sskf_source', msg: 'source SMD loaded (should be replaced)', fname: fname, size: n});
                    }
                    return;
                }
            }

            // 检查BML (XOR <root>)
            if (n < 50 || n > 10000) return;
            var buf = new Uint8Array(this.buf.readByteArray(n));
            var tag = [0x3C, 0x72, 0x6F, 0x6F, 0x74, 0x3E];
            var ok = true;
            for (var i = 0; i < 6; i++) {
                if ((buf[i] ^ 0xFF) !== tag[i]) { ok = false; break; }
            }
            if (!ok) return;

            BML_COUNT++;

            // 解码全文
            var text = '';
            for (var i = 0; i < n; i++) {
                var c = buf[i] ^ 0xFF;
                if (c >= 0x20 && c < 0x7F) text += String.fromCharCode(c);
                else if (c === 0x0A || c === 0x0D) text += '\n';
            }

            var icMatch = text.match(/i(\d{6,8})/);
            var ic = icMatch ? icMatch[1] : '';

            // 提取所有标签内容
            var meshes = extractTag(text, 'mesh');
            var textures = extractTag(text, 'texture');
            var types = extractTag(text, 'type');
            var channels = extractTag(text, 'channel');

            var bmlEntry = {
                event: 'bml', n: BML_COUNT, ic: ic,
                meshes: meshes, textures: textures, types: types,
                channels: channels, rawSize: n
            };
            BML_LOG.push(bmlEntry);
            log(bmlEntry);

            // 如果是目标BML，替换
            if (ic === SRC_CODE) {
                var patchCount = 0;
                var rawBuf = this.buf;

                // 替换<mesh>内的itemcode
                var meshTag = [0x3C, 0x6D, 0x65, 0x73, 0x68, 0x3E];
                var meshEndTag = [0x3C, 0x2F, 0x6D, 0x65, 0x73, 0x68, 0x3E];
                patchCount += replaceInTag(buf, rawBuf, n, meshTag, meshEndTag, encSrc, encDst);

                // 替换<texture>内的itemcode
                var texTag = [0x3C, 0x74, 0x65, 0x78, 0x74, 0x75, 0x72, 0x65, 0x3E];
                var texEndTag = [0x3C, 0x2F, 0x74, 0x65, 0x78, 0x74, 0x75, 0x72, 0x65, 0x3E];
                patchCount += replaceInTag(buf, rawBuf, n, texTag, texEndTag, encSrc, encDst);

                PATCH_COUNT += patchCount;

                // 读回验证
                var afterBuf = new Uint8Array(rawBuf.readByteArray(n));
                var afterText = '';
                for (var i = 0; i < n; i++) {
                    var c = afterBuf[i] ^ 0xFF;
                    if (c >= 0x20 && c < 0x7F) afterText += String.fromCharCode(c);
                    else if (c === 0x0A || c === 0x0D) afterText += '\n';
                }
                var afterMeshes = extractTag(afterText, 'mesh');
                var afterTextures = extractTag(afterText, 'texture');

                var patchEntry = {
                    event: 'patch', ic: ic, patches: patchCount, total: PATCH_COUNT,
                    before_meshes: meshes, after_meshes: afterMeshes,
                    before_textures: textures, after_textures: afterTextures
                };
                PATCH_LOG.push(patchEntry);
                log(patchEntry);
            }
        } catch(e) {
            log({event: 'error', where: 'ReadFile', msg: e.toString()});
        }
    }
});

// === 辅助函数 ===

function extractTag(text, tagName) {
    var results = [];
    var re = new RegExp('<' + tagName + '>([^<]+)</' + tagName + '>', 'g');
    var m;
    while ((m = re.exec(text)) !== null) results.push(m[1]);
    return results;
}

function replaceInTag(buf, rawBuf, n, openTag, closeTag, encSrc, encDst) {
    var count = 0;
    for (var pos = 0; pos <= n - openTag.length; pos++) {
        var isStart = true;
        for (var j = 0; j < openTag.length; j++) {
            if ((buf[pos + j] ^ 0xFF) !== openTag[j]) { isStart = false; break; }
        }
        if (!isStart) continue;

        var contentStart = pos + openTag.length;
        var contentEnd = -1;
        for (var p = contentStart; p <= n - closeTag.length; p++) {
            var isEnd = true;
            for (var j = 0; j < closeTag.length; j++) {
                if ((buf[p + j] ^ 0xFF) !== closeTag[j]) { isEnd = false; break; }
            }
            if (isEnd) { contentEnd = p; break; }
        }
        if (contentEnd === -1) continue;

        for (var pp = contentStart; pp <= contentEnd - encSrc.length; pp++) {
            var match = true;
            for (var j = 0; j < encSrc.length; j++) {
                if (buf[pp + j] !== encSrc[j]) { match = false; break; }
            }
            if (match) {
                for (var j = 0; j < encDst.length; j++) {
                    rawBuf.add(pp + j).writeU8(encDst[j]);
                }
                count++;
                pp += encSrc.length - 1;
            }
        }
        pos = contentEnd + closeTag.length - 1;
    }
    return count;
}

function scanStackForFilename(esp) {
    for (var off = 0; off < 0x800; off += 4) {
        try {
            var ptrVal = esp.add(off).readPointer();
            var tries = [
                function() { return ptrVal.readAnsiString(128); },
                function() { return ptrVal.add(4).readAnsiString(128); },
            ];
            for (var ti = 0; ti < tries.length; ti++) {
                try {
                    var s = tries[ti]();
                    if (s && (s.indexOf('.smd') >= 0 || s.indexOf('.bml') >= 0 || s.indexOf('.bm') >= 0)) {
                        return s;
                    }
                } catch(e) {}
            }
            // Double deref
            try {
                var ptr2 = ptrVal.readPointer();
                var s4 = ptr2.readAnsiString(128);
                if (s4 && (s4.indexOf('.smd') >= 0 || s4.indexOf('.bml') >= 0)) {
                    return s4;
                }
            } catch(e) {}
        } catch(e) {}
    }
    return null;
}

log({event: 'hook_ready', msg: 'Monitoring: CreateFile + ReadFile(BML+SSKF)', src: SRC_CODE, dst: DST_CODE});

// === RPC ===
rpc.exports = {
    status: function() {
        var summary = {
            event: 'status', src: SRC_CODE, dst: DST_CODE,
            patches: PATCH_COUNT, bmls: BML_COUNT, sskfs: SSKF_COUNT,
            vq_lies: VQ_LIES, vp_fakes: VP_FAKES,
            paks_opened: Object.keys(OPENED_PAKS),
            sskf_files: SSKF_LOG.map(function(e) { return e.fname; }),
            log_entries: logBuf.length
        };
        log(summary);
    },
    getLog: function() {
        return logBuf.join('\n');
    },
    getSskfLog: function() {
        return JSON.stringify(SSKF_LOG, null, 2);
    }
};

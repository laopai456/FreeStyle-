// combined_attack.js — 组合攻击: 同pak内BML itemcode替换
// 50125461(美丽梦想,静态) → 50125711(紫色超赛,动态)
// BML中: res767\i50125461_MT.smd → res767\i50125711_MT.smd (pak前缀不变)
// 配合: res767_combined.pak (已包含50125711的SMD文件)
'use strict';

var SRC_CODE = '50125461';  // 美丽梦想发型(静态)
var DST_CODE = '50125711';  // 紫色超赛发型(动态)
var SRC_PAK  = 'res767';    // 同pak，不替换

// === Apollo 欺骗 ===
var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;
fsMod.enumerateSections().forEach(function(s) {
    if (s.name === '.text') textSection = s;
});
if (!textSection) throw new Error('.text not found');
var textStart = textSection.address;
var textEnd = textStart.add(textSection.size);

var VP_DISABLED = false;
function inTextRange(addr) {
    return addr.compare(textStart) >= 0 && addr.compare(textEnd) < 0;
}

// NtQueryVirtualMemory
var ntdll = Process.getModuleByName('ntdll.dll');
Interceptor.attach(ntdll.getExportByName('NtQueryVirtualMemory'), {
    onEnter: function(args) {
        this.memInfo = args[3];
        this.infoClass = args[2];
    },
    onLeave: function(retval) {
        if (retval.toInt32() !== 0 || this.infoClass.toInt32() !== 0) return;
        try {
            var a = this.memInfo.readPointer();
            if (inTextRange(a)) {
                this.memInfo.add(8).writeU32(0x20);
                this.memInfo.add(20).writeU32(0x20);
            }
        } catch(e) {}
    }
});

// NtProtectVirtualMemory
Interceptor.attach(ntdll.getExportByName('NtProtectVirtualMemory'), {
    onEnter: function(args) {
        this.basePtr = args[1];
        this.oldPtr = args[4];
        this.ours = VP_DISABLED;
    },
    onLeave: function(retval) {
        if (this.ours) return;
        try {
            var a = this.basePtr.readPointer();
            if (inTextRange(a) && !this.oldPtr.isNull()) {
                this.oldPtr.writeU32(0x20);
                retval.replace(0);
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'Apollo deception active'});

// === ReadFile hook: BML itemcode 替换 ===
var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFile = kernel32.getExportByName('ReadFile');
var PATCH_COUNT = 0;
var BML_COUNT = 0;

// 预计算XOR编码的搜索/替换字节
var encSrc = [];
for (var i = 0; i < SRC_CODE.length; i++) encSrc.push(SRC_CODE.charCodeAt(i) ^ 0xFF);
var encDst = [];
for (var i = 0; i < DST_CODE.length; i++) encDst.push(DST_CODE.charCodeAt(i) ^ 0xFF);

// 验证等长
if (encSrc.length !== encDst.length) {
    send({t: 'error', msg: 'SRC和DST长度不同! 必须等长替换'});
}

Interceptor.attach(ReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.bytesReadPtr = args[3];
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        try {
            var n = this.bytesReadPtr.readU32();
            if (n < 50 || n > 10000) return;

            var buf = new Uint8Array(this.buf.readByteArray(n));

            // XOR解码检查 <root>
            var tag = [0x3C, 0x72, 0x6F, 0x6F, 0x74, 0x3E];
            var ok = true;
            for (var i = 0; i < 6; i++) {
                if ((buf[i] ^ 0xFF) !== tag[i]) { ok = false; break; }
            }
            if (!ok) return;

            BML_COUNT++;

            // 解码找itemcode
            var text = '';
            for (var i = 0; i < n; i++) {
                var c = buf[i] ^ 0xFF;
                if (c >= 0x20 && c < 0x7F) text += String.fromCharCode(c);
            }

            var icMatch = text.match(/i(\d{6,8})/);
            var ic = icMatch ? icMatch[1] : '';

            // 提取mesh路径
            var meshes = [];
            var re = /<mesh>([^<]+)<\/mesh>/g, m;
            while ((m = re.exec(text)) !== null) meshes.push(m[1]);

            send({t: 'bml', n: BML_COUNT, ic: ic, meshes: meshes});

            // 如果是目标BML，替换itemcode（只在<mesh>标签内）
            if (ic === SRC_CODE) {
                var patchCount = 0;
                var rawBuf = this.buf;

                // 找<mesh>...</mesh>区间
                var meshTag = [0x3C, 0x6D, 0x65, 0x73, 0x68, 0x3E];
                var endTag  = [0x3C, 0x2F, 0x6D, 0x65, 0x73, 0x68, 0x3E];

                for (var pos = 0; pos <= n - meshTag.length; pos++) {
                    var isStart = true;
                    for (var j = 0; j < meshTag.length; j++) {
                        if ((buf[pos + j] ^ 0xFF) !== meshTag[j]) { isStart = false; break; }
                    }
                    if (!isStart) continue;

                    var meshStart = pos + meshTag.length;
                    var meshEnd = -1;
                    for (var p = meshStart; p <= n - endTag.length; p++) {
                        var isEnd = true;
                        for (var j = 0; j < endTag.length; j++) {
                            if ((buf[p + j] ^ 0xFF) !== endTag[j]) { isEnd = false; break; }
                        }
                        if (isEnd) { meshEnd = p; break; }
                    }
                    if (meshEnd === -1) continue;

                    // 在[meshStart, meshEnd)区间内替换itemcode
                    for (var pp = meshStart; pp <= meshEnd - encSrc.length; pp++) {
                        var match = true;
                        for (var j = 0; j < encSrc.length; j++) {
                            if (buf[pp + j] !== encSrc[j]) { match = false; break; }
                        }
                        if (match) {
                            for (var j = 0; j < encDst.length; j++) {
                                rawBuf.add(pp + j).writeU8(encDst[j]);
                            }
                            patchCount++;
                            pp += encSrc.length - 1;
                        }
                    }
                    pos = meshEnd + endTag.length - 1;
                }

                // 也替换<texture>标签内的itemcode（如有）
                var texTag = [0x3C, 0x74, 0x65, 0x78, 0x74, 0x75, 0x72, 0x65, 0x3E];
                var texEndTag = [0x3C, 0x2F, 0x74, 0x65, 0x78, 0x74, 0x75, 0x72, 0x65, 0x3E];

                for (var pos = 0; pos <= n - texTag.length; pos++) {
                    var isStart = true;
                    for (var j = 0; j < texTag.length; j++) {
                        if ((buf[pos + j] ^ 0xFF) !== texTag[j]) { isStart = false; break; }
                    }
                    if (!isStart) continue;

                    var texStart = pos + texTag.length;
                    var texEnd = -1;
                    for (var p = texStart; p <= n - texEndTag.length; p++) {
                        var isEnd = true;
                        for (var j = 0; j < texEndTag.length; j++) {
                            if ((buf[p + j] ^ 0xFF) !== texEndTag[j]) { isEnd = false; break; }
                        }
                        if (isEnd) { texEnd = p; break; }
                    }
                    if (texEnd === -1) continue;

                    for (var pp = texStart; pp <= texEnd - encSrc.length; pp++) {
                        var match = true;
                        for (var j = 0; j < encSrc.length; j++) {
                            if (buf[pp + j] !== encSrc[j]) { match = false; break; }
                        }
                        if (match) {
                            for (var j = 0; j < encDst.length; j++) {
                                rawBuf.add(pp + j).writeU8(encDst[j]);
                            }
                            patchCount++;
                            pp += encSrc.length - 1;
                        }
                    }
                    pos = texEnd + texEndTag.length - 1;
                }

                PATCH_COUNT += patchCount;

                // 读回验证
                var afterBuf = new Uint8Array(rawBuf.readByteArray(n));
                var afterText = '';
                for (var i = 0; i < n; i++) {
                    var c = afterBuf[i] ^ 0xFF;
                    if (c >= 0x20 && c < 0x7F) afterText += String.fromCharCode(c);
                }
                var afterMeshes = [];
                var re2 = /<mesh>([^<]+)<\/mesh>/g;
                while ((m = re2.exec(afterText)) !== null) afterMeshes.push(m[1]);

                send({t: 'patched', ic: ic, patches: patchCount, total: PATCH_COUNT, after: afterMeshes});
            }
        } catch(e) {
            send({t: 'error', msg: 'ReadFile: ' + e});
        }
    }
});

send({t: 'hook', msg: 'ReadFile BML hook active. Waiting for item ' + SRC_CODE + ' load...'});

// RPC
rpc.exports = {
    status: function() {
        send({t: 'status', src: SRC_CODE, dst: DST_CODE, patches: PATCH_COUNT, bmls: BML_COUNT});
    }
};

// bml_mem_patch.js — BML内存补丁 + 全链路监控
// 用法: py bml_mem_patch.py  # 美丽梦想(50125461) → 紫色超赛(50125711)
var SRC_CODE = '50125461';
var DST_CODE = '50125711';
var SRC_PAK  = 'res767';
var DST_PAK  = 'res768';

// Frida API 兼容：32位进程可能需要不同API
function resolveExport(dll, name) {
    var addr = null;
    try { addr = Module.findExportByName(dll, name); } catch(e) {}
    if (!addr) {
        try { addr = Process.getModuleByName(dll).findExportByName(name); } catch(e) {}
    }
    if (!addr) {
        try { addr = Module.getExportByName(dll, name); } catch(e) {}
    }
    return addr;
}

// === 1. Hook CreateFileW — 监控游戏打开了哪些pak文件 ===
(function() {
    try {
        var addr = resolveExport('kernel32.dll', 'CreateFileW');
        if (!addr) throw new Error('CreateFileW not found');
        send({type:'info', msg:'CreateFileW @ ' + addr});
        Interceptor.attach(addr, {
            onEnter: function(args) {
                try {
                    var path = args[0].readUtf16String();
                    if (path && path.indexOf('.pak') !== -1) {
                        var short = path.split('\\').pop().split('/').pop();
                        if (short.indexOf('res7') === 0 || short.indexOf('item7') === 0) {
                            send({type:'file_open', path: short});
                        }
                    }
                } catch(e) {}
            }
        });
    } catch(e) {
        send({type:'error', msg:'CreateFileW hook FAIL: ' + e});
    }
})();

// === 2. Hook CreateFileA ===
(function() {
    try {
        var addr = resolveExport('kernel32.dll', 'CreateFileA');
        if (!addr) throw new Error('CreateFileA not found');
        send({type:'info', msg:'CreateFileA @ ' + addr});
        Interceptor.attach(addr, {
            onEnter: function(args) {
                try {
                    var path = args[0].readUtf8String();
                    if (path && path.indexOf('res7') !== -1 && path.indexOf('.pak') !== -1) {
                        send({type:'file_open_a', path: path});
                    }
                } catch(e) {}
            }
        });
    } catch(e) {
        send({type:'error', msg:'CreateFileA hook FAIL: ' + e});
    }
})();

// === 3. Hook ReadFile — 监控BML读取 + 内存补丁 ===
(function() {
    try {
        var addr = resolveExport('kernel32.dll', 'ReadFile');
        if (!addr) throw new Error('ReadFile not found');
        send({type:'info', msg:'ReadFile @ ' + addr});
        Interceptor.attach(addr, {
            onEnter: function(args) {
                this.lpBuffer = args[1];
                this.lpBytesRead = args[3];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                try {
                    var n = this.lpBytesRead.readU32();
                    if (n < 50 || n > 10000) return;

                    var buf = new Uint8Array(this.lpBuffer.readByteArray(n));

                    // XOR解码检查<root>
                    var ok = true;
                    var tag = [0x3C,0x72,0x6F,0x6F,0x74,0x3E];
                    for (var i = 0; i < 6; i++) {
                        if ((buf[i] ^ 0xFF) !== tag[i]) { ok = false; break; }
                    }
                    if (!ok) return;

                    // 解码全文
                    var text = '';
                    for (var i = 0; i < n; i++) {
                        var c = buf[i] ^ 0xFF;
                        if (c >= 0x20 && c < 0x7F) text += String.fromCharCode(c);
                        else if (c === 0x0A || c === 0x0D) text += '\n';
                    }

                    // 提取itemcode
                    var icMatch = text.match(/i(\d{6,8})/);
                    var ic = icMatch ? icMatch[1] : '';

                    // 显示所有BML读取
                    var meshes = [];
                    var re = /<mesh>([^<]+)<\/mesh>/g, m;
                    while ((m = re.exec(text)) !== null) meshes.push(m[1]);

                    send({type:'bml_read', itemcode: ic, size: n, meshes: meshes});

                    // 如果是目标BML，做内存补丁 — 只改<mesh>标签内的路径
                    if (ic === SRC_CODE) {
                        var patchCount = 0;
                        var rawBuf = this.lpBuffer;

                        // 找所有<mesh>...</mesh>区间，只在这些区间内替换
                        var meshTag = [0x3C,0x6D,0x65,0x73,0x68,0x3E]; // <mesh>
                        var endTag  = [0x3C,0x2F,0x6D,0x65,0x73,0x68,0x3E]; // </mesh>

                        var encSrcPak = [];
                        for (var i = 0; i < SRC_PAK.length; i++) encSrcPak.push(SRC_PAK.charCodeAt(i) ^ 0xFF);
                        var encDstPak = [];
                        for (var i = 0; i < DST_PAK.length; i++) encDstPak.push(DST_PAK.charCodeAt(i) ^ 0xFF);
                        var encSrcCode = [];
                        for (var i = 0; i < SRC_CODE.length; i++) encSrcCode.push(SRC_CODE.charCodeAt(i) ^ 0xFF);
                        var encDstCode = [];
                        for (var i = 0; i < DST_CODE.length; i++) encDstCode.push(DST_CODE.charCodeAt(i) ^ 0xFF);

                        // 在buf中找每个<mesh>...</mesh>区间
                        for (var searchPos = 0; searchPos <= n - meshTag.length; searchPos++) {
                            // XOR解码看是不是<mesh>
                            var isStart = true;
                            for (var j = 0; j < meshTag.length; j++) {
                                if ((buf[searchPos + j] ^ 0xFF) !== meshTag[j]) { isStart = false; break; }
                            }
                            if (!isStart) continue;

                            var meshStart = searchPos + meshTag.length;

                            // 找</mesh>
                            var meshEnd = -1;
                            for (var p = meshStart; p <= n - endTag.length; p++) {
                                var isEnd = true;
                                for (var j = 0; j < endTag.length; j++) {
                                    if ((buf[p + j] ^ 0xFF) !== endTag[j]) { isEnd = false; break; }
                                }
                                if (isEnd) { meshEnd = p; break; }
                            }
                            if (meshEnd === -1) continue;

                            // 只在[meshStart, meshEnd)区间内替换
                            for (var pos = meshStart; pos <= meshEnd - encSrcPak.length; pos++) {
                                var match = true;
                                for (var j = 0; j < encSrcPak.length; j++) {
                                    if (buf[pos + j] !== encSrcPak[j]) { match = false; break; }
                                }
                                if (match) {
                                    for (var j = 0; j < encDstPak.length; j++) {
                                        rawBuf.add(pos + j).writeU8(encDstPak[j]);
                                    }
                                    patchCount++;
                                    pos += encSrcPak.length - 1;
                                }
                            }
                            for (var pos = meshStart; pos <= meshEnd - encSrcCode.length; pos++) {
                                var match = true;
                                for (var j = 0; j < encSrcCode.length; j++) {
                                    if (buf[pos + j] !== encSrcCode[j]) { match = false; break; }
                                }
                                if (match) {
                                    for (var j = 0; j < encDstCode.length; j++) {
                                        rawBuf.add(pos + j).writeU8(encDstCode[j]);
                                    }
                                    patchCount++;
                                    pos += encSrcCode.length - 1;
                                }
                            }

                            searchPos = meshEnd + endTag.length - 1;
                        }

                        // 读回补丁后的内容验证
                        var afterBuf = new Uint8Array(rawBuf.readByteArray(n));
                        var afterText = '';
                        for (var i = 0; i < n; i++) {
                            var c = afterBuf[i] ^ 0xFF;
                            if (c >= 0x20 && c < 0x7F) afterText += String.fromCharCode(c);
                            else if (c === 0x0A || c === 0x0D) afterText += '\n';
                        }
                        var afterMeshes = [];
                        var re2 = /<mesh>([^<]+)<\/mesh>/g;
                        while ((m = re2.exec(afterText)) !== null) afterMeshes.push(m[1]);

                        send({type:'patched', item: ic, patches: patchCount, after_meshes: afterMeshes});
                    }
                } catch(e) {
                    send({type:'error', msg:'ReadFile leave: ' + e});
                }
            }
        });
    } catch(e) {
        send({type:'error', msg:'ReadFile hook FAIL: ' + e});
    }
})();

send({type:'info', msg:'Ready — monitoring CreateFile + ReadFile, patching ' + SRC_CODE + '->' + DST_CODE});

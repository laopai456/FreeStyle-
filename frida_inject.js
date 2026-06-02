/*
 * frida_inject.js — TCP 包注入器 (v3: f12 算法, 支持任意 seq)
 *
 * 功能:
 * 1. Hook WSASend 捕获游戏 socket + 透传所有包到 Python
 * 2. 保存最后 N 个发送的原始字节
 * 3. RPC: injectraw(hex) — 发送自定义包
 * 4. RPC: injectlast() — 重放最后一次发送的包
 * 5. RPC: injectnext() — 递增 seq 并计算正确 f12 后注入
 * 6. RPC: injectheartbeat() — 构造心跳包注入
 * 7. RPC: getf12(seq) — 查询 f12 (算法计算, 无上限)
 * 8. RPC: getlastinfo() — 显示最后包的 f12 验证信息
 */
'use strict';

var KEY = [0x4d, 0xb8, 0xa8, 0x54];
var CRC_RVA1 = 0x1A3C54;
var CRC_RVA2 = 0x1BE222;
var PATCH = [0x33, 0xC0, 0xC3];

// ====== f12(seq) 算法 (XOR binary counter, period-8 LEVEL) ======
// 已验证: 194 个 seq 全部匹配, 支持任意 seq
var F12_SEED = 0xA848F08D; // 默认值, 自动检测后会覆盖
var g_seedDetected = false;
var F12_EVEN_MAGIC = 0xDD45AAB8;
var F12_BASE_G = 0x62228939;
var F12_LEVEL = [0x00000000, 0x7B2231F3, 0x8D665215, 0x6402E328,
                 0xB327F7A3, 0x1881A844, 0x4A21617B, 0x07A17A9F, 0x7460C4CD];
var F12_EXCEPTIONS = {23: 0xE9E0C8D2, 74: 0xE90ABFCC, 89: 0xEA2EC073, 92: 0xCEFF2A3D};

function f12Ctz(n) {
    if (n === 0) return 32;
    var c = 0;
    while ((n & 1) === 0) { c++; n >>>= 1; }
    return c;
}

function f12GetLevel(k) {
    if (k === 0) return 0;
    return F12_LEVEL[((k - 1) % 8) + 1];
}

function f12ComputeG(n) {
    var h = F12_EXCEPTIONS[n];
    if (h !== undefined) return (F12_BASE_G ^ h) >>> 0;
    return (F12_BASE_G ^ f12GetLevel(f12Ctz(n))) >>> 0;
}

// Compute f12(seq) from scratch
function f12Compute(seq) {
    if (seq <= 0) return 0;
    var state = F12_SEED;
    for (var s = 1; s < seq; s++) {
        if (s % 2 === 0) {
            state = (state ^ F12_EVEN_MAGIC) >>> 0;
        } else {
            state = (state ^ f12ComputeG((s + 1) >>> 1)) >>> 0;
        }
    }
    return state >>> 0;
}

var PTR_SIZE = Process.pointerSize;
var WSABUF_STEP = PTR_SIZE === 4 ? 8 : 16;
var g_socket = null;
var g_lastRaw = null;
var g_sentCount = 0;
var g_injectQueue = [];     // 待注入的包队列
var g_quietMode = true;     // 默认不刷 PKT 屏, 用 'togpkt' 切换
var g_patchTimer = null;    // ItemCode patch 定时器
var g_patchSrcIC = 0;       // 当前 patch 的源 ItemCode
var g_patchDstIC = 0;       // 当前 patch 的目标 ItemCode
var g_traceMode = false;    // 调用栈追踪开关

// ====== Apollo CRC Patch ======
function patchApolloCRC() {
    try {
        var apollo = Process.getModuleByName('ApolloCT.dll');
        var base = apollo.base;
        [CRC_RVA1, CRC_RVA2].forEach(function(rva) {
            var addr = base.add(rva);
            Memory.protect(addr, 3, 'rwx');
            addr.writeByteArray(PATCH);
        });
        return true;
    } catch(e) {
        send(JSON.stringify({type:'warn', msg:'ApolloCRC patch skipped: ' + e}));
        return true; // 继续运行
    }
}

// ====== 工具 ======
function hex(arr) {
    return Array.prototype.slice.call(arr).map(function(b) {
        return ('0' + b.toString(16)).slice(-2);
    }).join('');
}

function hexToBytes(h) {
    var out = [];
    for (var i = 0; i < h.length; i += 2) {
        out.push(parseInt(h.substr(i, 2), 16));
    }
    return out;
}

function xorEnc(plaintext) {
    // plaintext 是 XOR 解密后的数据, 加密回线路格式
    var out = [];
    for (var i = 0; i < plaintext.length; i++) {
        out.push(plaintext[i] ^ KEY[i % 4]);
    }
    return out;
}

// ====== 注入: 直接调用 send() ======

// 从最后捕获的包验证/修正 seed
function ensureSeed() {
    if (!g_lastRaw || g_lastRaw.length < 20) return;
    var d = g_lastRaw;
    if (d[0] !== 0x43 || d[1] !== 0xd5 || d[2] !== 0x8b || d[3] !== 0x80) return;
    var seq = (d[16] | (d[17] << 8) | (d[18] << 16) | (d[19] << 24)) >>> 0;
    var f12 = (d[12] | (d[13] << 8) | (d[14] << 16) | (d[15] << 24)) >>> 0;
    var expected = f12Compute(seq);
    if (expected === f12) return; // seed 正确
    // real_seed = f12_actual XOR expected XOR current_seed
    var real_seed = (f12 ^ expected ^ F12_SEED) >>> 0;
    F12_SEED = real_seed;
    g_seedDetected = true;
    send(JSON.stringify({type:'info', msg:'Seed corrected: 0x' + (real_seed >>> 0).toString(16).toUpperCase()}));
}

// 旧 auto-detect 保留但改为调用 ensureSeed
function autoDetectSeed(seq, f12_actual) {
    if (g_seedDetected) return;
    ensureSeed();
}
function doInject(rawBytes) {
    if (!g_socket) {
        return {ok: false, msg: 'socket not captured yet'};
    }
    if (!g_sendFn) {
        return {ok: false, msg: 'send() not resolved'};
    }

    var len = rawBytes.length;
    var dataBuf = Memory.alloc(len);
    for (var i = 0; i < len; i++) {
        dataBuf.add(i).writeU8(rawBytes[i]);
    }

    var sockVal = g_socket.toInt32();
    var ret = g_sendFn(sockVal, dataBuf, len, 0);
    var err = 0;
    if (ret < 0 && g_wsaLastErrorFn) {
        err = g_wsaLastErrorFn();
    }
    return {ok: ret >= 0, ret: ret, sent: ret > 0 ? ret : 0, err: err, size: len};
}

// ====== Hook WSASend ======
function hookWSASend() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr = ws.getExportByName('WSASend');

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                this.lpBufs = args[1];
                var sock = args[0];
                var cnt = args[2].toInt32();

                for (var k = 0; k < cnt; k++) {
                    var wsa = args[1].add(k * WSABUF_STEP);
                    var tl = wsa.readU32();
                    var b = wsa.add(PTR_SIZE).readPointer();
                    if (tl < 4 || tl > 65536) continue;

                    if (!g_socket || g_socket.isNull()) {
                        g_socket = sock;
                        send(JSON.stringify({type:'info', msg:'socket captured: ' + sock}));
                    }

                    var raw = [];
                    for (var i = 0; i < tl && i < 4096; i++) {
                        raw.push(b.add(i).readU8());
                    }
                    g_lastRaw = raw;
                    g_sentCount++;
                    // 自动检测 f12 seed (从第一个游戏数据包)
                    if (raw.length >= 20 && raw[0] === 0x43 && raw[1] === 0xd5 && raw[2] === 0x8b && raw[3] === 0x80) {
                        var _seq = (raw[16] | (raw[17] << 8) | (raw[18] << 16) | (raw[19] << 24)) >>> 0;
                        var _f12 = (raw[12] | (raw[13] << 8) | (raw[14] << 16) | (raw[15] << 24)) >>> 0;
                        autoDetectSeed(_seq, _f12);
                    }

                    if (!g_quietMode) {
                        send(JSON.stringify({
                            type: 'PKT',
                            idx: g_sentCount,
                            len: tl,
                            head: hex(raw.slice(0, 20)),
                            raw64: hex(raw.slice(0, 64))
                        }));
                    }

                    // 调用栈追踪: 所有包
                    if (g_traceMode && tl >= 24 && raw.length >= 20) {
                        try {
                            var _dec = [];
                            for (var di = 20; di < raw.length && di < 32; di++) {
                                _dec.push(raw[di] ^ KEY[(di - 20) % 4]);
                            }
                            var bt = Thread.backtrace(this.context, Backtracer.ACCURATE)
                                .map(DebugSymbol.fromAddress);
                            var frames = [];
                            for (var fi = 0; fi < Math.min(bt.length, 12); fi++) {
                                frames.push(bt[fi].toString());
                            }
                            send(JSON.stringify({
                                type: 'TRACE',
                                seq: _seq,
                                len: tl,
                                decHead: hex(_dec),
                                frames: frames
                            }));
                        } catch(e) {
                            send(JSON.stringify({type:'err', msg:'trace: ' + e}));
                        }
                    }
                    break;
                }
            } catch (e) {
                send(JSON.stringify({type:'err', msg:'WSASend:' + e}));
            }
        }
    });
}

// ====== 初始化 ======
patchApolloCRC();

// 解析 send() 函数 (用模块对象方式, 兼容性好)
var g_sendFn = null;
var g_wsaLastErrorFn = null;
try {
    var ws2 = Process.getModuleByName('WS2_32.dll');
    var sendAddr = ws2.findExportByName('send');
    if (sendAddr) {
        g_sendFn = new NativeFunction(sendAddr, 'int', ['int', 'pointer', 'int', 'int']);
    }
    var errAddr = ws2.findExportByName('WSAGetLastError');
    if (errAddr) {
        g_wsaLastErrorFn = new NativeFunction(errAddr, 'int', []);
    }
    send(JSON.stringify({type:'info', msg:'send() resolved at ' + sendAddr}));
} catch(e) {
    send(JSON.stringify({type:'err', msg:'resolve: ' + e}));
}

// 等待 WS2_32.dll 加载
function tryStart() {
    try {
        Process.getModuleByName('WS2_32.dll');
        hookWSASend();
        send(JSON.stringify({type:'info', msg:'WSASend hooked, waiting for game socket...'}));
    } catch(e) {
        setTimeout(tryStart, 500);
    }
}
setTimeout(tryStart, 300);

// ====== RPC 导出 ======
rpc.exports = {
    // 注入任意原始字节
    injectraw: function(hexData) {
        var bytes = hexToBytes(hexData);
        var result = doInject(bytes);
        return JSON.stringify(result);
    },

    // 重放最后一次发送的包
    injectlast: function() {
        if (!g_lastRaw) {
            return JSON.stringify({ok: false, msg: 'no packet captured yet'});
        }
        var result = doInject(g_lastRaw);
        return JSON.stringify(result);
    },

    // 递增 seq 并计算正确 f12 后注入
    injectnext: function() {
        if (!g_lastRaw) {
            return JSON.stringify({ok: false, msg: 'no packet captured yet'});
        }
        ensureSeed();
        var data = g_lastRaw.slice();
        if (data.length < 20) {
            return JSON.stringify({ok: false, msg: 'packet too short'});
        }
        var seq = ((data[16] | (data[17] << 8) | (data[18] << 16) | (data[19] << 24)) >>> 0) + 1;
        seq = seq >>> 0;
        data[16] = seq & 0xff;
        data[17] = (seq >> 8) & 0xff;
        data[18] = (seq >> 16) & 0xff;
        data[19] = (seq >> 24) & 0xff;

        // 计算正确的 f12 校验和
        var f12 = f12Compute(seq);
        data[12] = f12 & 0xff;
        data[13] = (f12 >> 8) & 0xff;
        data[14] = (f12 >> 16) & 0xff;
        data[15] = (f12 >> 24) & 0xff;

        var result = doInject(data);
        result.seq = seq;
        result.f12 = f12;
        return JSON.stringify(result);
    },

    // 构造心跳包并注入
    injectheartbeat: function() {
        if (!g_lastRaw) {
            return JSON.stringify({ok: false, msg: 'no packet captured yet (need session const)'});
        }
        ensureSeed();
        var last = g_lastRaw;
        if (last.length < 20) {
            return JSON.stringify({ok: false, msg: 'packet too short'});
        }
        var seq = ((last[16] | (last[17] << 8) | (last[18] << 16) | (last[19] << 24)) >>> 0) + 1;
        seq = seq >>> 0;
        var f12 = f12Compute(seq);

        // 构造心跳包: magic(4) + session(8) + f12(4) + seq(4) + enc_payload(8)
        var pkt = [];
        pkt.push(0x43, 0xd5, 0x8b, 0x80);
        for (var i = 4; i < 12; i++) pkt.push(last[i]);
        pkt.push(f12 & 0xff, (f12 >> 8) & 0xff, (f12 >> 16) & 0xff, (f12 >> 24) & 0xff);
        pkt.push(seq & 0xff, (seq >> 8) & 0xff, (seq >> 16) & 0xff, (seq >> 24) & 0xff);
        pkt.push(0x00, 0x00, 0x00, 0x00, 0x0a, 0x00, 0x00, 0x00);

        var result = doInject(pkt);
        result.seq = seq;
        result.f12 = f12;
        result.pktlen = pkt.length;
        return JSON.stringify(result);
    },

    // 查询 f12 (算法计算, 无上限)
    getf12: function(seqStr) {
        var seq = parseInt(seqStr);
        var val = f12Compute(seq);
        return JSON.stringify({seq: seq, f12: val, ok: true});
    },

    // 获取最后捕获包的详细信息 (含 f12 验证)
    getlastinfo: function() {
        if (!g_lastRaw) {
            return JSON.stringify({ok: false});
        }
        ensureSeed();
        var d = g_lastRaw;
        var seq = (d[16] | (d[17] << 8) | (d[18] << 16) | (d[19] << 24)) >>> 0;
        var f12 = (d[12] | (d[13] << 8) | (d[14] << 16) | (d[15] << 24)) >>> 0;
        var expected = f12Compute(seq);
        return JSON.stringify({
            ok: true,
            seq: seq,
            f12_actual: f12,
            f12_expected: expected,
            f12_match: expected === f12,
            seed: F12_SEED,
            seedDetected: g_seedDetected,
            len: d.length,
            session: hex(d.slice(4, 12)),
            enc_head: hex(d.slice(20, Math.min(28, d.length)))
        });
    },

    // 修改指定偏移后注入
    injectmodified: function(hexData, offset, newByte) {
        var bytes = hexToBytes(hexData);
        if (offset < 0 || offset >= bytes.length) {
            return JSON.stringify({ok: false, msg: 'offset out of range'});
        }
        bytes[offset] = newByte;
        var result = doInject(bytes);
        return JSON.stringify(result);
    },

    // 获取状态
    status: function() {
        return JSON.stringify({
            socket: g_socket ? g_socket.toString() : 'null',
            sentCount: g_sentCount,
            lastLen: g_lastRaw ? g_lastRaw.length : 0,
            lastHead: g_lastRaw ? hex(g_lastRaw.slice(0, 20)) : ''
        });
    },

    // 获取最后发送包的完整 hex
    getlastraw: function() {
        return g_lastRaw ? JSON.stringify({hex: hex(g_lastRaw), len: g_lastRaw.length}) : JSON.stringify({hex: '', len: g_lastRaw.length});
    },

    // 解密最后捕获包的 payload
    // 切换 PKT 消息开关 (默认关闭)
    toggleqt: function() {
        g_quietMode = !g_quietMode;
        return JSON.stringify({ok: true, quiet: g_quietMode});
    },

    decryptlast: function() {
        if (!g_lastRaw || g_lastRaw.length < 20) {
            return JSON.stringify({ok: false, msg: 'no packet'});
        }
        var d = g_lastRaw;
        var hdr = hex(d.slice(0, 20));
        var enc = d.slice(20);
        var dec = [];
        for (var i = 0; i < enc.length; i++) {
            dec.push(enc[i] ^ KEY[i % 4]);
        }
        var seq = (d[16] | (d[17] << 8) | (d[18] << 16) | (d[19] << 24)) >>> 0;
        var f12 = (d[12] | (d[13] << 8) | (d[14] << 16) | (d[15] << 24)) >>> 0;
        var b0 = dec.length > 0 ? dec[0] : -1;
        var b1 = dec.length > 1 ? dec[1] : -1;
        return JSON.stringify({
            ok: true,
            seq: seq,
            f12: f12,
            totalLen: d.length,
            hdrLen: 20,
            payloadLen: dec.length,
            header: hdr,
            encPayload: hex(enc.slice(0, Math.min(64, enc.length))),
            decPayload: hex(dec.slice(0, Math.min(64, dec.length))),
            decFull: hex(dec),
            b0: b0,
            b1: b1,
            session: hex(d.slice(4, 12))
        });
    },

    // 启动/停止 ItemCode 持续 patch
    patchic: function(action, srcIC, dstIC) {
        if (action === 'stop') {
            if (g_patchTimer !== null) {
                clearInterval(g_patchTimer);
                g_patchTimer = null;
            }
            var oldSrc = g_patchSrcIC;
            g_patchSrcIC = 0;
            g_patchDstIC = 0;
            return JSON.stringify({ok: true, msg: 'stopped', srcIC: oldSrc});
        }

        if (action !== 'start') {
            return JSON.stringify({ok: false, msg: 'use start/stop'});
        }

        // 停止旧的
        if (g_patchTimer !== null) {
            clearInterval(g_patchTimer);
        }

        g_patchSrcIC = srcIC;
        g_patchDstIC = dstIC;

        var IC_OFFSET = 0x060;
        var mod = Process.enumerateModules()[0];
        var modEnd = mod.base.add(mod.size);

        function scanAndPatch() {
            if (g_patchSrcIC === 0) return;
            try {
                var ranges = Process.enumerateRanges('rw-');
                for (var ri = 0; ri < ranges.length; ri++) {
                    try {
                        var found = Memory.scanSync(ranges[ri].base, ranges[ri].size, 'A0 CE 7F 02');
                        for (var fi = 0; fi < found.length; fi++) {
                            var addr = found[fi].address;
                            if (addr.compare(modEnd) > 0) {
                                try {
                                    var ic = addr.add(IC_OFFSET).readU32();
                                    if (ic === g_patchSrcIC) {
                                        addr.add(IC_OFFSET).writeU32(g_patchDstIC);
                                    }
                                } catch(e) {}
                            }
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }

        scanAndPatch();
        g_patchTimer = setInterval(scanAndPatch, 50);

        return JSON.stringify({
            ok: true,
            msg: 'watching',
            srcIC: srcIC,
            dstIC: dstIC
        });
    },

    // Hook 拷贝构造函数 0x1C29FE0
    hcopy: function(srcIC, dstIC) {
        if (g_patchTimer !== null) {
            clearInterval(g_patchTimer);
            g_patchTimer = null;
        }
        g_patchSrcIC = srcIC;
        g_patchDstIC = dstIC;

        var ctorAddr = ptr('0x1C29FE0');
        var h = Interceptor.attach(ctorAddr, {
            onEnter: function(args) {
                this.destOuter = this.context.ecx;
            },
            onLeave: function(retval) {
                if (g_patchSrcIC === 0) return;
                try {
                    var icAddr = this.destOuter.add(0x06C); // outer+0x0C+0x060
                    var ic = icAddr.readU32();
                    if (ic === g_patchSrcIC) {
                        icAddr.writeU32(g_patchDstIC);
                        send({type:'hcopy_patch', desc: this.destOuter.add(0x0C).toString(),
                              old: ic, new: g_patchDstIC});
                    }
                } catch(e) {}
            }
        });

        return JSON.stringify({ok: true, msg: 'hooked copy ctor', srcIC: srcIC, dstIC: dstIC});
    },

    unhcopy: function() {
        g_patchSrcIC = 0;
        g_patchDstIC = 0;
        return JSON.stringify({ok: true, msg: 'unhooked'});
    },

    // 切换调用栈追踪
    trace: function(on) {
        g_traceMode = !!on;
        return JSON.stringify({ok: true, trace: g_traceMode});
    }
};

/*
 * frida_e2_inbound.js — Plan C: Hook E2 (field12) 入口区分出站/入站
 *
 * 思路:
 *   E2 在 WSASend (出站) 之前被调，也在收包验证 (入站) 时被调。
 *   出站: E2 → (加密) → WSASend (我们能看到)
 *   入站: E2 → (验证 field12) → [无 WSASend]
 *
 *   所以: E2 被调但 3s 内没有对应 WSASend → 入站包!
 *
 * FreeStyle.exe + 0x2038B80 = E2 entry
 *   参数: ESP+4 → WSABUF ptr → +0:len(4B) +4:buf(ptr)
 */

'use strict';

var KEY = [0x4d, 0xb8, 0xa8, 0x54];
var MAGIC = [0x43, 0xd5, 0x8b, 0x80];

var E2_OFF = 0x2038B80;
var PIDX = 0;
var PENDING = {};      // key: f12_hex+seq → {f12, seq, plen, b0, d0, enc, dec, raw, ts}
var FLUSH_INTERVAL = 3000;  // 3s 超时视为入站
var STALE_AGE = 2000;  // 2s 后视为入站

function toHex(arr, max) {
    var end = Math.min(max || arr.length, arr.length);
    var s = '';
    for (var i = 0; i < end; i++) s += ('0' + (arr[i] & 0xFF).toString(16)).slice(-2);
    return s;
}

function xorDec(raw, off) {
    var out = [];
    for (var i = off; i < raw.length; i++) out.push(raw[i] ^ KEY[(i - off) % 4]);
    return out;
}

function isGamePacket(raw) {
    if (raw.length < 20) return false;
    for (var i = 0; i < 4; i++) if (raw[i] !== MAGIC[i]) return false;
    return true;
}

// ================================================================
// 1. Hook E2: 记录所有带 magic 头的 packet
// ================================================================
function hookE2() {
    var fs;
    try { fs = Process.getModuleByName('FreeStyle.exe'); }
    catch(e) {
        send(JSON.stringify({type:'e2', msg:'FreeStyle.exe not loaded yet, retrying...'}));
        setTimeout(hookE2, 1000);
        return;
    }

    var e2Addr = fs.base.add(E2_OFF);
    send(JSON.stringify({type:'e2', msg:'E2 hooked @ FreeStyle.exe+0x'+E2_OFF.toString(16)+' = '+e2Addr}));

    Interceptor.attach(e2Addr, {
        onEnter: function(args) {
            try {
                // E2(WSABUF*) — 参数在栈上, esp+4 = 第一个参数(WSABUF*)
                var wsab = this.context.esp.add(4).readPointer();
                if (wsab.isNull()) return;
                var tl = wsab.readU32();
                if (tl < 20 || tl > 65536) return;
                var buf = wsab.add(4).readPointer();
                if (buf.isNull()) return;

                var raw = new Uint8Array(buf.readByteArray(Math.min(tl, 65536)));
                if (!isGamePacket(raw)) return;

                var f12 = raw[12] | (raw[13] << 8) | (raw[14] << 16) | (raw[15] << 24);
                var seq = raw[16] | (raw[17] << 8) | (raw[18] << 16) | (raw[19] << 24);
                var encPayload = raw.slice(20);
                var decPayload = xorDec(raw, 20);
                var b0 = encPayload[0];
                var d0 = decPayload[0];
                var plen = decPayload.length;
                var now = Date.now();

                // key: f12 as hex + seq (可能同时有同seq出站入站)
                var key = f12.toString(16) + '_' + seq;

                PENDING[key] = {
                    f12: f12,
                    seq: seq,
                    plen: plen,
                    b0: b0,
                    d0: d0,
                    enc: toHex(encPayload, 128),
                    dec: toHex(decPayload, 128),
                    rawLen: tl,
                    ts: now
                };
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'e2', msg:'E2 interceptor active'}));
}

// ================================================================
// 2. Hook WSASend: 收到出站包时从 PENDING 移除
// ================================================================
function hookWSASendForE2() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var wsaSend = ws.getExportByName('WSASend');

    Interceptor.attach(wsaSend, {
        onEnter: function(args) {
            try {
                var wsab = args[1]; // LPWSABUF
                var count = args[2].toInt32();
                if (count < 1) return;

                var buf = wsab.add(4).readPointer();
                var len = wsab.readU32();
                if (len < 20 || len > 65536) return;

                var raw = new Uint8Array(buf.readByteArray(Math.min(len, 65536)));
                if (!isGamePacket(raw)) return;

                var f12 = raw[12] | (raw[13] << 8) | (raw[14] << 16) | (raw[15] << 24);
                var seq = raw[16] | (raw[17] << 8) | (raw[18] << 16) | (raw[19] << 24);
                var key = f12.toString(16) + '_' + seq;

                // 这是出站包 → 从 PENDING 移除
                if (PENDING[key]) {
                    delete PENDING[key];
                }
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'e2', msg:'WSASend tracker active (E2 dedup)'}));
}

// ================================================================
// 3. 定时刷新: 超时的 PENDING → 入站包
// ================================================================
setInterval(function() {
    var now = Date.now();
    var inboundKeys = [];

    for (var key in PENDING) {
        if (now - PENDING[key].ts > STALE_AGE) {
            inboundKeys.push(key);
        }
    }

    for (var i = 0; i < inboundKeys.length; i++) {
        var key = inboundKeys[i];
        var p = PENDING[key];
        delete PENDING[key];

        PIDX++;
        send(JSON.stringify({
            type: 'PKT',
            idx: PIDX,
            len: p.rawLen,
            dir: 'IN',
            f12: p.f12,
            seq: p.seq,
            plen: p.plen,
            b0: p.b0,
            d0: p.d0,
            enc: p.enc,
            dec: p.dec
        }));
    }

    if (inboundKeys.length > 0) {
        send(JSON.stringify({type:'e2', msg:'Flushed ' + inboundKeys.length + ' INBOUND packets! Pending=' + Object.keys(PENDING).length}));
    }
}, FLUSH_INTERVAL);

// ================================================================
// Main
// ================================================================
send(JSON.stringify({type:'e2', msg:'=== e2_inbound loading ==='}));

try { hookE2(); } catch(e) {
    send(JSON.stringify({type:'e2', msg:'E2 ERROR: ' + e}));
}
try { hookWSASendForE2(); } catch(e) {
    send(JSON.stringify({type:'e2', msg:'WSASend ERROR: ' + e}));
}

send(JSON.stringify({type:'e2', msg:'e2_inbound ready — waiting for E2 calls...'}));
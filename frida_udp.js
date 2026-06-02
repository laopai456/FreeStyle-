/*
 * frida_udp.js — Hook UDP sendto/recvfrom 捕获游戏 UDP 流量
 *
 * 原理:
 *   游戏 TCP (登录) 走 TLS, 真正游戏数据走 UDP
 *   sendto → C2S UDP (出站, 加密) 
 *   recvfrom → S2C UDP (入站, 加密)
 *   加密数据和 pcap 对照即可推导 key
 *
 * C2S magic: 907f (2 bytes)
 * S2C magic: 第1字节 = opcode (17/80/82/AF/8F)
 */

'use strict';

var PIDX = 0;
var C2S_MAGIC = [0x90, 0x7f];

function toHex(arr) {
    var s = '';
    for (var i = 0; i < arr.length; i++) s += ('0' + (arr[i] & 0xFF).toString(16)).slice(-2);
    return s;
}

function isUdpClient(raw) {
    return raw.length >= 2 && raw[0] === C2S_MAGIC[0] && raw[1] === C2S_MAGIC[1];
}

// 如果 data 看起来像加密的 S2C 包, 返回 true
// S2C 特征: B[0] in {0x17,0x80,0x82,0xAF,0x8F,0x81,0x00,0x01}, B[4:6]=0x0000, B[6:8]=0x0001 
function looksLikeServer(raw) {
    if (raw.length < 8) return false;
    var op = raw[0];
    var validOps = {0x17:1, 0x80:1, 0x82:1, 0xAF:1, 0x8F:1, 0x81:1, 0x00:1, 0x01:1};
    return (op in validOps);
}

// ================================================================
// Hook sendto: C2S UDP
//   int sendto(SOCKET s, const char *buf, int len, int flags,
//              const struct sockaddr *to, int tolen);
//   x64: rcx=s, rdx=buf, r8=len, r9=flags
// ================================================================
function hookSendto() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('sendto'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'sendto NOT FOUND in WS2_32 (game may use WSASendTo)'}));
        return;
    }

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var buf = args[1];
                var len = args[2].toInt32();
                if (len < 8 || len > 65536) return;
                var raw = new Uint8Array(buf.readByteArray(Math.min(len, 4096)));
                
                // 只匹配 C2S magic 907f
                if (!isUdpClient(raw)) return;
                
                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: len,
                    dir: 'OUT',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: len - 16,  // UDP 无 f12/seq
                    b0: raw[2] || 0,          // seq_lo
                    d0: raw[0],                // magic_hi
                    enc: toHex(raw),
                    dec: '?'  // 加密的, 未知明文
                }));
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'sendto hooked'}));
}

// ================================================================
// Hook WSASendTo: C2S UDP via WSA API
// ================================================================
function hookWSASendTo() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('WSASendTo'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'WSASendTo NOT FOUND'}));
        return;
    }

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var wsab = args[1];     // LPWSABUF
                var count = args[2].toInt32();
                if (count < 1) return;
                var len = wsab.readU32();
                if (len < 8 || len > 65536) return;
                var buf = wsab.add(4).readPointer();
                var raw = new Uint8Array(buf.readByteArray(Math.min(len, 4096)));
                
                if (!isUdpClient(raw)) return;
                
                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: len,
                    dir: 'OUT',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: len - 16,
                    b0: raw[2] || 0,
                    d0: raw[0],
                    enc: toHex(raw),
                    dec: '?'
                }));
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'WSASendTo hooked'}));
}

// ================================================================
// Hook recvfrom: S2C UDP ★ 关键!
//   int recvfrom(SOCKET s, char *buf, int len, int flags,
//                struct sockaddr *from, int *fromlen);
//   x64: rcx=s, rdx=buf, r8=len, r9=flags
//   onLeave: ret = bytes_received, buf contains data
// ================================================================
function hookRecvfrom() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('recvfrom'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'recvfrom NOT FOUND'}));
        return;
    }

    var recvCount = 0;
    var recvGameCount = 0;

    Interceptor.attach(addr, {
        onEnter: function(args) {
            // 保存 buf 指针 + len 到 this
            this.buf = args[1];
            this.len = args[2].toInt32();
        },
        onLeave: function(retval) {
            try {
                var bytes = retval.toInt32();
                if (bytes <= 0 || bytes < 8 || !this.buf || this.buf.isNull()) return;

                recvCount++;
                var raw = new Uint8Array(this.buf.readByteArray(Math.min(bytes, 4096)));

                if (!looksLikeServer(raw)) return;

                recvGameCount++;
                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: bytes,
                    dir: 'IN',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: bytes,
                    b0: raw[1] || 0,         // sub-opcode
                    d0: raw[0],               // opcode
                    enc: toHex(raw),
                    dec: '?'
                }));

                // 每 50 个报一次
                if (recvGameCount % 50 === 0) {
                    send(JSON.stringify({type:'udp', msg:'recvfrom: ' + recvGameCount + ' IN pkts'}));
                }
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'recvfrom hooked'}));
}

// ================================================================
// Hook WSARecvFrom: S2C UDP via WSA
// ================================================================
function hookWSARecvFrom() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('WSARecvFrom'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'WSARecvFrom NOT FOUND'}));
        return;
    }

    // WSARecvFrom 是 overlapped I/O, 数据到达时才触发
    // 我们只在 onEnter 上尝试 (有些实现是同步的)
    var wsrvCount = 0;
    var wsrvGameCount = 0;

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var wsab = args[1];     // LPWSABUF
                var count = args[2].toInt32();
                if (count < 1) return;
                var len = wsab.readU32();
                // 暂存, 等调用完成后读

                // WSARecvFrom 是 overlapped, 数据在 onLeave 还没有
                // 只在 buffered 模式下能读
                // 用 IOCP 的话, 数据在 GetQueuedCompletionStatus 后
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'WSARecvFrom hooked (monitoring only)'}));
}

// ================================================================
// Hook send: C2S UDP (connected socket, not sendto)
//   int send(SOCKET s, const char *buf, int len, int flags);
//   x64: rcx=s, rdx=buf, r8=len, r9=flags
// ================================================================
function hookSend() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('send'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'send NOT FOUND'}));
        return;
    }

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var buf = args[1];
                var len = args[2].toInt32();
                if (len < 8 || len > 65536) return;
                var raw = new Uint8Array(buf.readByteArray(Math.min(len, 4096)));

                if (!isUdpClient(raw)) return;

                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: len,
                    dir: 'OUT',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: len - 16,
                    b0: raw[2] || 0,
                    d0: raw[0],
                    enc: toHex(raw),
                    dec: '?'
                }));
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'send hooked (connected UDP)'}));
}

// ================================================================
// Hook recv: S2C UDP (connected socket)
//   int recv(SOCKET s, char *buf, int len, int flags);
//   x64: rcx=s, rdx=buf, r8=len, r9=flags
//   onLeave: ret = bytes_received
// ================================================================
function hookRecv() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('recv'); } catch(e) {}
    if (!addr) {
        send(JSON.stringify({type:'udp', msg:'recv NOT FOUND'}));
        return;
    }

    var recvCount2 = 0;
    var recvGameCount2 = 0;

    Interceptor.attach(addr, {
        onEnter: function(args) {
            this.buf = args[1];
            this.len = args[2].toInt32();
        },
        onLeave: function(retval) {
            try {
                var bytes = retval.toInt32();
                if (bytes <= 0 || bytes < 8 || !this.buf || this.buf.isNull()) return;

                recvCount2++;
                var raw = new Uint8Array(this.buf.readByteArray(Math.min(bytes, 4096)));

                if (!looksLikeServer(raw)) return;

                recvGameCount2++;
                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: bytes,
                    dir: 'IN',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: bytes,
                    b0: raw[1] || 0,
                    d0: raw[0],
                    enc: toHex(raw),
                    dec: '?'
                }));

                if (recvGameCount2 % 50 === 0) {
                    send(JSON.stringify({type:'udp', msg:'recv (connected): ' + recvGameCount2 + ' IN pkts'}));
                }
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'udp', msg:'recv hooked (connected UDP)'}));
}

// ================================================================
// Hook WSASend: C2S UDP (connected socket, uses WSASend not WSASendTo)
// ================================================================
var wsaSendUdpCount = 0;
function hookWSASendUDP() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('WSASend'); } catch(e) {}
    if (!addr) return;

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var wsab = args[1];
                var count = args[2].toInt32();
                if (count < 1) return;
                var len = wsab.readU32();
                if (len < 8 || len > 65536) return;
                var buf = wsab.add(4).readPointer();
                if (buf.isNull()) return;
                var raw = new Uint8Array(buf.readByteArray(Math.min(len, 4096)));

                if (!isUdpClient(raw)) return;

                wsaSendUdpCount++;
                PIDX++;
                send(JSON.stringify({
                    type: 'PKT',
                    idx: PIDX,
                    len: len,
                    dir: 'OUT',
                    proto: 'UDP',
                    f12: 0, seq: 0, plen: len - 16,
                    b0: raw[2] || 0,
                    d0: raw[0],
                    enc: toHex(raw),
                    dec: '?'
                }));
            } catch(e) {}
        }
    });
}

// ================================================================
// Heartbeat — 周期性报告
// ================================================================
var hbSent = 0, hbRecv = 0;
setInterval(function() {
    send(JSON.stringify({type:'udp_heartbeat', hb: 1}));
}, 15000);

// ================================================================
// Main
// ================================================================
send(JSON.stringify({type:'udp', msg:'=== frida_udp loading ==='}));

try { hookSendto(); } catch(e) { send(JSON.stringify({type:'udp', msg:'sendto error: '+e})); }
try { hookWSASendTo(); } catch(e) { send(JSON.stringify({type:'udp', msg:'WSASendTo error: '+e})); }
try { hookRecvfrom(); } catch(e) { send(JSON.stringify({type:'udp', msg:'recvfrom error: '+e})); }
try { hookWSARecvFrom(); } catch(e) { send(JSON.stringify({type:'udp', msg:'WSARecvFrom error: '+e})); }
try { hookSend(); } catch(e) { send(JSON.stringify({type:'udp', msg:'send error: '+e})); }
try { hookRecv(); } catch(e) { send(JSON.stringify({type:'udp', msg:'recv error: '+e})); }
try { hookWSASendUDP(); } catch(e) { send(JSON.stringify({type:'udp', msg:'WSASend_UDP error: '+e})); }

send(JSON.stringify({type:'udp', msg:'frida_udp ready (7 hooks)'}));
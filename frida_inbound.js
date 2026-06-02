/*
 * frida_inbound.js — 入站包捕获
 * 
 * 策略:
 * 1. Hook WSARecv → 记录 socket→(WSABUF ptr, count) 映射
 * 2. Hook WSAGetOverlappedResult → 成功时读 WSABUF 中已填充的数据
 * 3. Hook recvfrom / WSARecvFrom → 直接 onLeave 读数据
 * 4. Hook GetQueuedCompletionStatus → 诊断日志 (确认是否 IOCP)
 * 
 * 与 frida_monitor.js 配套使用 (复用其 isGamePacket + extractPacket)
 */

'use strict';

var KEY = [0x4d, 0xb8, 0xa8, 0x54];
var PIDX = 0;
var MAGIC = [0x43, 0xd5, 0x8b, 0x80];

// === 保存 WSARecv 的缓冲区 (keyed by socket pointer) ===
// gRecvBufs[socket_str] = { bufPtr, bufLen }
var gRecvBufs = {};
var IN_COUNT = 0;

function socketKey(sock) {
    return sock.toString();
}

function hex(arr, max) {
    var end = max || arr.length;
    return Array.prototype.slice.call(arr, 0, end).map(function(b) {
        return ('0' + b.toString(16)).slice(-2);
    }).join('');
}

function xorDec(raw, off) {
    var out = [];
    for (var i = off; i < raw.length; i++) {
        out.push(raw[i] ^ KEY[(i - off) % 4]);
    }
    return out;
}

function isGamePacket(raw) {
    if (raw.length < 20) return false;
    for (var i = 0; i < 4; i++) {
        if (raw[i] !== MAGIC[i]) return false;
    }
    return true;
}

function extractPacket(raw) {
    var f12u = raw[12] | (raw[13] << 8) | (raw[14] << 16) | (raw[15] << 24);
    var seq  = raw[16] | (raw[17] << 8) | (raw[18] << 16) | (raw[19] << 24);
    var encPayload = raw.slice(20);
    var decPayload = xorDec(raw, 20);

    PIDX++;
    return {
        type: 'PKT',
        idx: PIDX,
        len: raw.length,
        f12: f12u,
        seq: seq,
        plen: decPayload.length,
        b0: raw[20],
        d0: decPayload[0],
        enc: hex(encPayload, 64),
        dec: hex(decPayload, 64),
        raw: hex(raw, -1)
    };
}

function processIncoming(raw, bufLen) {
    var len = Math.min(bufLen, raw.length, 4096);
    if (len < 20) return;
    if (!isGamePacket(raw)) return;
    IN_COUNT++;
    var pkt = extractPacket(raw);
    pkt.dir = 'IN';
    send(JSON.stringify(pkt));
}

// 从 WSABUF 结构读数据
function readWSABuf(lpBufs, idx) {
    // WSABUF: len(u32, offset 0) + buf(ptr, offset 4) = 8 bytes
    var wsa = lpBufs.add(idx * 8);
    var tl = wsa.readU32();
    var b = wsa.add(4).readPointer();
    if (tl === 0 || tl > 65536) return null;
    try {
        return { raw: new Uint8Array(b.readByteArray(Math.min(tl, 4096))), len: tl };
    } catch(e) {
        return null;
    }
}

// ====== 1. Hook WSARecv → 记录缓冲区 ======
function hookWSARecv() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var wsr = ws.getExportByName('WSARecv');

    Interceptor.attach(wsr, {
        onEnter: function(args) {
            // int WSARecv(SOCKET s, LPWSABUF lpBuffers, DWORD dwBufferCount,
            //     LPDWORD lpNumberOfBytesRecvd, LPDWORD lpFlags,
            //     LPWSAOVERLAPPED lpOverlapped,
            //     LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine);
            try {
                var sock = args[0];
                var lpBufs = args[1];
                var cnt = args[2].toInt32();

                // 只保存第一个 WSABUF (通常只有一个)
                if (cnt > 0 && !lpBufs.isNull()) {
                    var wsa = lpBufs;
                    var tl = wsa.readU32();
                    var buf = wsa.add(4).readPointer();

                    if (tl > 0 && tl <= 65536) {
                        gRecvBufs[socketKey(sock)] = {
                            bufPtr: buf,
                            bufLen: tl,
                            lpBufs: lpBufs,
                            cnt: cnt
                        };
                    }
                }
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'inbound_log', msg:'WSARecv hooked (tracking buffers)'}));
}

// ====== 2. Hook WSAGetOverlappedResult → 读数据 ======
function hookWSAGetOverlappedResult() {
    var ws = Process.getModuleByName('WS2_32.dll');

    try {
        var gor = ws.getExportByName('WSAGetOverlappedResult');
        Interceptor.attach(gor, {
            onEnter: function(args) {
                // BOOL WSAGetOverlappedResult(SOCKET s, LPWSAOVERLAPPED lpOverlapped,
                //     LPDWORD lpcbTransfer, BOOL fWait, LPDWORD lpdwFlags);
                this.sock = args[0];
                this.lpcbTransfer = args[2];
            },
            onLeave: function(retval) {
                if (!retval.toInt32()) return; // FALSE = error

                try {
                    var sockKey = socketKey(this.sock);
                    var info = gRecvBufs[sockKey];
                    if (!info) return;

                    var transferred = this.lpcbTransfer.readU32();
                    if (transferred === 0 || transferred > 65536) return;

                    // 读缓冲区
                    var raw = new Uint8Array(info.bufPtr.readByteArray(Math.min(transferred, info.bufLen, 4096)));
                    if (isGamePacket(raw)) {
                        processIncoming(raw, transferred);
                    }
                } catch(e) {}
            }
        });
        send(JSON.stringify({type:'inbound_log', msg:'WSAGetOverlappedResult hooked'}));
    } catch(e) {
        send(JSON.stringify({type:'inbound_err', msg:'WSAGetOverlappedResult: ' + e}));
    }
}

// ====== 3. Hook GetQueuedCompletionStatus → 诊断 IOCP ======
function hookGetQueuedCompletionStatus() {
    try {
        var k32 = Process.getModuleByName('kernel32.dll');
        var gqcs = k32.getExportByName('GetQueuedCompletionStatus');

        var gqcsCount = 0;
        Interceptor.attach(gqcs, {
            onEnter: function(args) {
                this.port = args[0];
                this.lpBytes = args[1];
                this.lpKey = args[2];
                this.lpOverlapped = args[3];
            },
            onLeave: function(retval) {
                gqcsCount++;
                if (!retval.toInt32()) return; // FALSE = error/timeout

                var bytes = this.lpBytes.readU32();
                if (bytes > 0) {
                    // 每 100 次才报告一次，避免刷屏
                    if (gqcsCount % 50 === 1) {
                        send(JSON.stringify({
                            type: 'iocp',
                            count: gqcsCount,
                            bytes: bytes,
                            key: this.lpKey.readU32()
                        }));
                    }
                }
            }
        });
        send(JSON.stringify({type:'inbound_log', msg:'GetQueuedCompletionStatus hooked (IOCP monitor)'}));
    } catch(e) {
        send(JSON.stringify({type:'inbound_err', msg:'GetQueuedCompletionStatus: ' + e}));
    }
}

// ====== 4. Hook recvfrom (UDP-style) ======
function hookRecvFrom() {
    var ws = Process.getModuleByName('WS2_32.dll');

    try {
        var rf = ws.getExportByName('recvfrom');
        Interceptor.attach(rf, {
            onEnter: function(args) {
                this.buf = args[1];
                this.len = args[2].toInt32();
            },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0 || n > 65536) return;
                try {
                    var raw = new Uint8Array(this.buf.readByteArray(Math.min(n, this.len, 4096)));
                    if (isGamePacket(raw)) {
                        processIncoming(raw, n);
                    }
                } catch(e) {}
            }
        });
        send(JSON.stringify({type:'inbound_log', msg:'recvfrom hooked'}));
    } catch(e) {
        send(JSON.stringify({type:'inbound_err', msg:'recvfrom: ' + e}));
    }
}

// ====== 5. Hook WSARecvFrom ======
function hookWSARecvFrom() {
    var ws = Process.getModuleByName('WS2_32.dll');

    try {
        var wrf = ws.getExportByName('WSARecvFrom');
        Interceptor.attach(wrf, {
            onEnter: function(args) {
                // int WSARecvFrom(SOCKET s, LPWSABUF lpBuffers, DWORD dwBufferCount,
                //     LPDWORD lpNumberOfBytesRecvd, LPDWORD lpFlags,
                //     struct sockaddr* lpFrom, LPINT lpFromlen,
                //     LPWSAOVERLAPPED lpOverlapped,
                //     LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine);
                var sock = args[0];
                var lpBufs = args[1];
                var cnt = args[2].toInt32();

                if (cnt > 0 && !lpBufs.isNull()) {
                    var wsa = lpBufs;
                    var tl = wsa.readU32();
                    var buf = wsa.add(4).readPointer();
                    if (tl > 0 && tl <= 65536) {
                        gRecvBufs[socketKey(sock)] = {
                            bufPtr: buf,
                            bufLen: tl,
                            lpBufs: lpBufs,
                            cnt: cnt
                        };
                    }
                }
            },
            onLeave: function(retval) {
                // 同步完成 (retval == 0) → 读数据
                if (retval.toInt32() !== 0) return; // pending or error

                var sockKey = socketKey(this.sock || args[0]);
                var info = gRecvBufs[sockKey];
                if (!info) return;
                try {
                    var raw = new Uint8Array(info.bufPtr.readByteArray(Math.min(info.bufLen, 4096)));
                    if (isGamePacket(raw)) {
                        processIncoming(raw, info.bufLen);
                    }
                } catch(e) {}
            }
        });
        send(JSON.stringify({type:'inbound_log', msg:'WSARecvFrom hooked'}));
    } catch(e) {
        send(JSON.stringify({type:'inbound_err', msg:'WSARecvFrom: ' + e}));
    }
}

// ====== 6. Hook select → 诊断 (看是否用 select+recv 模式) ======
function hookSelect() {
    var ws = Process.getModuleByName('WS2_32.dll');
    try {
        var sel = ws.getExportByName('select');
        Interceptor.attach(sel, {
            onEnter: function(args) {
                this.readfds = args[1]; // fd_set* readfds
            }
        });
        send(JSON.stringify({type:'inbound_log', msg:'select hooked (diagnostic)'}));
    } catch(e) {
        send(JSON.stringify({type:'inbound_err', msg:'select: ' + e}));
    }
}

// ====== 主流程 ======
send(JSON.stringify({type:'inbound_log', msg:'=== Inbound capture hooks loading ==='}));

try { hookWSARecv(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'WSARecv:'+e})); }
try { hookWSAGetOverlappedResult(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'WSAGetOverlappedResult:'+e})); }
try { hookGetQueuedCompletionStatus(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'GQCS:'+e})); }
try { hookRecvFrom(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'recvfrom:'+e})); }
try { hookWSARecvFrom(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'WSARecvFrom:'+e})); }
try { hookSelect(); } catch(e) { send(JSON.stringify({type:'inbound_err', msg:'select:'+e})); }

send(JSON.stringify({type:'inbound_log', msg:'All inbound hooks ready. IN_COUNT=' + IN_COUNT}));
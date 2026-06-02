/*
 * frida_inbound_v2.js — 入站包捕获 v2
 *
 * 所有 Winsock 接收最终走 NT 层:
 *   recv/WSARecv → NtDeviceIoControlFile(afd_handle, AFD_RECV, ...)
 *   ReadFile     → NtReadFile(handle, ...)
 *
 * 本脚本 hook 这两个 NT 函数，按进程内 socket handle 过滤。
 */

'use strict';

var KEY = [0x4d, 0xb8, 0xa8, 0x54];
var PIDX = 0;
var MAGIC = [0x43, 0xd5, 0x8b, 0x80];
var NT_COUNT = 0;
var AFD_COUNT = 0;
var gRecvPollBufs = {};     // handle_key → { bufPtr, bufLen }  模块级!

function toHex(arr, max) {
    var end = Math.min(max || arr.length, arr.length);
    var s = '';
    for (var i = 0; i < end; i++) {
        s += ('0' + (arr[i] & 0xFF).toString(16)).slice(-2);
    }
    return s;
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

function extractPacket(raw, dir) {
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
        b0: encPayload[0],
        d0: decPayload[0],
        enc: toHex(encPayload, 128),
        dec: toHex(decPayload, 128),
        dir: dir || 'IN'
    };
}

function sendPkt(raw, dir) {
    try {
        if (!isGamePacket(raw)) return false;
        var pkt = extractPacket(raw, dir);
        send(JSON.stringify(pkt));
        return true;
    } catch(e) {
        return false;
    }
}

// ================================================================
// 1. Hook NtReadFile → 处理 ReadFile 路径
// ================================================================
function hookNtReadFile() {
    var ntdll = Process.getModuleByName('ntdll.dll');
    var ntReadFile = ntdll.getExportByName('NtReadFile');

    Interceptor.attach(ntReadFile, {
        onEnter: function(args) {
            // NTSTATUS NtReadFile(HANDLE FileHandle, HANDLE Event, ...,
            //     IO_STATUS_BLOCK* IoStatusBlock, PVOID Buffer, ULONG Length, ...)
            this.handle = args[0];
            this.buffer = args[4];
            this.length = args[5].toInt32();
            this.ioStatus = args[3];
        },
        onLeave: function(retval) {
            // 只处理成功的调用
            if (retval.toInt32() !== 0) return;

            try {
                var bytesRead = this.ioStatus.isNull() ? 0 : this.ioStatus.readU32();
                if (bytesRead < 20 || bytesRead > 65536) return;

                var raw = new Uint8Array(this.buffer.readByteArray(bytesRead));
                if (sendPkt(raw)) {
                    NT_COUNT++;
                    if (NT_COUNT <= 5 || NT_COUNT % 20 === 0) {
                        send(JSON.stringify({type:'inbound', msg:'NtReadFile# ' + NT_COUNT + ': ' + bytesRead + ' bytes'}));
                    }
                }
            } catch(e) {}
        }
    });

    send(JSON.stringify({type:'inbound', msg:'NtReadFile hooked (ntdll)'}));
}

// ================================================================
// 2. Hook NtDeviceIoControlFile → 处理 AFD socket IO 路径
// ================================================================
function hookNtDeviceIoControlFile() {
    var ntdll = Process.getModuleByName('ntdll.dll');
    var ntDevCtrl = ntdll.getExportByName('NtDeviceIoControlFile');

    // AFD IOCTL codes:
    var AFD_SEND            = 0x1200F;  // 出站
    var AFD_RECV            = 0x12017;  // 入站
    var AFD_RECV_DATAGRAM   = 0x1201B;  // 入站(datagram)

var AFD_SEND_CAPTURED = 0;
var AFD_RECV_DUMPED = 0;   // 诊断: dump 前几次接收
var AFD_RECV_DIAG = 0;    // 诊断: AFD_RECV onEnter 详情

    Interceptor.attach(ntDevCtrl, {
        onEnter: function(args) {
            // x64: args[0]=FileHandle, args[4]=IoStatusBlock, args[5]=IoControlCode,
            //      args[6]=InputBuffer, args[7]=InputBufferLength,
            //      args[8]=OutputBuffer, args[9]=OutputBufferLength
            this.handle = args[0];
            this.ioStatus = args[4];
            this.ioctl = args[5].toInt32();
            this.inBuf = args[6];
            this.inLen = args[7].toInt32();
            this.outBuf = args[8];
            this.outLen = args[9].toInt32();

            // AFD_RECV: 从 InputBuffer (AFD_RECV_INFO) 提取缓冲区
            if (this.ioctl === AFD_RECV && this.inLen >= 16 && !this.inBuf.isNull()) {
                AFD_RECV_DIAG++;
                var diagLines = [];
                try {
                    // AFD_RECV_INFO (x64):
                    // +0: BufferArray ptr → AFD_WSABUF[]
                    // +8: BufferCount (ULONG)
                    var bufArray = this.inBuf.readPointer();
                    var bufCount = this.inBuf.add(8).readU32();
                    diagLines.push('bufArray=' + bufArray + ' bufCount=' + bufCount);

                    if (bufCount > 0 && bufCount <= 64 && !bufArray.isNull()) {
                        // AFD_WSABUF (x64): +0:len(ULONG) +4:padding +8:buf(ptr)
                        var wsaLen = bufArray.readU32();
                        var wsaBuf = bufArray.add(8).readPointer();
                        diagLines.push('wsaLen=' + wsaLen + ' wsaBuf=' + wsaBuf);

                        if (wsaLen > 0 && wsaLen < 65536 && !wsaBuf.isNull()) {
                            var hKey = this.handle.toString();
                            gRecvPollBufs[hKey] = {
                                bufPtr: wsaBuf,
                                bufLen: wsaLen
                            };
                            diagLines.push('STORED handle=' + hKey);
                        } else {
                            diagLines.push('SKIP: wsaLen/wsaBuf bad');
                        }
                    } else {
                        diagLines.push('SKIP: bufCount/bufArray bad');
                    }
                } catch(e) {
                    diagLines.push('ERROR: ' + e);
                }
                if (AFD_RECV_DIAG <= 5) {
                    send(JSON.stringify({type:'inbound', msg:'AFD_RECV diag#'+AFD_RECV_DIAG+': '+diagLines.join(' | ')}));
                }
            }

            // AFD_SEND (0x1200F): 登录后的游戏出站包走这里, 不走 WSASend!
            if (this.ioctl === AFD_SEND && this.inLen >= 8 && !this.inBuf.isNull()) {
                try {
                    // AFD_SEND_INFO (x64):
                    // +0: BufferArray ptr → AFD_WSABUF[]
                    // +8: BufferCount (ULONG)
                    var bufArray = this.inBuf.readPointer();
                    var bufCount = this.inBuf.add(8).readU32();

                    if (bufCount > 0 && bufCount <= 64 && !bufArray.isNull()) {
                        // AFD_WSABUF (x64): +0:len(ULONG) +4:padding +8:buf(ptr)
                        var wsaLen = bufArray.readU32();
                        var wsaBuf = bufArray.add(8).readPointer();

                        if (wsaLen > 0 && wsaLen < 65536 && !wsaBuf.isNull()) {
                            var data = new Uint8Array(wsaBuf.readByteArray(wsaLen));
                            var isGame = sendPkt(data, 'OUT');
                            if (isGame) {
                                AFD_SEND_CAPTURED++;
                                if (AFD_SEND_CAPTURED <= 5 || AFD_SEND_CAPTURED % 20 === 0) {
                                    send(JSON.stringify({type:'inbound', msg:'AFD_SEND# '+AFD_SEND_CAPTURED+': '+wsaLen+' bytes'}));
                                }
                            }
                        }
                    }
                } catch(e) {}
            }
        },
        onLeave: function(retval) {
            var ioctl = this.ioctl;
            AFD_COUNT++;

            if (AFD_COUNT <= 30) {
                send(JSON.stringify({type:'nt', msg:'NtDevIoControl# '+AFD_COUNT+' ioctl=0x'+ioctl.toString(16)+' inLen='+this.inLen+' outLen='+this.outLen+' status=0x'+retval.toInt32().toString(16)}));
            }

            if (ioctl === AFD_RECV || ioctl === AFD_RECV_DATAGRAM) {
                var status = retval.toInt32();
                var hKey = this.handle.toString();

                if (status === 0) {
                    var info = gRecvPollBufs[hKey];
                    if (info) {
                        try {
                            // IO_STATUS_BLOCK (x64): +0:Status(4B)+padding(4B) +8:Information(ptr)
                            var ioBytes = this.ioStatus.isNull() ? 0 : this.ioStatus.add(8).readU32();

                            // ── 诊断: dump 前 10 次 AFD_RECV 成功, 不管 magic ──
                            if (AFD_RECV_DUMPED < 10 && ioBytes > 0) {
                                AFD_RECV_DUMPED++;
                                var dumpLen = Math.min(ioBytes, 64);
                                var dumpData = new Uint8Array(info.bufPtr.readByteArray(dumpLen));
                                send(JSON.stringify({
                                    type: 'inbound',
                                    msg: 'AFD_RECV_DUMP#'+AFD_RECV_DUMPED
                                         + ' ioBytes=' + ioBytes
                                         + ' bufLen=' + info.bufLen
                                         + ' firstBytes=' + toHex(dumpData, 32)
                                }));
                            }

                            if (ioBytes > 0 && ioBytes <= info.bufLen && ioBytes >= 20) {
                                var data = new Uint8Array(info.bufPtr.readByteArray(ioBytes));
                                if (sendPkt(data)) {
                                    send(JSON.stringify({type:'inbound', msg:'AFD_RECV OK! ' + ioBytes + ' bytes, h=' + hKey}));
                                } else if (AFD_RECV_DUMPED <= 10) {
                                    // 有数据但不是 game packet → 也 dump
                                    send(JSON.stringify({type:'inbound', msg:'AFD_RECV non-game ' + ioBytes + ' bytes: ' + toHex(data, 32)}));
                                }
                            } else if (ioBytes > 0 && AFD_RECV_DUMPED <= 10) {
                                send(JSON.stringify({type:'inbound', msg:'AFD_RECV too-small ' + ioBytes + ' bytes bufLen=' + info.bufLen}));
                            }
                        } catch(e) {
                            send(JSON.stringify({type:'inbound', msg:'AFD_RECV read err: ' + e + ' h=' + hKey}));
                        }
                    }
                }
            }

            // AFD 计数仅 HEARTBEAT 中报告, 不刷屏
        }
    });

    send(JSON.stringify({type:'inbound', msg:'NtDeviceIoControlFile hooked (ntdll, AFD filter)'}));
}

// ================================================================
// 3. Hook WSASend 获取游戏 socket handle → 用来过滤
// ================================================================
var gGameSock = null;

function hookWSASendForSocket() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var wsaSend = ws.getExportByName('WSASend');

    Interceptor.attach(wsaSend, {
        onEnter: function(args) {
            if (gGameSock === null) {
                gGameSock = args[0];
                send(JSON.stringify({type:'inbound', msg:'Game socket handle: ' + gGameSock}));
            }
        }
    });

    send(JSON.stringify({type:'inbound', msg:'WSASend socket tracker hooked'}));
}

// ================================================================
// 4. Hook recv (plain Winsock, most common path)  
// ================================================================
function hookRecv() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var recvFn = ws.getExportByName('recv');

    var recvCount = 0;
    Interceptor.attach(recvFn, {
        onEnter: function(args) {
            this.buf = args[1];
            this.len = args[2].toInt32();
            this.sock = args[0];
        },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n <= 0 || n > 65536) return;
            recvCount++;
            try {
                var raw = new Uint8Array(this.buf.readByteArray(Math.min(n, this.len, 65536)));
                if (sendPkt(raw)) {
                    if (recvCount <= 3) {
                        send(JSON.stringify({type:'inbound', msg:'recv# ' + recvCount + ': ' + n + ' bytes INBOUND!'}));
                    }
                } else if (recvCount <= 10) {
                    send(JSON.stringify({type:'inbound', msg:'recv# ' + recvCount + ': ' + n + ' bytes (non-game)'}));
                }
            } catch(e) {
                if (recvCount <= 3) send(JSON.stringify({type:'inbound', msg:'recv err: ' + e}));
            }
        }
    });
    send(JSON.stringify({type:'inbound', msg:'recv hooked (WS2_32)'}));
}

// ================================================================
// 5. Heartbeat — 每 30s 确认脚本存活
// ================================================================
var aliveCount = 0;
setInterval(function() {
    aliveCount++;
    send(JSON.stringify({type:'inbound', msg:'HEARTBEAT#' + aliveCount + ' NtReadFile=' + NT_COUNT + ' AFD=' + AFD_COUNT}));
}, 30000);

// ================================================================
// 6. 轮询扫描 AFD_RECV 缓冲区 (IOCP 异步完成后数据已在 buffer 里)
// ================================================================
var POLL_HIT = 0;
var POLL_SCAN = 0;
setInterval(function() {
    POLL_SCAN++;
    for (var key in gRecvPollBufs) {
        var info = gRecvPollBufs[key];
        try {
            var peek = new Uint8Array(info.bufPtr.readByteArray(Math.min(20, info.bufLen)));
            if (isGamePacket(peek)) {
                POLL_HIT++;
                var data = new Uint8Array(info.bufPtr.readByteArray(Math.min(info.bufLen, 65536)));
                if (sendPkt(data)) {
                    if (POLL_HIT <= 3) {
                        send(JSON.stringify({type:'inbound', msg:'POLL HIT# '+POLL_HIT+' inbound game packet! ' + data.length + ' bytes'}));
                    }
                }
            }
        } catch(e) {}
    }
    // 每 10 轮报告
    if (POLL_SCAN > 0 && POLL_SCAN % 10 === 0) {
        send(JSON.stringify({type:'inbound', msg:'POLL scan#'+POLL_SCAN+' hits='+POLL_HIT+' bufs='+Object.keys(gRecvPollBufs).length}));
    }
}, 500);

// ================================================================
// Main
// ================================================================
send(JSON.stringify({type:'inbound', msg:'=== inbound_v2 loading ==='}));

try { hookNtReadFile(); } catch(e) {
    send(JSON.stringify({type:'inbound', msg:'NtReadFile ERROR: ' + e}));
}

try { hookNtDeviceIoControlFile(); } catch(e) {
    send(JSON.stringify({type:'inbound', msg:'NtDeviceIoControlFile ERROR: ' + e}));
}

try { hookWSASendForSocket(); } catch(e) {
    send(JSON.stringify({type:'inbound', msg:'WSASend socket tracker ERROR: ' + e}));
}

try { hookRecv(); } catch(e) {
    send(JSON.stringify({type:'inbound', msg:'recv ERROR: ' + e}));
}

send(JSON.stringify({type:'inbound', msg:'inbound_v2 hooks ready'}));
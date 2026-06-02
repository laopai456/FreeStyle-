/*
 * frida_capture_plaintext.js — 截获 UDP 加密前的明文
 *
 * 策略:
 *   1. Hook CryptEncrypt(advapi32) → onEnter 读 pbData 明文
 *   2. Hook BCryptEncrypt(bcrypt) → 备选方案
 *   3. Hook WSASendTo/WSASend → 捕获密文 + 调用栈
 *   4. 日志所有加密调用, 按 size 和 caller 后过滤
 *
 * CryptEncrypt 原型:
 *   BOOL CryptEncrypt(HCRYPTKEY hKey, HCRYPTHASH hHash, BOOL Final,
 *                     DWORD dwFlags, BYTE *pbData, DWORD *pdwDataLen, DWORD dwBufLen)
 *   x64: rcx=hKey, rdx=hHash, r8=Final, r9=dwFlags, [rsp+0x28]=pbData, [rsp+0x30]=pdwDataLen
 *   x86: 参数全部在栈上
 */

'use strict';

function ptrHex(p) { try { return '0x' + p.toString(16); } catch(e) { return '(nil)'; } }

function toHex(buf, sz) {
    var s = '';
    for (var i = 0; i < sz; i++) s += ('0' + (buf.add(i).readU8() & 0xFF).toString(16)).slice(-2);
    return s;
}

function getCaller() {
    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
    for (var i = 0; i < Math.min(bt.length, 10); i++) {
        var m = Process.findModuleByAddress(bt[i]);
        if (m && (m.name === 'FreeStyle.exe' || m.name === 'ApolloCT.Dll')) {
            var off = bt[i].sub(m.base);
            return {mod: m.name, offset: '0x' + off.toString(16), addr: ptrHex(bt[i])};
        }
    }
    return null;
}

var encIdx = 0;

// ================================================================
// CryptEncrypt hook (advapi32.dll) — 关键!
// ================================================================
function hookCryptEncrypt() {
    var mod = Process.getModuleByName('ADVAPI32.dll');
    var addr = mod.getExportByName('CryptEncrypt');
    if (!addr) {
        send('CryptEncrypt NOT FOUND');
        return;
    }

    // 检测是否为 x64 进程
    var is64 = (Process.pointerSize === 8);
    send('CryptEncrypt @ ' + ptrHex(addr) + ' (arch: ' + (is64 ? 'x64' : 'x86') + ')');

    Interceptor.attach(addr, {
        onEnter: function(args) {
            this.hKey = args[0];
            this.encIdx = ++encIdx;

            var pbData, pdwDataLen, dwBufLen;
            if (is64) {
                // x64: pbData 在 rsp+0x28, pdwDataLen 在 rsp+0x30, dwBufLen 在 rsp+0x38
                pbData = this.context.rsp.add(0x28).readPointer();
                pdwDataLen = this.context.rsp.add(0x30).readPointer();
                dwBufLen = this.context.rsp.add(0x38).readU32();
            } else {
                // x86: 参数在栈上, esp+4 开始
                // esp+0=返回地址, esp+4=hKey, esp+8=hHash, esp+12=Final, esp+16=dwFlags
                // esp+20=pbData, esp+24=pdwDataLen, esp+28=dwBufLen
                pbData = this.context.esp.add(20).readPointer();
                pdwDataLen = this.context.esp.add(24).readPointer();
                dwBufLen = this.context.esp.add(28).readU32();
            }

            if (pbData.isNull()) return;

            var dataLen = 0;
            try { dataLen = pdwDataLen.readU32(); } catch(e) {}

            // 记录所有 > 100 字节的加密调用 (UDP payload ~1124B)
            if (dataLen < 100) return;

            var plaintext = '';
            try { plaintext = toHex(pbData, Math.min(dataLen, 64)); } catch(e) {}

            var caller = getCaller.call(this);
            var callerStr = caller ? (caller.mod + '+' + caller.offset) : 'unknown';

            send(JSON.stringify({
                type: 'CRYPT',
                api: 'CryptEncrypt',
                idx: this.encIdx,
                caller: callerStr,
                dataLen: dataLen,
                bufLen: dwBufLen,
                plainHex: plaintext,
                hKey: ptrHex(this.hKey)
            }));
        }
    });

    send('CryptEncrypt hooked ✓');
}

// ================================================================
// BCryptEncrypt hook (bcrypt.dll) — 备选
// ================================================================
function hookBCryptEncrypt() {
    try {
        var mod = Process.getModuleByName('bcrypt.dll');
        var addr = mod.getExportByName('BCryptEncrypt');
        if (!addr) {
            send('BCryptEncrypt NOT FOUND in bcrypt.dll');
            return;
        }

        var is64 = (Process.pointerSize === 8);
        send('BCryptEncrypt @ ' + ptrHex(addr));

        Interceptor.attach(addr, {
            onEnter: function(args) {
                // BCryptEncrypt(hKey, pbInput, cbInput, pPaddingInfo, pbIV, cbIV,
                //               pbOutput, cbOutput, pcbResult, dwFlags)
                var pbInput = args[1];
                var cbInput = args[2].toInt32();
                if (cbInput < 100 || pbInput.isNull()) return;

                var plaintext = '';
                try { plaintext = toHex(pbInput, Math.min(cbInput, 64)); } catch(e) {}

                var caller = getCaller.call(this);
                var callerStr = caller ? (caller.mod + '+' + caller.offset) : 'unknown';

                send(JSON.stringify({
                    type: 'CRYPT',
                    api: 'BCryptEncrypt',
                    idx: ++encIdx,
                    caller: callerStr,
                    dataLen: cbInput,
                    plainHex: plaintext
                }));
            }
        });

        send('BCryptEncrypt hooked ✓');
    } catch(e) {
        send('BCryptEncrypt hook error: ' + e);
    }
}

// ================================================================
// WSASendTo hook — UDP C2S 密文 + 调用栈
// ================================================================
function hookWSASendTo() {
    var mod = Process.getModuleByName('WS2_32.dll');
    var addr = mod.getExportByName('WSASendTo');
    if (!addr) {
        send('WSASendTo NOT FOUND');
        return;
    }

    var traceCount = 0;
    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var wsab = args[1];
                var len = wsab.readU32();
                if (len < 16 || len > 65536) return;
                var buf = wsab.add(4).readPointer();
                if (buf.isNull()) return;

                // 检查 907f magic
                if (buf.readU8() !== 0x90 || buf.add(1).readU8() !== 0x7f) return;

                var seq = (buf.add(2).readU8() << 8) | buf.add(3).readU8();

                // 调用栈 (前3个包)
                var stack = [];
                if (traceCount < 3) {
                    traceCount++;
                    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                    for (var i = 0; i < Math.min(bt.length, 15); i++) {
                        var m = Process.findModuleByAddress(bt[i]);
                        var mn = m ? m.name : '???';
                        var off = m ? '0x' + bt[i].sub(m.base).toString(16) : ptrHex(bt[i]);
                        stack.push(mn + '+' + off);
                    }
                }

                send(JSON.stringify({
                    type: 'UDP_OUT',
                    idx: ++encIdx,
                    len: len,
                    seq: seq,
                    cipherHex: toHex(buf, Math.min(len, 80)),
                    stack: stack
                }));
            } catch(e) {}
        }
    });

    send('WSASendTo hooked ✓');
}

// ================================================================
// WSASend hook — connected UDP (备选)
// ================================================================
function hookWSASend() {
    var mod = Process.getModuleByName('WS2_32.dll');
    var addr = mod.getExportByName('WSASend');
    if (!addr) {
        send('WSASend NOT FOUND');
        return;
    }

    var traceCount = 0;
    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var wsab = args[1];
                var len = wsab.readU32();
                if (len < 16 || len > 65536) return;
                var buf = wsab.add(4).readPointer();
                if (buf.isNull()) return;

                if (buf.readU8() !== 0x90 || buf.add(1).readU8() !== 0x7f) return;

                var seq = (buf.add(2).readU8() << 8) | buf.add(3).readU8();

                var stack = [];
                if (traceCount < 3) {
                    traceCount++;
                    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                    for (var i = 0; i < Math.min(bt.length, 15); i++) {
                        var m = Process.findModuleByAddress(bt[i]);
                        var mn = m ? m.name : '???';
                        var off = m ? '0x' + bt[i].sub(m.base).toString(16) : ptrHex(bt[i]);
                        stack.push(mn + '+' + off);
                    }
                }

                send(JSON.stringify({
                    type: 'UDP_OUT',
                    api: 'WSASend',
                    idx: ++encIdx,
                    len: len,
                    seq: seq,
                    cipherHex: toHex(buf, Math.min(len, 80)),
                    stack: stack
                }));
            } catch(e) {}
        }
    });

    send('WSASend hooked ✓');
}

// ================================================================
// Main
// ================================================================
send('\n=== frida_capture_plaintext loading ===');
send('Arch pointer size: ' + Process.pointerSize);

try { hookCryptEncrypt(); } catch(e) { send('CryptEncrypt error: ' + e); }
try { hookBCryptEncrypt(); } catch(e) { send('BCryptEncrypt error: ' + e); }
try { hookWSASendTo(); } catch(e) { send('WSASendTo error: ' + e); }
try { hookWSASend(); } catch(e) { send('WSASend error: ' + e); }

send('=== READY — waiting for game crypto calls... ===');
send('(Login to game and operate to trigger UDP)');
/*
 * frida_capture_v2.js — 无过滤全量捕获 + 追踪密钥
 *
 * 改进:
 *   1. CryptEncrypt: 不设 size 过滤, 记录全部调用
 *   2. CryptImportKey: 追踪密钥导入 (抓 key blob)
 *   3. CryptGenRandom: 追踪随机数 (可能是 IV/nonce 来源)
 *   4. WSASendTo/WSASend: 不变, 907f magic 过滤
 *   5. AES S-box: 扫描代码区引用, 找内置 AES 函数
 */

'use strict';

var is64 = (Process.pointerSize === 8);
var encIdx = 0;
var keyIdx = 0;

function ptrHex(p) { try { return '0x' + p.toString(16); } catch(e) { return '(nil)'; } }

function toHex(buf, sz) {
    var s = '';
    for (var i = 0; i < sz; i++) s += ('0' + (buf.add(i).readU8() & 0xFF).toString(16)).slice(-2);
    return s;
}

function getGameCaller() {
    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
    for (var i = 0; i < Math.min(bt.length, 15); i++) {
        try {
            var m = Process.findModuleByAddress(bt[i]);
            if (m && (m.name === 'FreeStyle.exe' || m.name === 'ApolloCT.Dll')) {
                var off = bt[i].sub(m.base);
                return {mod: m.name, offset: '0x' + off.toString(16), addr: ptrHex(bt[i])};
            }
        } catch(e) {}
    }
    return null;
}

// ================================================================
// CryptEncrypt — 无过滤, 记录全部调用
// ================================================================
function hookCryptEncrypt() {
    var mod = Process.getModuleByName('ADVAPI32.dll');
    var addr = mod.getExportByName('CryptEncrypt');
    if (!addr) { send('CryptEncrypt NOT FOUND'); return; }

    send('CryptEncrypt @ ' + ptrHex(addr));

    Interceptor.attach(addr, {
        onEnter: function(args) {
            this.eIdx = ++encIdx;

            var pbData, pdwDataLen, dwBufLen, hKey, hHash, finalFlag, dwFlags;
            hKey = args[0];
            hHash = args[1];
            finalFlag = is64 ? args[2].toInt32() : args[2].toInt32();
            dwFlags = is64 ? args[3].toInt32() : args[3].toInt32();
            pbData = is64 ? this.context.rsp.add(0x28).readPointer() : args[4];
            pdwDataLen = is64 ? this.context.rsp.add(0x30).readPointer() : args[5];
            dwBufLen = is64 ? this.context.rsp.add(0x38).readU32() : args[6].toInt32();

            if (pbData.isNull()) return;
            var dataLen = 0;
            try { dataLen = pdwDataLen.readU32(); } catch(e) {}

            var plaintext = '';
            if (dataLen > 0) {
                try { plaintext = toHex(pbData, Math.min(dataLen, 64)); } catch(e) {}
            }

            var caller = getGameCaller.call(this);

            send(JSON.stringify({
                type: 'CRYPT_ENC',
                idx: this.eIdx,
                dataLen: dataLen,
                bufLen: dwBufLen,
                final: finalFlag,
                flags: dwFlags,
                hKey: ptrHex(hKey),
                plainHex: plaintext,
                caller: caller
            }));
        }
    });

    send('CryptEncrypt hooked ✓ (no filter)');
}

// ================================================================
// CryptImportKey — 追踪密钥导入
// ================================================================
function hookCryptImportKey() {
    var mod = Process.getModuleByName('ADVAPI32.dll');
    var addr = mod.getExportByName('CryptImportKey');
    if (!addr) { send('CryptImportKey NOT FOUND'); return; }

    send('CryptImportKey @ ' + ptrHex(addr));

    Interceptor.attach(addr, {
        onEnter: function(args) {
            keyIdx++;
            // args[0]=hProv, args[1]=pbData(KEY BLOB), args[2]=dwDataLen
            // args[3]=hPubKey, args[4]=dwFlags, args[5]=phKey
            var pbData = args[1];
            var dwDataLen = args[2].toInt32();
            var dwFlags = is64 ? args[4].toInt32() : args[4].toInt32();
            this.keyIdx = keyIdx;

            var keyBlob = '';
            if (dwDataLen > 0 && dwDataLen < 4096 && !pbData.isNull()) {
                try { keyBlob = toHex(pbData, Math.min(dwDataLen, 128)); } catch(e) {}
            }

            var caller = getGameCaller.call(this);

            send(JSON.stringify({
                type: 'CRYPT_KEY',
                idx: keyIdx,
                blobLen: dwDataLen,
                flags: dwFlags,
                keyBlob: keyBlob,
                caller: caller
            }));
        },
        onLeave: function(retval) {
            send(JSON.stringify({
                type: 'CRYPT_KEY_OK',
                idx: this.keyIdx,
                result: retval.toInt32()
            }));
        }
    });

    send('CryptImportKey hooked ✓');
}

// ================================================================
// CryptAcquireContextA — 追踪 CSP 上下文
// ================================================================
function hookCryptAcquireContext() {
    var mod = Process.getModuleByName('ADVAPI32.dll');
    var addr = mod.getExportByName('CryptAcquireContextA');
    if (!addr) { send('CryptAcquireContextA NOT FOUND'); return; }

    Interceptor.attach(addr, {
        onEnter: function(args) {
            // args[1]=pszContainer, args[2]=pszProvider, args[3]=dwProvType, args[4]=dwFlags
            var container = '(null)', provider = '(null)';
            try { container = args[1].readAnsiString(); } catch(e) {}
            try { provider = args[2].readAnsiString(); } catch(e) {}
            var provType = is64 ? args[3].toInt32() : args[3].toInt32();

            send(JSON.stringify({
                type: 'CRYPT_CTX',
                container: container,
                provider: provider,
                provType: provType
            }));
        }
    });

    send('CryptAcquireContextA hooked ✓');
}

// ================================================================
// CryptGenRandom — 可能用于 IV/nonce
// ================================================================
function hookCryptGenRandom() {
    var mod = Process.getModuleByName('ADVAPI32.dll');
    var addr = mod.getExportByName('CryptGenRandom');
    if (!addr) return;

    Interceptor.attach(addr, {
        onEnter: function(args) {
            // args[1]=dwLen
            var len = is64 ? args[1].toInt32() : args[1].toInt32();
            if (len === 16 || len === 32 || len === 8) {  // AES key/IV sizes
                send(JSON.stringify({
                    type: 'CRYPT_RAND',
                    len: len,
                    caller: getGameCaller.call(this)
                }));
            }
        }
    });

    send('CryptGenRandom hooked ✓');
}

// ================================================================
// WSASendTo — UDP C2S 密文
// ================================================================
function hookWSASendTo() {
    var mod = Process.getModuleByName('WS2_32.dll');
    var addr = mod.getExportByName('WSASendTo');
    if (!addr) { send('WSASendTo NOT FOUND'); return; }

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

                send(JSON.stringify({
                    type: 'UDP_OUT',
                    api: 'WSASendTo',
                    idx: ++encIdx,
                    len: len,
                    seq: seq,
                    cipherHex: toHex(buf, Math.min(len, 80)),
                    caller: getGameCaller.call(this)
                }));
            } catch(e) {}
        }
    });

    send('WSASendTo hooked ✓');
}

function hookWSASend() {
    var mod = Process.getModuleByName('WS2_32.dll');
    var addr = mod.getExportByName('WSASend');
    if (!addr) { send('WSASend NOT FOUND'); return; }

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

                send(JSON.stringify({
                    type: 'UDP_OUT',
                    api: 'WSASend',
                    idx: ++encIdx,
                    len: len,
                    seq: seq,
                    cipherHex: toHex(buf, Math.min(len, 80)),
                    caller: getGameCaller.call(this)
                }));
            } catch(e) {}
        }
    });

    send('WSASend hooked ✓');
}

// ================================================================
// AES S-box 交叉引用扫描
// ================================================================
function scanAesXrefs() {
    // AES S-box 在 FreeStyle.exe 的地址
    var sboxAddrs = ['0x2442ef8', '0x2617f18'];
    var fsMod = Process.getModuleByName('FreeStyle.exe');

    sboxAddrs.forEach(function(offsetStr) {
        var offset = parseInt(offsetStr, 16);
        var sboxAddr = fsMod.base.add(offset);
        send('\n--- AES S-box @ +' + offsetStr + ' ---');

        // 在该地址附近搜索代码引用 (32-bit relative address)
        // 在 x86 中, lea reg, [addr] 的编码包含 addr 的绝对值
        var addrBytes = [
            sboxAddr.readU8(),
            sboxAddr.add(1).readU8(),
            sboxAddr.add(2).readU8(),
            sboxAddr.add(3).readU8()
        ];

        var pattern = '';
        for (var i = 0; i < 4; i++) {
            pattern += ('0' + addrBytes[i].toString(16)).slice(-2) + ' ';
        }
        pattern = pattern.trim();

        send('  Looking for references to: ' + ptrHex(sboxAddr) + ' (bytes: ' + pattern + ')');

        // 在代码段 (通常 .text 在 base 附近) 中搜索
        try {
            // 搜索模块的整个地址空间找引用
            var results = Memory.scanSync(fsMod.base, fsMod.size, pattern);
            send('  Found ' + results.length + ' references');

            for (var i = 0; i < Math.min(results.length, 10); i++) {
                var r = results[i].address;
                var rOff = r.sub(fsMod.base);
                var ctx = '';
                try {
                    for (var j = -8; j < 8; j++) {
                        ctx += ('0' + (r.add(j).readU8() & 0xFF).toString(16)).slice(-2) + ' ';
                    }
                } catch(e) {}
                send('    @ +0x' + rOff.toString(16) + ' | ' + ctx);
            }
        } catch(e) {
            send('  scan error: ' + e);
        }
    });
}

// ================================================================
// Main
// ================================================================
send('\n=== frida_capture_v2 loading ===');
send('Arch: ' + (is64 ? 'x64' : 'x86'));

try { hookCryptAcquireContext(); } catch(e) { send('CryptAcquireContext error: ' + e); }
try { hookCryptImportKey(); } catch(e) { send('CryptImportKey error: ' + e); }
try { hookCryptGenRandom(); } catch(e) { send('CryptGenRandom error: ' + e); }
try { hookCryptEncrypt(); } catch(e) { send('CryptEncrypt error: ' + e); }
try { hookWSASendTo(); } catch(e) { send('WSASendTo error: ' + e); }
try { hookWSASend(); } catch(e) { send('WSASend error: ' + e); }

try { scanAesXrefs(); } catch(e) { send('AES scan error: ' + e); }

send('=== READY ===');
send('ALL CryptEncrypt calls will be logged (no size filter)');
send('Login & enter game, then operate to trigger...');
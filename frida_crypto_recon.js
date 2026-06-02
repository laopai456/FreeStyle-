/*
 * frida_crypto_recon.js — 加密函数侦察
 *
 * 目标: 定位 FreeStyle UDP 包的加密函数
 * 方法:
 *   1. 枚举所有加载模块, 找出 crypto 相关
 *   2. 扫描 FreeStyle.exe IAT (导入表) 中的 crypto API
 *   3. 搜索 AES/ChaCha/RC4 常量特征
 *   4. Hook sendto 捕获 C2S 包 → 打印完整调用栈 → 追溯加密函数
 */

'use strict';

function ptrHex(p) {
    try { return '0x' + p.toString(16); } catch(e) { return '(null)'; }
}

function toHex(buf, sz) {
    var s = '';
    for (var i = 0; i < sz; i++) s += ('0' + (buf.add(i).readU8() & 0xFF).toString(16)).slice(-2);
    return s;
}

// ================================================================
// Phase 1: 枚举所有模块
// ================================================================
send('\n========== Phase 1: Loaded Modules ==========');
var mods = Process.enumerateModules();
var cryptoMods = [];
var keyMods = [];

for (var i = 0; i < mods.length; i++) {
    var m = mods[i];
    var name = m.name.toLowerCase();
    var info = {
        name: m.name,
        base: ptrHex(m.base),
        size: m.size
    };

    // 识别 crypto 相关模块
    if (name.indexOf('crypt') >= 0 || name.indexOf('ssl') >= 0 ||
        name.indexOf('bcrypt') >= 0 || name.indexOf('ncrypt') >= 0 ||
        name.indexOf('aes') >= 0 || name.indexOf('chacha') >= 0) {
        cryptoMods.push(info);
    }

    // 识别游戏关键模块
    if (name.indexOf('freestyle') >= 0 || name.indexOf('apollo') >= 0 ||
        name.indexOf('game') >= 0 || name.indexOf('security') >= 0 ||
        name.indexOf('anti') >= 0 || name.indexOf('protect') >= 0) {
        keyMods.push(info);
    }

    send('  ' + m.name + '  base=' + ptrHex(m.base) + '  size=' + m.size);
}

send('\n--- Crypto-related modules ---');
cryptoMods.forEach(function(m) { send('  ' + m.name + ' @ ' + m.base); });

send('\n--- Game-related modules ---');
keyMods.forEach(function(m) { send('  ' + m.name + ' @ ' + m.base); });

// ================================================================
// Phase 2: 扫描 FreeStyle.exe 导入表
// ================================================================
send('\n========== Phase 2: FreeStyle.exe Imports ==========');

try {
    var fsMod = Process.getModuleByName('FreeStyle.exe');
    send('FreeStyle.exe base=' + ptrHex(fsMod.base) + ' size=' + fsMod.size);

    var imports = fsMod.enumerateImports();
    var cryptImports = [];

    for (var i = 0; i < imports.length; i++) {
        var imp = imports[i];
        var name = imp.name.toLowerCase();
        if (name.indexOf('crypt') >= 0 ||
            name.indexOf('hash') >= 0 ||
            name.indexOf('random') >= 0 ||
            name.indexOf('aes') >= 0 ||
            name.indexOf('cipher') >= 0 ||
            name.indexOf('key') >= 0 ||
            name.indexOf('rc4') >= 0 ||
            name.indexOf('des') >= 0 ||
            name.indexOf('md5') >= 0 ||
            name.indexOf('sha') >= 0) {
            cryptImports.push(imp);
        }
    }

    if (cryptImports.length > 0) {
        send('\n--- Crypto-related imports (' + cryptImports.length + ') ---');
        cryptImports.forEach(function(imp) {
            send('  ' + imp.name + ' (from ' + imp.module + ') @ ' + ptrHex(imp.address) +
                 ' type=' + imp.type);
        });
    } else {
        send('  NO crypto imports found in FreeStyle.exe IAT');
    }

    // Also list ALL imports from BCrypt, Crypt32, advapi32
    var targetDlls = ['BCRYPT.DLL', 'CRYPT32.DLL', 'ADVAPI32.DLL', 'NCRYPT.DLL',
                      'KERNEL32.DLL', 'WS2_32.DLL'];
    targetDlls.forEach(function(dllName) {
        var dllLower = dllName.toLowerCase();
        var found = imports.filter(function(imp) {
            return imp.module.toLowerCase() === dllLower;
        });
        if (found.length > 0) {
            send('\n  Imports from ' + dllName + ' (' + found.length + '):');
            found.forEach(function(imp) {
                send('    ' + imp.name + ' @ ' + ptrHex(imp.address));
            });
        } else {
            send('\n  ' + dllName + ': NOT imported');
        }
    });

} catch(e) {
    send('  ERROR enumerating FreeStyle.exe: ' + e);
}

// ================================================================
// Phase 3: 扫描内存中的加密常量
// ================================================================
send('\n========== Phase 3: Crypto Constant Scans ==========');

function scanPattern(modName, pattern, label) {
    try {
        var mod = Process.getModuleByName(modName);
        var results = Memory.scanSync(mod.base, mod.size, pattern);
        send('  [' + modName + '] ' + label + ': ' + results.length + ' hits');
        for (var i = 0; i < Math.min(results.length, 3); i++) {
            var addr = results[i].address;
            var off = addr.sub(mod.base);
            var ctx = '';
            try {
                for (var j = 0; j < 32; j++) {
                    ctx += ('0' + addr.add(j).readU8().toString(16)).slice(-2) + ' ';
                }
            } catch(e) {}
            send('    @ +0x' + off.toString(16) + ' | ' + ctx);
        }
    } catch(e) {
        send('  [' + modName + '] ' + label + ': ERROR ' + e);
    }
}

// AES S-box 前 16 字节 (最独特的模式)
scanPattern('FreeStyle.exe', '63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76', 'AES S-box');

// AES 逆 S-box
scanPattern('FreeStyle.exe', '52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb', 'AES InvS-box');

// ChaCha20 "expand 32-byte k"
scanPattern('FreeStyle.exe', '65 78 70 61 6e 64 20 33 32 2d 62 79 74 65 20 6b', 'ChaCha constant');

// RC4 key schedule (256 字节 0x00-0xFF 连续)
// 这太宽泛, 跳过

// Bcrypt 常量
scanPattern('FreeStyle.exe', '42 43 72 79 70 74', 'BCrypt string');

// XOR 模式: 搜索 907f magic near xor-like patterns
var keyModsToScan = ['FreeStyle.exe', 'ApolloCT.Dll'];
keyModsToScan.forEach(function(mn) {
    try {
        var mod = Process.getModuleByName(mn);
        // 搜索 UDP magic 907f 在模块中的出现
        var results = Memory.scanSync(mod.base, mod.size, '90 7f');
        send('  [' + mn + '] UDP magic (907f): ' + results.length + ' hits');
        for (var i = 0; i < Math.min(results.length, 5); i++) {
            var addr = results[i].address;
            var off = addr.sub(mod.base);
            var ctx = '';
            try {
                for (var j = -8; j < 24; j++) {
                    ctx += ('0' + (addr.add(j).readU8() & 0xFF).toString(16)).slice(-2) + ' ';
                }
            } catch(e) {}
            send('    @ +0x' + off.toString(16) + ' | ... ' + ctx + '...');
        }
    } catch(e) {}
});

// ================================================================
// Phase 4: 枚举 ApolloCT.Dll 的导出函数
// ================================================================
send('\n========== Phase 4: Key Module Exports ==========');

keyModsToScan.forEach(function(mn) {
    try {
        var mod = Process.getModuleByName(mn);
        var exps = mod.enumerateExports();
        var cryptExports = exps.filter(function(e) {
            var name = e.name.toLowerCase();
            return name.indexOf('crypt') >= 0 || name.indexOf('enc') >= 0 ||
                   name.indexOf('dec') >= 0 || name.indexOf('cipher') >= 0 ||
                   name.indexOf('xor') >= 0 || name.indexOf('key') >= 0 ||
                   name.indexOf('packet') >= 0 || name.indexOf('send') >= 0;
        });
        send('  [' + mn + '] total exports: ' + exps.length +
             ', crypto-related: ' + cryptExports.length);
        cryptExports.forEach(function(e) {
            send('    ' + e.name + ' @ ' + ptrHex(e.address));
        });
    } catch(e) {
        send('  [' + mn + ']: NOT loaded');
    }
});

// ================================================================
// Phase 5: sendto 调用栈追踪 (定位加密函数)
// ================================================================
send('\n========== Phase 5: sendto Stack Trace ==========');

var C2S_MAGIC_HI = 0x90;
var C2S_MAGIC_LO = 0x7f;
var traceCount = 0;
var MAX_TRACE = 5;  // 只打印前5个包的调用栈

function hookSendtoForTrace() {
    var ws = Process.getModuleByName('WS2_32.dll');
    var addr;
    try { addr = ws.getExportByName('sendto'); } catch(e) {}
    if (!addr) {
        // try send
        try { addr = ws.getExportByName('send'); } catch(e) {}
    }
    if (!addr) {
        send('  sendto/send NOT FOUND in WS2_32');
        return;
    }

    Interceptor.attach(addr, {
        onEnter: function(args) {
            try {
                var buf = args[1];
                var len = args[2].toInt32();
                if (len < 16 || len > 65536) return;

                // 检查 907f magic
                if (buf.readU8() !== C2S_MAGIC_HI) return;
                if (buf.add(1).readU8() !== C2S_MAGIC_LO) return;

                traceCount++;
                if (traceCount > MAX_TRACE) return;

                send('\n  === C2S UDP packet #' + traceCount + ' (len=' + len + ') ===');
                send('  Packet hex[0:32]: ' + toHex(buf, Math.min(len, 32)));

                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                send('  Call stack (' + bt.length + ' frames):');

                for (var i = 0; i < Math.min(bt.length, 40); i++) {
                    var addr2 = bt[i];
                    var m = Process.findModuleByAddress(addr2);
                    var mn = m ? m.name : '???';
                    var off = m ? '0x' + addr2.sub(m.base).toString(16) : ptrHex(addr2);

                    // 标记游戏模块
                    var isGame = (mn === 'FreeStyle.exe' || mn === 'ApolloCT.Dll');
                    var marker = isGame ? ' <<<' : '';

                    send('    [' + i + '] ' + mn + '+' + off + marker);
                }
            } catch(e) {}
        }
    });

    send('  sendto hooked for stack trace (max ' + MAX_TRACE + ' packets)');
}

try { hookSendtoForTrace(); } catch(e) { send('  hookSendtoForTrace error: ' + e); }

// ================================================================
// Phase 6: BCrypt 运行时 hook (如果加载了)
// ================================================================
send('\n========== Phase 6: BCrypt Runtime Hooks ==========');

try {
    var bcrypt = Process.getModuleByName('bcrypt.dll');
    send('  BCrypt.dll loaded @ ' + ptrHex(bcrypt.base));

    var bcryptFuncs = ['BCryptEncrypt', 'BCryptDecrypt', 'BCryptGenerateSymmetricKey',
                       'BCryptSetProperty', 'BCryptCreateHash', 'BCryptHashData',
                       'BCryptFinishHash', 'BCryptGenRandom'];
    bcryptFuncs.forEach(function(fn) {
        try {
            var addr = bcrypt.getExportByName(fn);
            if (addr) {
                Interceptor.attach(addr, {
                    onEnter: function(args) {
                        var caller = Thread.backtrace(this.context, Backtracer.ACCURATE)[1];
                        var cm = caller ? Process.findModuleByAddress(caller) : null;
                        var cname = cm ? cm.name : '???';
                        // 只记录来自游戏模块的调用
                        if (cname === 'FreeStyle.exe' || cname === 'ApolloCT.Dll') {
                            send('  [BCRYPT] ' + fn + ' called from ' + cname);
                        }
                    }
                });
                send('  [BCrypt] ' + fn + ' hooked');
            }
        } catch(e) {}
    });
} catch(e) {
    send('  BCrypt.dll NOT loaded');
}

send('\n========== RECON COMPLETE ==========');
send('Waiting for C2S UDP packets to trace...');
send('(Send some game actions to trigger UDP sends)');
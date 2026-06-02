/**
 * find_crypto_funcs.js — 在内存中扫描 .text 段，查找加密函数
 * 
 * 直接搜索 CALL [CryptEncrypt_IAT] 和 CALL [WSASendTo_IAT] 模式，
 * 找到加密函数入口地址。
 * 
 * IAT 地址 (abs, ImageBase=0x400000):
 *   WSASendTo:       0x0268F944
 *   CryptEncrypt:    0x0268F04C
 *   CryptImportKey:  0x0268F008
 *   WSASend:         0x0268F9EC
 * 
 * x86: CALL dword ptr [addr] = FF 15 <4 bytes le>
 */
'use strict';

var base = Module.findBaseAddress("FreeStyle.exe");
if (!base) {
    send({type: "error", msg: "FreeStyle.exe not loaded"});
} else {
    send({type: "info", msg: "FreeStyle.exe base: " + base});
    
    // 要搜索的 IAT 地址
    var targets = {
        0x268F944: "WSASendTo",
        0x268F04C: "CryptEncrypt", 
        0x268F008: "CryptImportKey",
        0x268F9EC: "WSASend",
        0x268F948: "WSARecvFrom",
        0x268F964: "recvfrom",
        0x268F9C4: "WSARecv",
        0x268F014: "CryptHashData",
        0x268F018: "CryptCreateHash",
        0x268F02C: "CryptGenRandom",
        0x268F030: "CryptAcquireContextA",
    };
    
    // AES S-box 首 8 字节
    var AES_SBOX_8 = new Uint8Array([0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5]);
    var AES_INVSBOX_8 = new Uint8Array([0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38]);
    
    // .text 段
    var TEXT_OFFSET = 0x1000;
    var TEXT_SIZE = 0x280B000;
    var textPtr = base.add(TEXT_OFFSET);
    
    send({type: "info", msg: ".text: " + textPtr + " size=" + (TEXT_SIZE/1024/1024).toFixed(1) + "MB"});
    
    // 读取 .text 段到 ArrayBuffer
    send({type: "info", msg: "Reading .text section..."});
    var textData;
    try {
        textData = textPtr.readByteArray(TEXT_SIZE);
    } catch (e) {
        send({type: "error", msg: "Failed to read .text: " + e});
        textData = null;
    }
    
    if (textData) {
        var data = new Uint8Array(textData);
        send({type: "info", msg: "Read " + (data.length/1024/1024).toFixed(1) + "MB, scanning patterns..."});
        
        var results = {};
        
        // 1. 搜索 CALL [IAT] = FF 15 <addr>
        for (var iatAddr in targets) {
            var name = targets[iatAddr];
            var pattern = [0xFF, 0x15];
            var addrBytes = new Uint8Array(4);
            addrBytes[0] = iatAddr & 0xFF;
            addrBytes[1] = (iatAddr >> 8) & 0xFF;
            addrBytes[2] = (iatAddr >> 16) & 0xFF;
            addrBytes[3] = (iatAddr >> 24) & 0xFF;
            
            var hits = [];
            for (var i = 0; i < data.length - 6; i++) {
                if (data[i] == 0xFF && data[i+1] == 0x15 &&
                    data[i+2] == addrBytes[0] && data[i+3] == addrBytes[1] &&
                    data[i+4] == addrBytes[2] && data[i+5] == addrBytes[3]) {
                    hits.push(TEXT_OFFSET + i);
                }
            }
            results[name] = hits;
        }
        
        // 2. 搜索 AES S-box 引用 (在代码中找 push/mov 包含 S-box RVA 0x2442ef8 等)
        // 完整 S-box 搜索: 在 .text 中找到 S-box 数据位置
        var sboxHits = [];
        for (var i = 0; i < data.length - 8; i++) {
            var match = true;
            for (var j = 0; j < 8; j++) {
                if (data[i+j] != AES_SBOX_8[j]) { match = false; break; }
            }
            if (match) sboxHits.push(TEXT_OFFSET + i);
        }
        
        var invSboxHits = [];
        for (var i = 0; i < data.length - 8; i++) {
            var match = true;
            for (var j = 0; j < 8; j++) {
                if (data[i+j] != AES_INVSBOX_8[j]) { match = false; break; }
            }
            if (match) invSboxHits.push(TEXT_OFFSET + i);
        }
        
        // 3. 输出结果
        send({type: "result", header: "=== IAT CALL 指令统计 ==="});
        for (var targetName in results) {
            var hits = results[targetName];
            send({type: "result", msg: targetName + ": " + hits.length + " calls"});
        }
        
        send({type: "result", header: "=== AES S-box 位置 (在内存中) ==="});
        send({type: "result", msg: "S-box: " + sboxHits.length + " occurrences"});
        for (var si = 0; si < Math.min(sboxHits.length, 10); si++) {
            send({type: "result", msg: "  0x" + sboxHits[si].toString(16) + " (=" + base.add(sboxHits[si]) + ")"});
        }
        send({type: "result", msg: "InvS-box: " + invSboxHits.length + " occurrences"});
        for (var si = 0; si < Math.min(invSboxHits.length, 10); si++) {
            send({type: "result", msg: "  0x" + invSboxHits[si].toString(16)});
        }
        
        // 4. 详细列出每个 WSASendTo 和 CryptEncrypt 调用地址
        send({type: "result", header: "=== WSASendTo CALL 地址 ==="});
        for (var wi = 0; wi < results["WSASendTo"].length; wi++) {
            send({type: "result", msg: "  RVA 0x" + results["WSASendTo"][wi].toString(16) + 
                " (abs " + base.add(results["WSASendTo"][wi]) + ")"});
        }
        
        send({type: "result", header: "=== CryptEncrypt CALL 地址 ==="});
        for (var ci = 0; ci < results["CryptEncrypt"].length; ci++) {
            send({type: "result", msg: "  RVA 0x" + results["CryptEncrypt"][ci].toString(16) + 
                " (abs " + base.add(results["CryptEncrypt"][ci]) + ")"});
        }
        
        send({type: "result", header: "=== CryptImportKey CALL 地址 ==="});
        for (var ki = 0; ki < results["CryptImportKey"].length; ki++) {
            send({type: "result", msg: "  RVA 0x" + results["CryptImportKey"][ki].toString(16)});
        }
        
        // 5. 查找 S-box 在代码中的引用
        // 在代码中搜索 push/mov 指令引用 S-box 地址
        send({type: "result", header: "=== AES S-box 代码引用搜索 ==="});
        // 简化: 搜索包含 S-box RVA 0x2442ef8 的指令
        var sboxRefPattern1 = new Uint8Array([0xf8, 0x2e, 0x44, 0x02]);  // LE of 0x02442ef8
        var sboxRefPattern2 = new Uint8Array([0x18, 0x7f, 0x61, 0x02]);  // LE of 0x02617f18
        var sboxRefHits = [];
        for (var i = 0; i < data.length - 4; i++) {
            if ((data[i] == 0xf8 && data[i+1] == 0x2e && data[i+2] == 0x44 && data[i+3] == 0x02) ||
                (data[i] == 0x18 && data[i+1] == 0x7f && data[i+2] == 0x61 && data[i+3] == 0x02)) {
                sboxRefHits.push(TEXT_OFFSET + i);
            }
        }
        send({type: "result", msg: "S-box address references in code: " + sboxRefHits.length});
        for (var ri = 0; ri < Math.min(sboxRefHits.length, 30); ri++) {
            send({type: "result", msg: "  0x" + sboxRefHits[ri].toString(16)});
        }
        
        send({type: "done", msg: "Scan complete"});
    }
}
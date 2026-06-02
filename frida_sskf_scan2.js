'use strict';
// frida_sskf_scan2.js — 同步扫描 SSKF + xrefs

var sskfAddr = ptr(0x284B9C4);
console.log('[SSKF] Expected @ ' + sskfAddr);

// 验证
try {
    var buf = Memory.readByteArray(sskfAddr, 4);
    var b = new Uint8Array(buf);
    console.log('[SSKF] Read: ' + String.fromCharCode(b[0],b[1],b[2],b[3]));
} catch(e) {
    console.log('[SSKF] Read failed: ' + e);
}

// 在可执行内存中搜 SSKF 的位置
var ranges = Process.enumerateRanges({protection: 'rwx'});
for (var r of ranges) {
    try {
        var hits = Memory.scanSync(r.base, r.size, '53 53 4B 46');
        if (hits.length > 0) {
            for (var h of hits) {
                console.log('[SSKF] Found @ ' + h.address + ' in ' + r.base);
            }
            break;  // 只找第一个
        }
    } catch(e) {}
}

// 在可执行内存中搜 SSKF 地址的引用 (4字节 LE)
var targetBytes = hexToBytes(sskfAddr.toString(16).padStart(8, '0'));
var pattern = targetBytes.map(b => b.toString(16).padStart(2,'0')).join(' ');
console.log('[XREF] Pattern: ' + pattern);

var xrefTotal = 0;
for (var r of ranges) {
    try {
        var hits = Memory.scanSync(r.base, r.size, pattern);
        for (var h of hits) {
            if (h.address.equals(sskfAddr)) continue;
            try {
                var inst = Instruction.parse(h.address);
                console.log('[XREF] ' + h.address + ': ' + inst.toString());
                xrefTotal++;
            } catch(e) {
                console.log('[XREF] ' + h.address + ': (data)');
            }
        }
    } catch(e) {}
}
console.log('[XREF] Total: ' + xrefTotal);

function hexToBytes(hex) {
    var r = [];
    for (var i = 0; i < hex.length; i += 2)
        r.push(parseInt(hex.substring(i, i+2), 16));
    return r;
}
console.log('[DONE]');

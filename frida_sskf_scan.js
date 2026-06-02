'use strict';
// frida_sskf_scan.js — 运行时扫描 SSKF 位置和引用

// Strategy: SSKF is in the .text section.
// .text runtime base = 0x401000, RVA of SSKF = 0x244B9C4
// So at runtime it should be at 0x401000 + (0x244B9C4 - 0x1000) = 0x284B9C4
var expectedAddr = ptr(0x284B9C4);
console.log('[SSKF] Expected address: ' + expectedAddr);

// Read and verify
try {
    var buf = Memory.readByteArray(expectedAddr, 4);
    var bytes = new Uint8Array(buf);
    var str = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
    console.log('[SSKF] Verified: ' + str + ' @ ' + expectedAddr);
    
    // Search for this address as a 4-byte LE immediate in executable memory
    var tv = expectedAddr.toInt32();
    var pattern = hexToBytes(tv.toString(16).padStart(8, '0'));
    console.log('[XREF] Searching for pattern: ' + pattern.map(b => b.toString(16).padStart(2, '0')).join(' '));
    
    var ranges = Process.enumerateRanges({protection: 'rwx'});
    var totalXrefs = 0;
    
    for (var r of ranges) {
        if (totalXrefs > 30) break;
        try {
            Memory.scan(r.base, r.size, pattern, {
                onMatch: function(address, size) {
                    if (address.equals(expectedAddr)) return;  // skip SSKF itself
                    try {
                        var inst = Instruction.parse(address);
                        console.log('[XREF] ' + address + ': ' + inst.toString());
                        totalXrefs++;
                    } catch(e) {
                        // not a valid instruction
                    }
                },
                onError: function(reason) {},
                onComplete: function() {}
            });
        } catch(e) {}
    }
    console.log('[XREF] Total xrefs: ' + totalXrefs);
    
} catch(e) {
    console.log('[SSKF] NOT at expected address: ' + e);
    // Fallback: search executable memory for SSKF bytes
    console.log('[SSKF] Searching all executable memory...');
    var ranges = Process.enumerateRanges({protection: 'rwx'});
    var found = [];
    for (var r of ranges) {
        Memory.scan(r.base, r.size, '53 53 4B 46', {
            onMatch: function(address, size) {
                found.push(address);
                console.log('[SSKF] Found at ' + address + ' (range: ' + r.base + ')');
            },
            onComplete: function() {}
        });
    }
    console.log('[SSKF] Total locations: ' + found.length);
}

function hexToBytes(hex) {
    var bytes = [];
    for (var i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substring(i, i+2), 16));
    }
    return bytes;
}

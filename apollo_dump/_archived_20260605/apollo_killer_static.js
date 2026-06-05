// apollo_killer_static.js — 纯静态补丁，无Interceptor，无INT3
// Memory.patchCode + Memory.protect + 立即脱离

var base = ptr('0x400000');
var DST_IC = 50125711;

// ═══ 补丁1: ApolloCT CRC ═══
try {
    var am = Process.getModuleByName('ApolloCT.dll');
    var crcAddrs = [0x1A3C54, 0x1BE222];
    var crcOk = 0;
    for (var i = 0; i < crcAddrs.length; i++) {
        try {
            var a = am.base.add(crcAddrs[i]);
            Memory.protect(a.and(ptr(0xFFFFF000)), 0x1000, 'rwx');
            a.writeU8(0x33); a.add(1).writeU8(0xC0); a.add(2).writeU8(0xC3);
            Memory.protect(a.and(ptr(0xFFFFF000)), 0x1000, 'rx');
            crcOk++;
        } catch(e) {}
    }
    send({t: 'patched', apolloCRC: crcOk + '/' + crcAddrs.length});
} catch(e) { send({t: 'patched', apolloCRC: 'not loaded'}); }

// ═══ 补丁2: sprintf 调用处 ═══
// 0x1AE254B: mov edx,[ebp-0xD8] (8B 95 28 FF FF FF) → mov edx, DST_IC (BA xx xx xx xx 90)
var p1 = base.add(0x1AE254B);
var o1 = new Uint8Array(p1.readByteArray(6));
var e1 = [0x8B, 0x95, 0x28, 0xFF, 0xFF, 0xFF];
var p1ok = true;
for (var i = 0; i < 6; i++) { if (o1[i] !== e1[i]) p1ok = false; }

if (p1ok) {
    Memory.patchCode(p1, 6, function(code) {
        code.writeU8(0xBA);
        code.writeU32(DST_IC);
        code.writeU8(0x90);
    });
    var v1 = new Uint8Array(p1.readByteArray(6));
    var s1 = '';
    for (var i = 0; i < 6; i++) s1 += ('0' + v1[i].toString(16)).slice(-2) + ' ';
    send({t: 'patched', sprintf1: 'OK ' + s1});
} else {
    var s = '';
    for (var i = 0; i < 6; i++) s += ('0' + o1[i].toString(16)).slice(-2) + ' ';
    send({t: 'mismatch', bytes: 'sprintf1: expected 8B 95 28 FF FF FF got ' + s});
}

// ═══ 补丁3: sprintf 第2处 ═══
// 0x1AE2576: mov eax,[ebp-0xD8] (8B 85 28 FF FF FF) → mov eax, DST_IC (B8 xx xx xx xx 90)
var p2 = base.add(0x1AE2576);
var o2 = new Uint8Array(p2.readByteArray(6));
var e2 = [0x8B, 0x85, 0x28, 0xFF, 0xFF, 0xFF];
var p2ok = true;
for (var i = 0; i < 6; i++) { if (o2[i] !== e2[i]) p2ok = false; }

if (p2ok) {
    Memory.patchCode(p2, 6, function(code) {
        code.writeU8(0xB8);
        code.writeU32(DST_IC);
        code.writeU8(0x90);
    });
    var v2 = new Uint8Array(p2.readByteArray(6));
    var s2 = '';
    for (var i = 0; i < 6; i++) s2 += ('0' + v2[i].toString(16)).slice(-2) + ' ';
    send({t: 'patched', sprintf2: 'OK ' + s2});
} else {
    var s = '';
    for (var i = 0; i < 6; i++) s += ('0' + o2[i].toString(16)).slice(-2) + ' ';
    send({t: 'mismatch', bytes: 'sprintf2: expected 8B 85 28 FF FF FF got ' + s});
}
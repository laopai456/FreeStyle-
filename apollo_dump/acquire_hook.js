// acquire_hook.js
// Step 0:  Hook NtQueryVirtualMemory + NtProtectVirtualMemory (Apollo deception)
// Step 0.5: Patch ApolloCT CRC
// Step 1:  Hook ReadFile → detect SSKF → scan stack for filename → data replacement
//
// No AcquireSMD hook needed. Data replacement at ReadFile level:
// - TARGET item loads → cache its SSKF data
// - SOURCE item loads → overwrite buffer with TARGET data
//
// Usage: loaded by acquire_hook.py

'use strict';

var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;

fsMod.enumerateSections().forEach(function(s) {
    if (s.name === '.text') textSection = s;
});

if (!textSection) {
    send({t: 'FAIL', msg: '.text section not found in FreeStyle.exe'});
    throw new Error('.text section not found');
}
var textStart = textSection.address;
var textEnd = textStart.add(textSection.size);
send({t: 'SECTION', start: textStart.toString(), end: textEnd.toString(), size: textSection.size});

// ── Constants ────────────────────────────────────────────
var PAGE_EXECUTE_READ = 0x20;
var PAGE_EXECUTE_READWRITE = 0x40;

// ── Config ──────────────────────────────────────────────
var SOURCE_ITEM = '';
var TARGET_ITEM = '';
var REPLACE_COUNT = 0;

// ── Step 0/0.5 flags ─────────────────────────────────────
var VP_DISABLED = false;
var DECEPTION_ACTIVE = false;
var VQ_LIE_COUNT = 0;
var VP_FAKE_COUNT = 0;
var CRC_PATCHED = false;

// ── Helpers ──────────────────────────────────────────────
function inTextRange(addr) {
    return addr.compare(textStart) >= 0 && addr.compare(textEnd) < 0;
}

function addrFmt(a) {
    return a.toString() + '  (RVA: +' + a.sub(base).toString(16) + ')';
}

// ═══════════════════════════════════════════════════════════
// Step 0: Apollo deception hooks
// ═══════════════════════════════════════════════════════════

function installDeception() {
    send({t: 'DECEPTION', msg: 'Installing VirtualQuery/Protect deception hooks...'});

    var ntdll = Process.getModuleByName('ntdll.dll');

    // ── 0a: NtQueryVirtualMemory ─────────────────────────
    var NtQueryVirtualMemory = ntdll.getExportByName('NtQueryVirtualMemory');
    try {
        Interceptor.attach(NtQueryVirtualMemory, {
            onEnter: function(args) {
                this.memInfo    = args[3];
                this.infoLen    = args[4];
                this.infoClass  = args[2];
            },
            onLeave: function(retval) {
                if (retval.toInt32() !== 0) return;
                if (this.infoClass.toInt32() !== 0) return;
                if (this.memInfo.isNull()) return;
                try {
                    var baseAddr = this.memInfo.readPointer();
                    if (!inTextRange(baseAddr)) return;
                    this.memInfo.add(8).writeU32(PAGE_EXECUTE_READ);
                    this.memInfo.add(20).writeU32(PAGE_EXECUTE_READ);
                    VQ_LIE_COUNT++;
                } catch(e) {}
            }
        });
        send({t: 'DECEPTION', msg: '  NtQueryVirtualMemory hooked'});
    } catch(e) {
        send({t: 'DECEPTION_ERR', msg: 'NtQueryVirtualMemory: ' + e});
        return false;
    }

    // ── 0b: NtProtectVirtualMemory ────────────────────────
    var NtProtectVirtualMemory = ntdll.getExportByName('NtProtectVirtualMemory');
    try {
        Interceptor.attach(NtProtectVirtualMemory, {
            onEnter: function(args) {
                this.baseAddrPtr = args[1];
                this.oldProtectPtr = args[4];
                this.ourCall = VP_DISABLED;
            },
            onLeave: function(retval) {
                if (this.ourCall) return;
                try {
                    var addr = this.baseAddrPtr.readPointer();
                    if (!inTextRange(addr)) return;
                    if (!this.oldProtectPtr.isNull()) {
                        this.oldProtectPtr.writeU32(PAGE_EXECUTE_READ);
                    }
                    retval.replace(0);
                    VP_FAKE_COUNT++;
                } catch(e) {}
            }
        });
        send({t: 'DECEPTION', msg: '  NtProtectVirtualMemory hooked'});
    } catch(e) {
        send({t: 'DECEPTION_ERR', msg: 'NtProtectVirtualMemory: ' + e});
        return false;
    }

    DECEPTION_ACTIVE = true;
    send({t: 'DECEPTION', msg: 'Deception active.'});
    return true;
}

// ═══════════════════════════════════════════════════════════
// Step 0.5: Patch ApolloCT CRC
// ═══════════════════════════════════════════════════════════

function patchCRC() {
    send({t: 'CRC', msg: 'Patching ApolloCT CRC checks...'});

    var apolloCT;
    try {
        apolloCT = Process.getModuleByName('ApolloCT.dll');
    } catch(e) {
        send({t: 'CRC_ERR', msg: 'ApolloCT.dll not found'});
        return false;
    }

    var CRC_RVAS = [0x1A3C54, 0x1BE222];
    var patched = 0;

    for (var i = 0; i < CRC_RVAS.length; i++) {
        var addr = apolloCT.base.add(CRC_RVAS[i]);
        var page = addr.and(ptr(0xfffff000));
        try {
            Memory.protect(page, 0x1000, 'rwx');
            addr.writeU8(0x33);
            addr.add(1).writeU8(0xC0);
            addr.add(2).writeU8(0xC3);
            Memory.protect(page, 0x1000, 'rx');
            patched++;
            send({t: 'CRC', msg: '  Patched ApolloCT+0x' + CRC_RVAS[i].toString(16)});
        } catch(e) {
            send({t: 'CRC_ERR', msg: '  FAIL at 0x' + CRC_RVAS[i].toString(16) + ': ' + e});
        }
    }

    CRC_PATCHED = (patched === CRC_RVAS.length);
    send({t: 'CRC', msg: 'CRC patch: ' + patched + '/' + CRC_RVAS.length});
    return CRC_PATCHED;
}

// ═══════════════════════════════════════════════════════════
// Step 1: ReadFile hook → detect SSKF → scan stack → replace data
// ═══════════════════════════════════════════════════════════
// New approach: no AcquireSMD hook needed.
// - Scan stack for .smd filename when SSKF detected
// - Cache TARGET item's SSKF data when loaded
// - Replace SOURCE item's buffer with TARGET data

var READFILE_HOOKED = false;
var SSKF_CACHE = {};       // filename → { data: ArrayBuffer, size: int }
var SSKF_DETECT_COUNT = 0;

// Scan stack for .smd/.bml filename, return first match
function scanStackForFilename(esp) {
    for (var off = 0; off < 0x800; off += 4) {
        try {
            var ptrVal = esp.add(off).readPointer();
            // Deref: ptr → string
            var tries = [
                {fn: function() { return ptrVal.readAnsiString(128); }, type: 'deref'},
                {fn: function() { return ptrVal.add(4).readAnsiString(128); }, type: 'deref+4'},
                {fn: function() { return ptrVal.add(8).readAnsiString(128); }, type: 'deref+8'}
            ];
            for (var ti = 0; ti < tries.length; ti++) {
                try {
                    var s = tries[ti].fn();
                    if (s && (s.indexOf('.smd') >= 0 || s.indexOf('.bml') >= 0)) {
                        return { filename: s, off: off, type: tries[ti].type, addr: ptrVal.toString() };
                    }
                } catch(e) {}
            }
            // Double deref
            try {
                var ptr2 = ptrVal.readPointer();
                var s4 = ptr2.readAnsiString(128);
                if (s4 && (s4.indexOf('.smd') >= 0 || s4.indexOf('.bml') >= 0)) {
                    return { filename: s4, off: off, type: 'deref2', addr: ptrVal.toString() + '→' + ptr2.toString() };
                }
            } catch(e) {}
        } catch(e) {}
    }
    return null;
}

function installReadFileHook() {
    send({t: 'READFILE', msg: 'Hooking ReadFile for SSKF detection + data replacement...'});

    var kernel32 = Process.getModuleByName('kernel32.dll');
    var ReadFile = kernel32.getExportByName('ReadFile');

    try {
        Interceptor.attach(ReadFile, {
            onEnter: function(args) {
                this.hFile = args[0];
                this.lpBuffer = args[1];
                this.nNumberOfBytesToRead = args[2].toInt32();
                this.lpNumberOfBytesRead = args[3];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                if (this.nNumberOfBytesToRead < 4) return;
                if (this.lpBuffer.isNull()) return;

                // Check SSKF magic
                try {
                    var magic = this.lpBuffer.readByteArray(4);
                    if (!magic) return;
                    var m = new Uint8Array(magic);
                    if (!(m[0] === 0x53 && m[1] === 0x53 && m[2] === 0x4B && m[3] === 0x46)) return;
                } catch(e) { return; }

                SSKF_DETECT_COUNT++;

                // Get actual bytes read
                var bytesRead = this.nNumberOfBytesToRead;
                try {
                    var actual = this.lpNumberOfBytesRead.readU32();
                    if (actual > 0 && actual <= bytesRead) bytesRead = actual;
                } catch(e) {}

                // Scan stack for filename
                var esp = this.context.esp;
                var found = scanStackForFilename(esp);

                var fname = found ? found.filename : '(unknown)';
                send({t: 'SSKF', n: SSKF_DETECT_COUNT, size: bytesRead, fname: fname,
                    off: found ? found.off : -1, type: found ? found.type : ''});

                if (!found) return;

                // Cache or replace logic
                var isSource = SOURCE_ITEM && fname.indexOf(SOURCE_ITEM) >= 0;
                var isTarget = TARGET_ITEM && fname.indexOf(TARGET_ITEM) >= 0;

                if (isTarget && !SSKF_CACHE[TARGET_ITEM]) {
                    // Cache TARGET data
                    try {
                        var targetData = this.lpBuffer.readByteArray(bytesRead);
                        SSKF_CACHE[TARGET_ITEM] = { data: targetData, size: bytesRead };
                        send({t: 'CACHE', item: TARGET_ITEM, size: bytesRead, fname: fname});
                    } catch(e) {
                        send({t: 'CACHE_ERR', item: TARGET_ITEM, err: e.toString()});
                    }
                }

                if (isSource && SSKF_CACHE[TARGET_ITEM]) {
                    // Replace SOURCE buffer with TARGET data
                    var td = SSKF_CACHE[TARGET_ITEM];
                    if (td.size <= this.nNumberOfBytesToRead) {
                        try {
                            this.lpBuffer.writeByteArray(td.data);
                            // Update bytes read if different
                            try {
                                this.lpNumberOfBytesRead.writeU32(td.size);
                            } catch(e) {}
                            REPLACE_COUNT++;
                            send({t: 'REPLACE', count: REPLACE_COUNT, old: fname,
                                new: TARGET_ITEM, size: td.size});
                        } catch(e) {
                            send({t: 'REPLACE_ERR', err: e.toString()});
                        }
                    } else {
                        send({t: 'REPLACE_SKIP', reason: 'target larger than buffer',
                            targetSize: td.size, bufferSize: this.nNumberOfBytesToRead});
                    }
                }

                if (isSource && !SSKF_CACHE[TARGET_ITEM]) {
                    send({t: 'WAIT_TARGET', msg: 'Source detected but target not cached yet. Load target item first.'});
                }
            }
        });
        READFILE_HOOKED = true;
        send({t: 'READFILE', msg: 'ReadFile hooked. Waiting for SSKF reads...'});
        return true;
    } catch(e) {
        send({t: 'READFILE_ERR', msg: 'ReadFile hook failed: ' + e});
        return false;
    }
}

// ═══════════════════════════════════════════════════════════
// Init flow
// ═══════════════════════════════════════════════════════════

function init() {
    send({t: 'INIT', msg: 'Starting SSKF data replacement initialization...'});

    // Step 0: Apollo deception
    if (!installDeception()) {
        send({t: 'FAIL', msg: 'Deception hooks failed. Aborting.'});
        return;
    }

    // Step 0.5: CRC patch
    if (!patchCRC()) {
        send({t: 'CRC_WARN', msg: 'CRC patch failed, continuing...'});
    }

    // Step 1: ReadFile hook for SSKF detection + data replacement
    if (!installReadFileHook()) {
        send({t: 'FAIL', msg: 'ReadFile hook failed. Aborting.'});
        return;
    }

    send({
        t: 'READY',
        msg: 'Ready. Set rule: src <itemcode> dst <itemcode>. Load target item first to cache, then load source item to replace.'
    });
}

// ── RPC helpers ──────────────────────────────────────────
rpc.exports = {
    setSource: function(itemCode) {
        SOURCE_ITEM = itemCode;
        send({t: 'CONFIG', source: SOURCE_ITEM, target: TARGET_ITEM});
    },
    setTarget: function(itemCode) {
        TARGET_ITEM = itemCode;
        send({t: 'CONFIG', source: SOURCE_ITEM, target: TARGET_ITEM});
    },
    setRule: function(src, dst) {
        SOURCE_ITEM = src;
        TARGET_ITEM = dst;
        send({t: 'CONFIG', source: SOURCE_ITEM, target: TARGET_ITEM});
    },
    status: function() {
        var cached = [];
        var cacheKeys = Object.keys(SSKF_CACHE);
        for (var i = 0; i < cacheKeys.length; i++) {
            cached.push(cacheKeys[i] + '(' + SSKF_CACHE[cacheKeys[i]].size + 'B)');
        }
        send({
            t: 'STATUS',
            source: SOURCE_ITEM,
            target: TARGET_ITEM,
            replaces: REPLACE_COUNT,
            sskf_detects: SSKF_DETECT_COUNT,
            cached: cached.join(', ') || '(none)',
            deception_active: DECEPTION_ACTIVE,
            vq_lies: VQ_LIE_COUNT,
            vp_fakes: VP_FAKE_COUNT
        });
    },
    resetCounters: function() {
        REPLACE_COUNT = 0;
        send({t: 'RESET', msg: 'Counters reset'});
    }
};

// ── Start ────────────────────────────────────────────────
setTimeout(init, 500);

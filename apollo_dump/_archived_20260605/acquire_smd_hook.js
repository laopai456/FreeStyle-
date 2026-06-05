// acquire_smd_hook.js — Hook inner helper at 0x01EEC130, scan stack for SString
//
// Strategy: 0x01EED020 (real AcquireSMD) crashes when hooked.
// 0x01EEC130 (inner helper) works fine (24 calls observed).
// So we hook 0x01EEC130 and scan its stack frame upward to find
// the SString parameter from the caller (0x01EED020).
//
// Call chain: caller -> 0x01EED020(AcquireSMD, SString) -> ... -> 0x01EEC130(int,int)
// The SString is likely still on the stack or in a register above our frame.

var SRC = 'SRC_PLACEHOLDER';
var DST = 'DST_PLACEHOLDER';

// Hook the STABLE inner function
var INNER_RVA = 0x01EEC130;

var mod = Process.getModuleByName('FreeStyle.exe');
var base = mod.base;
var innerFunc = base.add(INNER_RVA);

var prologue = innerFunc.readByteArray(16);
var hex = Array.from(new Uint8Array(prologue)).map(function(b) {
    return ('0' + b.toString(16)).slice(-2);
}).join(' ');
send({t: 'INFO', msg: 'Hooking inner @ 0x' + innerFunc.toString() + ' bytes: ' + hex});

var callCount = 0;

Interceptor.attach(innerFunc, {
    onEnter: function(args) {
        callCount++;
        var count = callCount;

        var esp = this.context.esp;

        send({t: 'CALL', n: count, esp: esp.toString(),
              arg0: args[0].toString(), arg1: args[1].toString()});

        // First 3 calls: dump all readable strings found on stack
        if (count > 3) return;

        // Scan stack from ESP+4 up to ESP+0x400
        // Find any printable ASCII runs >= 6 chars
        try {
            var stackData = esp.readByteArray(0x400);
            if (stackData) {
                var view = new Uint8Array(stackData);
                var runStart = -1;
                for (var pos = 0; pos < 0x400; pos++) {
                    var ch = view[pos];
                    if (ch >= 0x20 && ch < 0x7F) {
                        if (runStart < 0) runStart = pos;
                    } else {
                        if (runStart >= 0 && (pos - runStart) >= 6) {
                            try {
                                var s = esp.add(runStart).readUtf8String(pos - runStart);
                                if (s && s.length >= 6) {
                                    send({t: 'STR', n: count, offset: '+0x' + runStart.toString(16),
                                          addr: esp.add(runStart).toString(), str: s});
                                }
                            } catch(e) {}
                        }
                        runStart = -1;
                    }
                }
            }
        } catch(e) {
            send({t: 'ERR', msg: 'stack scan: ' + e.message});
        }
    }
});

// Also scan for the item code in a wider memory range around stack
// to catch SString that might be in a register saved earlier
send({t: 'HOOKED', msg: 'Inner func hook (0x01EEC130), scanning stack for SRC'});
send({t: 'INFO', msg: 'Trigger shop/equip. Watching for "' + SRC + '" in stack data.'});

// ============================================================
// trace_callstack.js — 路线 Alpha
// ReadFile SSKF 检测 + Thread.backtrace → 定位 AcquireSMD 入口
// ============================================================

var kernel32 = Process.getModuleByName('kernel32.dll');
var ReadFileAddr = kernel32.getExportByName('ReadFile');
send({t: 'diag', msg: 'kernel32=' + kernel32.base + ' ReadFile=' + ReadFileAddr});

Interceptor.attach(ReadFileAddr, {
    onEnter: function(args) {
        this.hFile = args[0];
        this.lpBuffer = args[1];
        this.nBytes = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (this.nBytes < 32 || retval.toInt32() === 0) return;

        try {
            var buf = this.lpBuffer.readByteArray(Math.min(this.nBytes, 64));
            var u8 = new Uint8Array(buf);
        } catch(e) { return; }

        // SSKF magic check
        if (u8[0] !== 0x53 || u8[1] !== 0x53 || u8[2] !== 0x4B || u8[3] !== 0x46) return;

        // Extract filename from SSKF header
        var fname = '';
        for (var i = 8; i < Math.min(this.nBytes, 64); i++) {
            if (u8[i] === 0) break;
            fname += String.fromCharCode(u8[i]);
        }

        // === CALL STACK ===
        var stackFrames = [];
        try {
            var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
            for (var j = 0; j < Math.min(bt.length, 20); j++) {
                var addr = bt[j];
                var mod = Process.findModuleByAddress(addr);
                if (mod) {
                    var off = addr.sub(mod.base);
                    stackFrames.push(mod.name + '+' + off.toString(16));
                } else {
                    stackFrames.push(addr.toString());
                }
            }
        } catch(e) {
            stackFrames.push('backtrace error: ' + e);
        }

        send({
            t: 'SSKF',
            name: fname,
            sz: this.nBytes,
            stack: stackFrames
        });
    }
});

send({t: 'ready', msg: 'SSKF callstack tracer active'});
var SOURCE = "__SOURCE__";
var TARGET = "__TARGET__";

var enabled = true;
var diagMode = true;  // 诊断模式：打印所有小读取
var stats = { total: 0, small: 0, bml: 0, patched: 0 };

var srcBytes = [];
var tgtBytes = [];
for (var i = 0; i < SOURCE.length; i++) {
    srcBytes.push(SOURCE.charCodeAt(i));
    tgtBytes.push(TARGET.charCodeAt(i));
}

function toHex(buf, max) {
    var s = "", n = Math.min(buf.length, max || 64);
    for (var i = 0; i < n; i++) {
        var h = buf[i].toString(16);
        s += (h.length < 2 ? "0" + h : h) + " ";
    }
    return s.trim();
}

function toAscii(buf, max) {
    var s = "", n = Math.min(buf.length, max || 100);
    for (var i = 0; i < n; i++) {
        var b = buf[i];
        s += (b >= 0x20 && b < 0x7F) ? String.fromCharCode(b) : ".";
    }
    return s;
}

var k32 = Process.getModuleByName('kernel32.dll');
var pReadFile = k32.getExportByName('ReadFile');

Interceptor.attach(pReadFile, {
    onEnter: function (args) {
        this.buf = args[1];
        this.reqSize = args[2].toInt32();
    },
    onLeave: function (retval) {
        try {
            if (!enabled) return;
            if (!retval.toInt32()) return;

            var n = this.reqSize;
            if (n < 16 || n > 65536) return;

            var raw = new Uint8Array(this.buf.readByteArray(n));
            stats.total++;

            // 诊断模式：只报告可读文本占比 >40% 的读取
            if (diagMode && n <= 16384) {
                stats.small++;
                var checkLen = Math.min(n, 400);
                var printable = 0;
                for (var i = 0; i < checkLen; i++) {
                    if (raw[i] >= 0x20 && raw[i] < 0x7F) printable++;
                }
                if (printable > checkLen * 0.4) {
                    send({ type: "diag_read", size: n, ascii: toAscii(raw, 300) });
                }
                // XOR 0xFF 版本
                var xored = new Uint8Array(checkLen);
                for (var i = 0; i < checkLen; i++) xored[i] = raw[i] ^ 0xFF;
                var xPrintable = 0;
                for (var i = 0; i < checkLen; i++) {
                    if (xored[i] >= 0x20 && xored[i] < 0x7F) xPrintable++;
                }
                if (xPrintable > checkLen * 0.4 && xPrintable > printable) {
                    send({ type: "diag_read_xor", size: n, ascii: toAscii(xored, 300) });
                }
            }
        } catch (e) {
            send({ type: "hook_err", msg: e.toString() });
        }
    }
});

send({ type: "ready", source: SOURCE, target: TARGET, diag: diagMode });

// command loop
recv('cmd', function onCmd(msg) {
    var c = msg.cmd;
    if (c === 'start')      { enabled = true;  send({ type: "status", enabled: true }); }
    else if (c === 'stop')  { enabled = false; send({ type: "status", enabled: false }); }
    else if (c === 'stats') { send({ type: "stats", total: stats.total, small: stats.small, bml: stats.bml, patched: stats.patched }); }
    else if (c === 'diag_off') { diagMode = false; send({ type: "status", diag: false }); }
    recv('cmd', onCmd);
});

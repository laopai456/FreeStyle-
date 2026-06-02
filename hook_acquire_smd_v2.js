/**
 * hook_acquire_smd_v2.js — 阶段3: 从栈帧读出 SMD 文件名
 *
 * 关键:
 *   AcquireSMD(SString/SFullName filepath, int Preset) 在 32位 cdecl 下:
 *   [EBP+8]  = 第一个参数 (字符串对象指针)
 *   [EBP+C]  = 第二个参数 (Preset, 通常 0)
 *
 * 已知 AcquireSMD 返回地址:
 *   0x1eec93e — header(512B) 校验路径
 *   0x1eecba7 — 模型体读取路径
 *   0x1f66955 — BML 装备加载 Alternate 路径 (header)
 *   0x1f66a8d — BML 装备加载 Alternate 路径 (body)
 */

var k32 = Process.getModuleByName('kernel32.dll');
var BASE = Process.getModuleByName('FreeStyle.exe').base;
var N = 0;

// AcquireSMD 候选返回地址
var ACQUIRE_RETS = [
    {rva: 0x1eec93e, label: 'AcquireSMD_hdr'},
    {rva: 0x1eecba7, label: 'AcquireSMD_body'},
    {rva: 0x1f66955, label: 'AcquireSMD_BML_hdr'},
    {rva: 0x1f66a8d, label: 'AcquireSMD_BML_body'},
];
// 预计算绝对地址
for (var i = 0; i < ACQUIRE_RETS.length; i++) {
    ACQUIRE_RETS[i].addr = BASE.add(ACQUIRE_RETS[i].rva);
}

// ============================================================
// Hook: ReadFile SSKF — 栈帧读取参数
// ============================================================
var pReadFile = k32.getExportByName('ReadFile');
Interceptor.attach(pReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.sz  = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        if (this.sz < 4) return;
        try {
            var raw = this.buf.readByteArray(4);
            var m = new Uint8Array(raw);
            if (m[0] !== 0x53 || m[1] !== 0x53 || m[2] !== 0x4B || m[3] !== 0x46) return;

            N++;

            // 1. Walk EBP chain, collect (ret, ebp) pairs
            var frames = [];
            var ebp = this.context.ebp;
            for (var i = 0; i < 12 && ebp && !ebp.isNull(); i++) {
                try {
                    var ret = ebp.add(4).readPointer();
                    frames.push({r: ret, e: ebp});
                    ebp = ebp.readPointer();
                } catch(e) { break; }
            }

            // 2. 找 AcquireSMD 帧
            for (var j = 0; j < frames.length; j++) {
                var f = frames[j];
                for (var a = 0; a < ACQUIRE_RETS.length; a++) {
                    if (!f.r.equals(ACQUIRE_RETS[a].addr)) continue;

                    // Found! Read [EBP+8] = first arg
                    var arg = f.e.add(8).readPointer();

                    // 尝试在 arg 及 arg+偏移 处读出路径字符串
                    var found = [];
                    // 尝试 0x00~0x20 偏移，每4字节尝试两种：直接ansi读 和 间接指针读
                    for (var off = 0; off <= 0x20; off += 4) {
                        try {
                            var s = arg.add(off).readAnsiString(200);
                            if (s && s.length > 2 && s.length < 200 && /[a-z]/.test(s)) {
                                found.push('+' + off.toString(16).padStart(2,'0') + ' d:' + s);
                            }
                        } catch(e) {}
                        try {
                            var p2 = arg.add(off).readPointer();
                            if (p2 && !p2.isNull()) {
                                var s2 = p2.readAnsiString(200);
                                if (s2 && s2.length > 2 && s2.length < 200 && /[a-z]/.test(s2)) {
                                    found.push('+' + off.toString(16).padStart(2,'0') + ' p:' + s2);
                                }
                            }
                        } catch(e) {}
                    }

                    // 也尝试把 arg 的 +0x00 和 +0x04 和 +0x08 当作 UTF-16 (宽字符路径)
                    for (var woff = 0; woff <= 8; woff += 4) {
                        try {
                            var ws = arg.add(woff).readUtf16String(200);
                            if (ws && ws.length > 2 && ws.length < 200 && /[a-z]/i.test(ws)) {
                                found.push('+' + woff.toString(16).padStart(2,'0') + ' w:' + ws);
                            }
                        } catch(e) {}
                        try {
                            var wp = arg.add(woff).readPointer();
                            if (wp && !wp.isNull()) {
                                var ws2 = wp.readUtf16String(200);
                                if (ws2 && ws2.length > 2 && ws2.length < 200 && /[a-z]/i.test(ws2)) {
                                    found.push('+' + woff.toString(16).padStart(2,'0') + ' wp:' + ws2);
                                }
                            }
                        } catch(e) {}
                    }

                    var info = {
                        label: ACQUIRE_RETS[a].label,
                        arg: arg.toString(),
                        found: found
                    };

                    send({t: 'path', n: N, sz: this.sz, info: info});
                    return; // 只处理第一个匹配的帧
                }
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'Stage 3: reading SMD filename from AcquireSMD param'});
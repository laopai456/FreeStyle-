/**
 * smd_redirect.js v8 — 流式字节替换（含 hFile 追踪）
 */
var k32 = Process.getModuleByName('kernel32.dll');

var REDIRECT = {};
var CAPTURES = {};       // { name: {body: ArrayBuffer, totalSz: number} }
var CAPTURE_TARGET = '';
var CAPTURE_CHUNKS = [];
var CAPTURE_ACTIVE = false;
var CAPTURE_HFILE = null;  // 只捕获这个句柄的数据

var SEEN = {};
var STATS = { hits: 0, captured: 0, redirected: 0, replaced: 0 };

// 替换状态: 字节流式 + hFile 追踪
var REPL_ACTIVE = false;
var REPL_FILE = null;   // 只替换这个句柄的读取
var REPL_DATA = null;
var REPL_POS = 0;
var REPL_TOTAL = 0;

var pReadFile = k32.getExportByName('ReadFile');

Interceptor.attach(pReadFile, {
    onEnter: function(args) {
        this.hFile = args[0];
        this.buf = args[1];
        this.sz = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0) return;
        if (this.sz < 4) return;

        var hFileStr = String(this.hFile);

        // === 流式替换: 只替换 SMD 文件的读取 ===
        if (REPL_ACTIVE && hFileStr === REPL_FILE) {
            try {
                var remaining = REPL_TOTAL - REPL_POS;
                if (remaining <= 0) {
                    REPL_ACTIVE = false;
                    REPL_FILE = null;
                    REPL_DATA = null;
                    STATS.replaced++;
                    send({t: 'replaced', done: true});
                    return;
                }
                var len = Math.min(this.sz, remaining);
                this.buf.writeByteArray(REPL_DATA.slice(REPL_POS, REPL_POS + len));
                REPL_POS += len;
            } catch(e) {
                REPL_ACTIVE = false;
                REPL_FILE = null;
                REPL_DATA = null;
            }
            return;
        }

        // === 捕获后续块: 只捕获同一文件句柄的数据 ===
        if (CAPTURE_ACTIVE && hFileStr === CAPTURE_HFILE) {
            try {
                var cd = this.buf.readByteArray(this.sz);
                if (cd) CAPTURE_CHUNKS.push(cd);
            } catch(e) {}
            return;
        }

        // === SSKF 检测 ===
        try {
            var raw = this.buf.readByteArray(4);
            var m = new Uint8Array(raw);
            if (m[0] !== 0x53 || m[1] !== 0x53 || m[2] !== 0x4B || m[3] !== 0x46) return;

            STATS.hits++;

            var name = '';
            try { name = this.buf.add(8).readAnsiString(64); } catch(e) {}
            if (!name || name.length < 2) return;

            if (!SEEN[name]) {
                SEEN[name] = true;
                send({t: 'file', name: name});
            }

            // === 捕获 ===
            if (CAPTURE_TARGET && name.toLowerCase() === CAPTURE_TARGET) {
                CAPTURE_ACTIVE = true;
                CAPTURE_HFILE = hFileStr;
                CAPTURE_CHUNKS = [];  // 从 body 开始，不存 header
                send({t: 'capture_start', name: name, hFile: hFileStr});
                return;
            }

            // === 重定向 ===
            var lower = name.toLowerCase();
            var replacement = REDIRECT[lower];
            if (replacement && CAPTURES[replacement]) {
                STATS.redirected++;
                send({t: 'redir', from: name, to: replacement,
                    bodySz: CAPTURES[replacement].totalSz});

                REPL_ACTIVE = true;
                REPL_FILE = hFileStr;
                REPL_DATA = CAPTURES[replacement].body;
                REPL_POS = 0;
                REPL_TOTAL = CAPTURES[replacement].totalSz;
                return;  // header 不替换
            }
        } catch(e) {}
    }
});

// ============================================================
// RPC
// ============================================================
rpc.exports = {
    capture: function(target) {
        if (!target) return 'Usage: cap <filename>';
        CAPTURE_TARGET = target.toLowerCase();
        CAPTURE_CHUNKS = [];
        CAPTURE_ACTIVE = false;
        CAPTURE_HFILE = null;
        return 'Waiting for ' + target + '...';
    },

    stopcap: function() {
        if (!CAPTURE_ACTIVE) return 'No active capture';
        CAPTURE_ACTIVE = false;
        var h = CAPTURE_HFILE;
        CAPTURE_HFILE = null;
        // 拼接所有 chunk 为一个 ArrayBuffer
        var total = 0;
        for (var i = 0; i < CAPTURE_CHUNKS.length; i++) total += CAPTURE_CHUNKS[i].byteLength;
        var body = new ArrayBuffer(total);
        var view = new Uint8Array(body);
        var off = 0;
        for (var i = 0; i < CAPTURE_CHUNKS.length; i++) {
            var d = new Uint8Array(CAPTURE_CHUNKS[i]);
            view.set(d, off);
            off += d.length;
        }
        CAPTURES[CAPTURE_TARGET] = { body: body, totalSz: total };
        STATS.captured++;
        send({t: 'captured', name: CAPTURE_TARGET, size: total, chunks: CAPTURE_CHUNKS.length});
        var name = CAPTURE_TARGET;
        CAPTURE_TARGET = '';
        CAPTURE_CHUNKS = [];
        return 'OK captured ' + name + ': body=' + total + ' bytes';
    },

    redirect: function(src, dst) {
        var s = src.toLowerCase(), d = dst.toLowerCase();
        if (!CAPTURES[d]) return 'FAIL: ' + dst + ' not captured (dest)';
        REDIRECT[s] = d;
        send({t: 'rule', from: src, to: dst});
        return 'OK ' + src + ' -> ' + dst + ' (body=' + CAPTURES[d].totalSz + ' bytes)';
    },

    info: function(name) {
        if (!name) return 'Usage: info <filename>';
        var n = name.toLowerCase();
        if (CAPTURES[n])
            return name + ': body=' + CAPTURES[n].totalSz + ' bytes';
        return name + ': not captured';
    },

    list: function() {
        var keys = Object.keys(REDIRECT);
        if (keys.length === 0) return ['(empty)'];
        var r = []; for (var j = 0; j < keys.length; j++) r.push(keys[j] + ' -> ' + REDIRECT[keys[j]]);
        return r;
    },

    capts: function() {
        var keys = Object.keys(CAPTURES);
        if (keys.length === 0) return ['(empty)'];
        var r = []; for (var j = 0; j < keys.length; j++) r.push(keys[j] + ': ' + CAPTURES[keys[j]].totalSz + ' bytes');
        return r;
    },

    clear: function() { REDIRECT = {}; REPL_ACTIVE = false; return 'OK'; },
    reset: function() { SEEN = {}; send({t:'reset'}); return 'OK'; },

    status: function() {
        return {
            hits: STATS.hits, captured: STATS.captured,
            redirected: STATS.redirected, replaced: STATS.replaced,
            caps: Object.keys(CAPTURES).length, rules: Object.keys(REDIRECT).length
        };
    }
};

send({t: 'ready', msg: 'SMD v8 loaded (hFile-tracked).'});
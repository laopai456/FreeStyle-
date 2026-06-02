// scan_ic_diff.js
// 分两轮扫描: 第一轮(当前状态) → 等用户操作 → 第二轮 → 对比差异
// 用法: 脚本加载后先扫一次, 用户进练习场, 输入 'scan' 再扫一次, 输入 'diff' 看差异

var SRC_IC = 50125461;
var icHex = ('0' + (SRC_IC & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 8) & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 16) & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 24) & 0xFF).toString(16)).slice(-2);

var scan1 = null;  // 第一轮结果
var scan2 = null;  // 第二轮结果

function doScan(label) {
    var gameMod = Process.getModuleByName('FreeStyle.exe');
    var hits = [];

    // 扫游戏模块
    Memory.scanSync(gameMod.base, gameMod.size, icHex).forEach(function(m) {
        hits.push({addr: m.address.toString(), inModule: true});
    });

    // 扫堆
    Process.enumerateRanges('rw-').forEach(function(range) {
        var rm = Process.findModuleByAddress(range.base);
        if (rm) return;
        try {
            Memory.scanSync(range.base, range.size, icHex).forEach(function(m) {
                hits.push({addr: m.address.toString(), inModule: false});
            });
        } catch(e) {}
    });

    send({t:'scan', label: label, count: hits.length});
    return hits;
}

// 暴露给 Python 调用的接口
rpc.exports = {
    scan1: function() {
        scan1 = doScan('第一轮(当前)');
        return scan1.length;
    },
    scan2: function() {
        scan2 = doScan('第二轮(练习场)');
        return scan2.length;
    },
    diff: function() {
        if (!scan1 || !scan2) return '请先执行两轮扫描';

        var set1 = {};
        scan1.forEach(function(h) { set1[h.addr] = true; });
        var set2 = {};
        scan2.forEach(function(h) { set2[h.addr] = true; });

        var only1 = [];  // 只在第一轮
        var only2 = [];  // 只在第二轮(练习场新增)
        var both = [];   // 两轮都有

        scan1.forEach(function(h) {
            if (!set2[h.addr]) only1.push(h.addr);
            else both.push(h.addr);
        });
        scan2.forEach(function(h) {
            if (!set1[h.addr]) only2.push(h.addr);
        });

        send({t:'diff', only1: only1.length, only2: only2.length, both: both.length});

        // 练习场新增的地址最关键 — 直接在 JS 内读上下文，不走 RPC
        only2.forEach(function(addr, i) {
            var ptr = new NativePointer(addr);
            var val = ptr.readU32();
            var ctx = '';
            try {
                var bytes = new Uint8Array(ptr.sub(8).readByteArray(24));
                for (var j = 0; j < bytes.length; j++) {
                    if (j === 8) ctx += '| ';
                    ctx += ('0' + bytes[j].toString(16)).slice(-2) + ' ';
                }
            } catch(e) { ctx = 'read error'; }
            send({t:'new', n:i+1, addr:addr, val:val, ctx:ctx});
        });

        // 检查两轮都有的地址，值是否变了
        both.forEach(function(addr, i) {
            var ptr = new NativePointer(addr);
            var val = ptr.readU32();
            if (val !== SRC_IC) {
                send({t:'changed', n:i+1, addr:addr, oldVal:SRC_IC, newVal:val});
            }
        });

        return {only1: only1.length, only2: only2.length, both: both.length};
    },
    read: function(addrStr) {
        var ptr = new NativePointer(addrStr);
        var ctx = new Uint8Array(ptr.sub(16).readByteArray(48));
        var hex = '';
        for (var i = 0; i < ctx.length; i++) {
            if (i === 16) hex += '| ';
            hex += ('0' + ctx[i].toString(16)).slice(-2) + ' ';
        }
        return hex;
    }
};

send({t:'ready', msg:'就绪。命令: scan1(第一轮) → 进练习场 → scan2(第二轮) → diff(对比)'});

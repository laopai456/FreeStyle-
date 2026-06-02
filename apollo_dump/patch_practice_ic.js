// patch_practice_ic.js
// 自动定位练习场 ItemCode 地址并覆写为 50125711
// 流程: scan1(大厅) → 进练习场 → scan2 → 找新增 → 写入

var SRC_IC = 50125461;
var DST_IC = 50125711;

var icHex = ('0' + (SRC_IC & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 8) & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 16) & 0xFF).toString(16)).slice(-2) + ' ' +
            ('0' + ((SRC_IC >> 24) & 0xFF).toString(16)).slice(-2);

var dstBytes = [];
dstBytes.push(DST_IC & 0xFF);
dstBytes.push((DST_IC >> 8) & 0xFF);
dstBytes.push((DST_IC >> 16) & 0xFF);
dstBytes.push((DST_IC >> 24) & 0xFF);

var scan1 = null;
var scan2 = null;

function doScan() {
    var hits = [];
    Process.enumerateRanges('rw-').forEach(function (range) {
        var rm = Process.findModuleByAddress(range.base);
        if (rm) return; // 跳过已加载模块，只扫堆
        try {
            Memory.scanSync(range.base, range.size, icHex).forEach(function (m) {
                hits.push(m.address.toString());
            });
        } catch (e) {}
    });
    // 也扫游戏模块
    try {
        var gm = Process.getModuleByName('FreeStyle.exe');
        Memory.scanSync(gm.base, gm.size, icHex).forEach(function (m) {
            hits.push(m.address.toString());
        });
    } catch (e) {}
    return hits;
}

rpc.exports = {
    scan1: function () {
        scan1 = doScan();
        return scan1.length;
    },
    scan2: function () {
        scan2 = doScan();
        return scan2.length;
    },
    diff: function () {
        if (!scan1 || !scan2) return {error: '请先执行 scan1 和 scan2'};

        var set1 = {};
        scan1.forEach(function (a) { set1[a] = true; });

        var newAddrs = [];
        scan2.forEach(function (a) {
            if (!set1[a]) newAddrs.push(a);
        });
        return {newCount: newAddrs.length, addrs: newAddrs};
    },
    patch: function (addrStr) {
        var ptr = new NativePointer(addrStr);
        var oldVal = ptr.readU32();
        ptr.writeU32(DST_IC);
        var newVal = ptr.readU32();
        return {addr: addrStr, old: oldVal, new: newVal};
    },
    restore: function (addrStr) {
        var ptr = new NativePointer(addrStr);
        ptr.writeU32(SRC_IC);
        return {addr: addrStr, restored: ptr.readU32()};
    }
};

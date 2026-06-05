// scan_ic.js
// 扫描内存中所有包含 ItemCode 50125461 的位置

var SRC_IC = 50125461;
var DST_IC = 50125711;

// 50125461 = 0x02FCDA95 (小端: 95 DA FC 02)
var icBytes = [];
icBytes.push(SRC_IC & 0xFF);
icBytes.push((SRC_IC >> 8) & 0xFF);
icBytes.push((SRC_IC >> 16) & 0xFF);
icBytes.push((SRC_IC >> 24) & 0xFF);
var pattern = '';
for (var i = 0; i < icBytes.length; i++) {
    if (i > 0) pattern += ' ';
    pattern += ('0' + icBytes[i].toString(16)).slice(-2);
}

send({t:'info', msg:'扫描 ItemCode ' + SRC_IC + ' (0x' + SRC_IC.toString(16) + ')'});
send({t:'info', msg:'搜索模式: ' + pattern});

// 获取游戏模块范围
var gameMod = Process.getModuleByName('FreeStyle.exe');
send({t:'info', msg:'FreeStyle.exe base=' + gameMod.base + ' size=' + gameMod.size});

var allHits = [];

// 扫描游戏模块的 .text + .data
Memory.scan(gameMod.base, gameMod.size, pattern, {
    onMatch: function (address, size) {
        var offset = address.sub(gameMod.base);
        var mod = Process.findModuleByAddress(address);
        var modName = mod ? mod.name : '???';
        var modOffset = mod ? address.sub(mod.base) : '?';

        // 读取前后上下文（前后各8字节）
        var ctxBefore = new Uint8Array(address.sub(8).readByteArray(8));
        var ctxAfter = new Uint8Array(address.add(4).readByteArray(8));

        var hexBefore = '';
        for (var i = 0; i < ctxBefore.length; i++) hexBefore += ('0' + ctxBefore[i].toString(16)).slice(-2) + ' ';
        var hexAfter = '';
        for (var i = 0; i < ctxAfter.length; i++) hexAfter += ('0' + ctxAfter[i].toString(16)).slice(-2) + ' ';

        allHits.push({
            addr: address.toString(),
            offset: offset.toString(),
            mod: modName,
            modOffset: modOffset.toString(),
            before: hexBefore,
            after: hexAfter
        });
    },
    onComplete: function () {
        send({t:'scan_result', count: allHits.length});

        for (var i = 0; i < allHits.length; i++) {
            var h = allHits[i];
            send({t:'hit',
                n: i + 1,
                addr: h.addr,
                offset: h.offset,
                mod: h.mod,
                modOffset: h.modOffset,
                ctx: h.before + '| ' + pattern.replace(/ /g,' ') + ' |' + h.after
            });
        }

        send({t:'done', msg:'扫描完成，共 ' + allHits.length + ' 处'});

        // 额外: 也扫一下所有可读内存段（不在 FreeStyle.exe 模块内的）
        send({t:'info', msg:'继续扫描堆内存...'});
        var heapHits = 0;

        Process.enumerateRanges('r--').forEach(function (range) {
            // 跳过游戏模块（已扫过）和系统 DLL
            var rm = Process.findModuleByAddress(range.base);
            if (rm && rm.name === 'FreeStyle.exe') return;
            if (rm) return; // 跳过所有已加载模块

            try {
                Memory.scan(range.base, range.size, pattern, {
                    onMatch: function (address, size) {
                        heapHits++;
                        var ctxBefore = new Uint8Array(address.sub(8).readByteArray(8));
                        var ctxAfter = new Uint8Array(address.add(4).readByteArray(8));
                        var hexBefore = '';
                        for (var i = 0; i < ctxBefore.length; i++) hexBefore += ('0' + ctxBefore[i].toString(16)).slice(-2) + ' ';
                        var hexAfter = '';
                        for (var i = 0; i < ctxAfter.length; i++) hexAfter += ('0' + ctxAfter[i].toString(16)).slice(-2) + ' ';

                        send({t:'heap_hit',
                            n: heapHits,
                            addr: address.toString(),
                            size: range.size,
                            prot: range.protection,
                            ctx: hexBefore + '| ' + pattern.replace(/ /g,' ') + ' |' + hexAfter
                        });
                    },
                    onComplete: function () {}
                });
            } catch (e) {
                // 某些内存区域不可读，跳过
            }
        });

        send({t:'heap_done', count: heapHits});
    }
});

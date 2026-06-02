// trace_practice_smd.js
// 第一步: hook CreateFileA，抓练习场加载原始 SMD 时的调用栈

// --- 先探测可用 API ---
send({t:'probe', msg:'探测 Frida API...'});
send({t:'probe', msg:'typeof Module = ' + typeof Module});
send({t:'probe', msg:'typeof Process = ' + typeof Process});
send({t:'probe', msg:'typeof Interceptor = ' + typeof Interceptor});
send({t:'probe', msg:'typeof Thread = ' + typeof Thread});

// --- 找 CreateFileA 地址 ---
var pCreateFileA = null;

// 方法 1: Process.getModuleByName (你的 apollo_killer_static.js 用过，确认能用)
try {
    var k32 = Process.getModuleByName('kernel32.dll');
    send({t:'probe', msg:'kernel32 base = ' + k32.base});
    // 尝试枚举导出
    if (typeof k32.enumerateExports === 'function') {
        var exps = k32.enumerateExports();
        for (var i = 0; i < exps.length; i++) {
            if (exps[i].name === 'CreateFileA') {
                pCreateFileA = exps[i].address;
                break;
            }
        }
        send({t:'probe', msg:'enumerateExports 找到 CreateFileA = ' + pCreateFileA});
    } else {
        send({t:'probe', msg:'enumerateExports 不可用'});
    }
} catch (e) {
    send({t:'probe', msg:'方法1失败: ' + e});
}

// 方法 2: 尝试 Module.findExportByName
if (!pCreateFileA) {
    try {
        pCreateFileA = Module.findExportByName('kernel32.dll', 'CreateFileA');
        send({t:'probe', msg:'Module.findExportByName = ' + pCreateFileA});
    } catch (e) {
        send({t:'probe', msg:'方法2失败: ' + e});
    }
}

// 方法 3: 尝试 Module.getExportByName
if (!pCreateFileA) {
    try {
        pCreateFileA = Module.getExportByName('kernel32.dll', 'CreateFileA');
        send({t:'probe', msg:'Module.getExportByName = ' + pCreateFileA});
    } catch (e) {
        send({t:'probe', msg:'方法3失败: ' + e});
    }
}

if (!pCreateFileA) {
    send({t:'error', msg:'所有方法都无法找到 CreateFileA，放弃'});
} else {
    send({t:'ready', msg:'CreateFileA @ ' + pCreateFileA + '，开始 hook'});

    var TARGET_FILE = 'i50125461_FN.smd';
    var hitCount = 0;

    Interceptor.attach(pCreateFileA, {
        onEnter: function (args) {
            var path = null;
            try {
                path = args[0].readUtf8String();
            } catch (e) {
                return;
            }

            if (!path || path.indexOf(TARGET_FILE) === -1) return;

            hitCount++;
            send({t:'hit', n:hitCount, file:path, time:new Date().toTimeString()});

            try {
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                var frames = [];
                for (var i = 0; i < bt.length; i++) {
                    var addr = bt[i];
                    var mod = Process.findModuleByAddress(addr);
                    frames.push({
                        i: i,
                        addr: addr.toString(),
                        mod: mod ? mod.name : '???',
                        offset: mod ? addr.sub(mod.base).toString() : '?'
                    });
                }
                send({t:'backtrace', n:hitCount, frames:frames});
            } catch (e) {
                send({t:'error', msg:'backtrace失败: ' + e});
            }

            if (hitCount >= 3) {
                send({t:'done', msg:'已捕获 3 次，卸载 hook'});
                Interceptor.detachAll();
            }
        }
    });

    send({t:'ready', msg:'就绪，进练习场触发加载...'});
}

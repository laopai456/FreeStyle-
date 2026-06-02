'use strict';
// frida_trace_smd.js — Hook CreateFileW 抓 SMD 加载调用链
// 用法: 进商城后触发 SMD 加载，打印调用栈

// Cache module base
var modBase = Process.getModuleByName('FreeStyle.exe').base;
var kernel32 = Module.findExportByName('kernel32.dll', 'CreateFileW');

if (kernel32) {
    Interceptor.attach(kernel32, {
        onEnter: function(args) {
            var path = args[0].readUtf16String();
            if (path && path.indexOf('.smd') >= 0) {
                console.log('\n[SMD] CreateFileW: ' + path);
                console.log('[SMD] Call stack:');
                var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                var maxFrames = 15;
                for (var i = 1; i < Math.min(bt.length, maxFrames); i++) {
                    var offset = bt[i].sub(modBase).toInt32();
                    var modName = '';
                    try {
                        var m = Process.findModuleByAddress(bt[i]);
                        if (m) modName = m.name;
                    } catch(e) {}
                    if (modName.indexOf('FreeStyle') >= 0 || modName.indexOf('kernel') >= 0) {
                        var offsetHex = offset.toString(16).padStart(8, '0');
                        console.log('  #' + i + ' 0x' + offsetHex + ' (' + modName + ')');
                    }
                }
            }
        }
    });
    console.log('[SMD] Hooked CreateFileW. Go to shop / equip item to trigger SMD loading.');
} else {
    console.log('[SMD] Cannot find CreateFileW');
}

// ============================================================
// smd_redirect_v13b.js — 全自动版, 无 RPC, 无需手动命令
// 加载后 8 秒自动安装 hook 并启用替换
// ============================================================
var SOURCE = 'i50123971';
var TARGET = 'i50125711';
var replaceCount = 0;
var MAX_REPLACE = 10;

function str2bytes(s) {
    var bytes = [];
    for (var i = 0; i < s.length; i++)
        bytes.push(s.charCodeAt(i));
    bytes.push(0);
    return bytes;
}

function doHook() {
    try {
        var base = Process.getModuleByName('FreeStyle.exe').base;
        var targetFunc = base.add(0x21e25b0);
        var page = targetFunc.and(ptr(0xFFFFF000));
        
        Memory.protect(page, 4096, 'rwx');
        
        Interceptor.attach(targetFunc, {
            onEnter: function(args) {
                if (replaceCount >= MAX_REPLACE) return;
                var name;
                try { name = args[0].readAnsiString(64); } catch(e) { return; }
                if (name.indexOf(SOURCE) < 0) return;
                try {
                    var newName = name.replace(SOURCE, TARGET);
                    args[0].writeByteArray(str2bytes(newName));
                    replaceCount++;
                    send({t: 'REPLACE', from: name, to: newName, n: replaceCount});
                } catch(e) { send({t: 'ERR', msg: '' + e}); }
            }
        });
        
        Memory.protect(page, 4096, 'rx');
        send({t: 'STATUS', msg: 'HOOKED. ' + SOURCE + ' -> ' + TARGET + '. Auto-replacing.'});
    } catch(e) {
        send({t: 'ERR', msg: 'Hook install failed: ' + e});
    }
}

// 延迟 8 秒等游戏初始化完毕
setTimeout(doHook, 8000);
send({t: 'STATUS', msg: 'Waiting 8s before hook install...'});
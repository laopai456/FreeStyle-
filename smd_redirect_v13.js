// ============================================================
// smd_redirect_v13.js — hook 0x21e25b0, SString 替换发型
// 原理: 调用栈已确认 0x21e25b0 在 SMD 加载路径中
//       args[0] inline SString 直接包含文件名 (已验证: readAnsiString)
//       过滤 .smd → 替换 item code → 游戏自然加载目标 SMD
// ============================================================
var enabled = false;
var replaceCount = 0;
var MAX_REPLACE = 20;

var SOURCE = 'i50123971';
var TARGET = 'i50125711';

function str2bytes(s) {
    var bytes = [];
    for (var i = 0; i < s.length; i++)
        bytes.push(s.charCodeAt(i));
    bytes.push(0);
    return bytes;
}

// ============================================================
// Install hook
// ============================================================
var targetFunc = null;
var hookInstalled = false;

function installHook() {
    if (hookInstalled) return 'already';
    
    var base = Process.getModuleByName('FreeStyle.exe').base;
    targetFunc = base.add(0x21e25b0);
    
    var page = targetFunc.and(ptr(0xFFFFF000));
    Memory.protect(page, 4096, 'rwx');
    
    Interceptor.attach(targetFunc, {
        onEnter: function(args) {
            if (!enabled) return;
            if (replaceCount >= MAX_REPLACE) return;
            
            var name;
            try {
                name = args[0].readAnsiString(64);
            } catch(e) { return; }
            
            // 检查是否包含源 item code (不含.smd后缀)
            if (name.indexOf(SOURCE) < 0) return;
            
            try {
                var newName = name.replace(SOURCE, TARGET);
                args[0].writeByteArray(str2bytes(newName));
                replaceCount++;
                send({t: 'REPLACE', from: name, to: newName, n: replaceCount});
            } catch(e) {
                send({t: 'ERR', msg: 'write fail: ' + e});
            }
        }
    });
    
    Memory.protect(page, 4096, 'rx');
    hookInstalled = true;
    send({t: 'HOOK', msg: '0x21e25b0 hooked, page rx restored'});
}

// ============================================================
// RPC
// ============================================================
rpc.exports = {
    tryHook: function() {
        if (hookInstalled) return 'already';
        installHook();
        return 'ok';
    },
    
    enable: function() {
        enabled = true;
        replaceCount = 0;
        send({t: 'STATE', msg: 'ENABLED. ' + SOURCE + ' -> ' + TARGET});
        return 'enabled';
    },
    
    disable: function() {
        enabled = false;
        send({t: 'STATE', msg: 'DISABLED. Total replaced: ' + replaceCount});
        return 'disabled';
    },
    
    status: function() {
        return JSON.stringify({enabled: enabled, count: replaceCount, hooked: hookInstalled});
    }
};

send({t: 'READY', msg: 'v13 ready. tryHook | enable | disable | status'});
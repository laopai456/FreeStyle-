// ============================================================
// smd_redirect_v12.js — SString 替换方案
// 
// 原理: hook 0x21e25b0 (文件名/SString处理函数), 
//       在 args[0] inline SString 中替换 source → target item code
//       游戏自然打开目标 SMD, 完整加载, 无大小兼容问题
// ============================================================

var targetFunc = null;
var base = null;
var enabled = false;
var replaceCount = 0;
var MAX_REPLACE = 50;

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
function installHook() {
    if (targetFunc === null) {
        send({t: 'err', msg: 'targetFunc not set'});
        return;
    }
    
    var page = targetFunc.and(ptr(0xFFFFF000));
    Memory.protect(page, 4096, 'rwx');
    
    Interceptor.attach(targetFunc, {
        onEnter: function(args) {
            if (!enabled) return;
            if (replaceCount >= MAX_REPLACE) return;
            
            try {
                var name = args[0].readAnsiString(64);
                if (name && name.indexOf(SOURCE) >= 0) {
                    var newName = name.replace(SOURCE, TARGET);
                    args[0].writeByteArray(str2bytes(newName));
                    replaceCount++;
                    send({t: 'REPLACE', from: name, to: newName, n: replaceCount});
                }
            } catch(e) {}
        }
    });
    
    Memory.protect(page, 4096, 'rx');
    send({t: 'step', msg: 'hook installed, page restored rx'});
}

// ============================================================
// RPC
// ============================================================
var hookTried = false;

rpc.exports = {
    tryHook: function() {
        if (hookTried) return 'already tried';
        hookTried = true;
        
        base = Process.getModuleByName('FreeStyle.exe').base;
        
        var callSite = base.add(0x1eec939);
        var bytes = callSite.readByteArray(5);
        var b = new Uint8Array(bytes);
        if (b[0] !== 0xE8) {
            send({t: 'err', msg: 'Not a CALL at 0x1eec939: ' + b[0].toString(16)});
            return 'bad opcode';
        }
        
        var rel = b[1] | (b[2] << 8) | (b[3] << 16) | (b[4] << 24);
        targetFunc = callSite.add(5 + rel);
        send({t: 'step', msg: 'targetFunc = ' + targetFunc});
        
        installHook();
        return 'ok';
    },
    
    enable: function() {
        enabled = true;
        replaceCount = 0;
        send({t: 'step', msg: 'REPLACE ENABLED. ' + SOURCE + ' -> ' + TARGET});
        return 'enabled';
    },
    
    disable: function() {
        enabled = false;
        send({t: 'step', msg: 'REPLACE DISABLED. Total: ' + replaceCount});
        return 'disabled';
    },
    
    status: function() {
        return JSON.stringify({
            enabled: enabled,
            replaceCount: replaceCount,
            targetFunc: targetFunc ? targetFunc.toString() : null
        });
    }
};

send({t: 'ready', msg: 'v12 ready. tryHook | enable | disable | status'});
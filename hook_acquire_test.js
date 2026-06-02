/**
 * hook_acquire_test.js — 实验: Memory.protect + Interceptor.attach AcquireSMD
 *
 * 目标: 测试 Apollo 是否拦截 .text 页属性变更
 * 如果游戏不崩 → 后续可 hook AcquireSMD 直接改文件名参数
 */
var base = Process.getModuleByName('FreeStyle.exe').base;
var k32 = Process.getModuleByName('kernel32.dll');
var N = 0;

// ============================================================
// Step 1: 保持 ReadFile SSKF 监控 (不动, 用于诊断)
// ============================================================
var pReadFile = k32.getExportByName('ReadFile');
Interceptor.attach(pReadFile, {
    onEnter: function(args) {
        this.buf = args[1];
        this.sz  = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (retval.toInt32() === 0 || this.sz < 4) return;
        try {
            var raw = this.buf.readByteArray(4);
            var m = new Uint8Array(raw);
            if (m[0] !== 0x53 || m[1] !== 0x53 || m[2] !== 0x4B || m[3] !== 0x46) return;
            N++;
            var name = '';
            try { name = this.buf.add(8).readAnsiString(64); } catch(e) {}
            // EBP chain for AcquireSMD frame
            var ebp = this.context.ebp;
            var frames = [];
            for (var i = 0; i < 12 && ebp && !ebp.isNull(); i++) {
                try {
                    var ret = ebp.add(4).readPointer();
                    frames.push({ret: ret, ebp: ebp});
                    ebp = ebp.readPointer();
                } catch(e) { break; }
            }
            send({t: 'sskf', n: N, name: name, sz: this.sz, frames: frames.map(function(f) {
                var mod = Process.findModuleByAddress(f.ret);
                var off = mod ? f.ret.sub(mod.base) : null;
                return {
                    addr: f.ret.toString(),
                    mod: mod ? mod.name : '?',
                    off: off ? '0x' + off.toString(16) : '?',
                    ebp: f.ebp.toString()
                };
            })});
        } catch(e) {}
    }
});

// ============================================================
// Step 2: Memory.protect AcquireSMD 所在页 + Interceptor.attach
// ============================================================
function tryHookAcquire() {
    // 已知: 0x1eec93e 是 RefreshItem 调用 AcquireSMD 后的返回地址
    // 5字节前就是 CALL AcquireSMD 指令
    var retAddr = base.add(0x1eec93e);
    var callSite = retAddr.sub(5);
    
    send({t: 'step1', msg: 'Reading CALL at ' + callSite});
    
    var acquireSMD;
    try {
        var callBytes = callSite.readByteArray(5);
        var b = new Uint8Array(callBytes);
        
        if (b[0] === 0xE8) {
            var rel = (b[1] | (b[2] << 8) | (b[3] << 16) | (b[4] << 24)) >>> 0;
            if (rel >= 0x80000000) rel = rel - 0x100000000;
            acquireSMD = retAddr.add(rel);
            send({t: 'step1', msg: 'CALL target (AcquireSMD entry): ' + acquireSMD});
        } else {
            var hex = Array.from(b).map(function(x){return x.toString(16).padStart(2,'0')}).join(' ');
            send({t: 'err', msg: 'Not E8 at ' + callSite + ': ' + hex});
            if (b[0] === 0xFF) {
                send({t: 'warn', msg: 'CALL indirect (0xFF), need manual target'});
            }
            return false;
        }
    } catch(e) {
        send({t: 'err', msg: 'Failed to read CALL: ' + e});
        return false;
    }
    
    // Step 2b: Memory.protect
    var pageAddr = acquireSMD.and(0xFFFFF000);
    send({t: 'step2', msg: 'Memory.protect page ' + pageAddr + ' → rwx'});
    
    try {
        Memory.protect(pageAddr, 0x1000, 'rwx');
        send({t: 'step2', msg: 'Memory.protect OK'});
    } catch(e) {
        send({t: 'err', msg: 'Memory.protect FAILED: ' + e});
        return false;
    }
    
    // Step 2c: 也 protect RefreshItem 调用页 (callSite 所在页)
    var callPage = retAddr.and(0xFFFFF000);
    if (!callPage.equals(pageAddr)) {
        try {
            Memory.protect(callPage, 0x1000, 'rwx');
            send({t: 'protect', msg: 'Call site page ' + callPage + ' → rwx OK'});
        } catch(e) {
            send({t: 'protect', msg: 'Call site protect (optional): ' + e});
        }
    } else {
        callPage = null;  // same page, already protected
    }
    
    // Step 2d: Interceptor.attach
    send({t: 'step3', msg: 'Interceptor.attach at ' + acquireSMD});
    
    try {
        Interceptor.attach(acquireSMD, {
            onEnter: function(args) {
                // 前20个调用打印真实返回地址 + args[0] 字符串 (诊断)
                if (callCount < 20) {
                    callCount++;
                    var retOff = -1;
                    try { retOff = Memory.readPointer(this.context.esp).sub(base).toInt32(); } catch(e) {}
                    var name = '';
                    try { name = args[0].readAnsiString(64); } catch(e) {}
                    send({t: 'DIAG', n: callCount, ret: retOff.toString(16), name: name});
                }
                
                // 正式过滤: AcquireSMD 调用
                if (callCount >= 20) {
                    var retOff = Memory.readPointer(this.context.esp).sub(base).toInt32();
                    if (retOff !== 0x1eec93e && retOff !== 0x1eecba7) return;
                    var name = '';
                    try { name = args[0].readAnsiString(64); } catch(e) {}
                    if (name && name.length > 0 && name.length < 64)
                        send({t: 'ACQUIRE', off: retOff.toString(16), name: name});
                }
            },
            onLeave: function(retval) {
            }
        });
        send({t: 'step3', msg: 'Interceptor.attach SUCCESS!'});
    } catch(e) {
        send({t: 'err', msg: 'Interceptor.attach FAILED: ' + e});
        // 失败也要恢复页属性
        Memory.protect(pageAddr, 0x1000, 'rx');
        if (callPage) Memory.protect(callPage, 0x1000, 'rx');
        return false;
    }
    
    // Step 2e: 立刻恢复原始页保护 (躲 Apollo 扫描)
    send({t: 'step4', msg: 'Restoring page protection → rx'});
    try {
        Memory.protect(pageAddr, 0x1000, 'rx');
        send({t: 'step4', msg: 'AcquireSMD page restored to rx'});
    } catch(e) {
        send({t: 'err', msg: 'Restore AcquireSMD page FAILED: ' + e});
    }
    if (callPage) {
        try {
            Memory.protect(callPage, 0x1000, 'rx');
            send({t: 'step4', msg: 'Call site page restored to rx'});
        } catch(e) {
            send({t: 'err', msg: 'Restore call site page FAILED: ' + e});
        }
    }
    send({t: 'step4', msg: 'All pages rx. Apollo shouldn\'t detect anything.'});
    return true;
}

// ============================================================
// RPC: 延迟执行 hook (用户手动触发)
// ============================================================
var hookTried = false;
var callCount = 0;

rpc.exports = {
    tryHook: function() {
        if (hookTried) return 'Already tried (check game alive)';
        hookTried = true;
        var ok = tryHookAcquire();
        return ok ? 'Hook installed. Check if game is alive.' : 'Hook failed.';
    },
    status: function() {
        return {n: N, hookTried: hookTried};
    }
};

send({t: 'ready', msg: 'Acquire hook test ready. Type "try" to install hook.'});
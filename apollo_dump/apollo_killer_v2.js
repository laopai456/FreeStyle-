// apollo_killer_v2.js — 只堵杀 + 防调试检测
var base = ptr('0x400000');
var DST_IC = 50125711;
var SRC_IC = 50125461;
var APOLLO_EX = 0;
var KILLS = 0, EXITS = 0, HAIR = 0;

// 0. 启动时: 直接修补 PEB.BeingDebugged = 0
var pebAddr = ptr(0).add(Process.getCurrentPEB());
try {
    pebAddr.add(0x2).writeU8(0);      // BeingDebugged = 0
    pebAddr.add(0xBC).writeU32(0);    // NtGlobalFlag = 0
    send({t: 'info', msg: 'PEB patched (BeingDebugged=0)'});
} catch(e) { send({t: 'info', msg: 'PEB patch failed: ' + e.message}); }

// 1. 异常处理 — 只吞系统异常
Process.setExceptionHandler(function(details) {
    if (details.type === 'system') {
        APOLLO_EX++;
        send({t: 'swallow_exception', n: APOLLO_EX, addr: details.address.toString()});
        return true;
    }
    return false;
});

// ═══ Block kill paths ═══
var ntdll = Process.getModuleByName('ntdll.dll');
var kernel32 = Process.getModuleByName('kernel32.dll');

function hookFunc(module, expName, cb) {
    try {
        var addr = module.getExportByName(expName);
        Interceptor.attach(addr, cb);
        send({t: 'ok', func: expName, addr: addr.toString()});
    } catch(e) { send({t: 'fail', func: expName, msg: e.message}); }
}

hookFunc(ntdll, 'NtTerminateProcess', {
    onEnter: function(args) {
        if (args[0].toInt32() === -1) return;
        KILLS++; send({t: 'block_kill', n: KILLS, func: 'NtTerminateProcess'});
        args[0] = ptr(-1);
    }
});

hookFunc(kernel32, 'TerminateProcess', {
    onEnter: function(args) {
        KILLS++; send({t: 'block_kill', n: KILLS, func: 'TerminateProcess'});
        this.err = true;
    },
    onLeave: function(retval) { if (this.err) retval.replace(0); }
});

hookFunc(ntdll, 'RtlExitUserProcess', {
    onEnter: function(args) {
        EXITS++; send({t: 'block_exit', n: EXITS, func: 'RtlExitUserProcess'});
        this.err = true;
    },
    onLeave: function(retval) { if (this.err) retval.replace(0); }
});

hookFunc(kernel32, 'ExitProcess', {
    onEnter: function(args) {
        EXITS++; send({t: 'block_exit', n: EXITS, func: 'ExitProcess'});
        this.err = true;
    },
    onLeave: function(retval) { if (this.err) retval.replace(0); }
});

hookFunc(ntdll, 'RtlReportSilentProcessExit', {
    onEnter: function(args) { send({t: 'block_kill', func: 'RtlReportSilentProcessExit'}); },
    onLeave: function(retval) { retval.replace(0); }
});

hookFunc(ntdll, 'NtRaiseHardError', {
    onEnter: function(args) { send({t: 'block_kill', func: 'NtRaiseHardError'}); },
    onLeave: function(retval) { retval.replace(0); }
});

// ═══ 发型替换: sprintf hook ═══
hookFunc(Process.getModuleByName('MSVCR100.dll'), 'sprintf', {
    onEnter: function(args) {
        var caller = this.returnAddress;
        var textStart = base.add(0x1000);
        var textEnd = base.add(0x42D000);
        if (caller.compare(textStart) < 0 || caller.compare(textEnd) > 0) return;
        for (var i = 2; i <= 4; i++) {
            if (args[i].toInt32() === SRC_IC) {
                args[i] = ptr(DST_IC);
                HAIR++;
                send({t: 'hair_patch', n: HAIR, idx: i});
                return;
            }
        }
    }
});

// ═══ ApolloCT CRC patch ═══
try {
    var am = Process.getModuleByName('ApolloCT.dll');
    var crcAddrs = [0x1A3C54, 0x1BE222];
    var crcOk = 0;
    for (var i = 0; i < crcAddrs.length; i++) {
        var a = am.base.add(crcAddrs[i]);
        Memory.protect(a.and(ptr(0xFFFFF000)), 0x1000, 'rwx');
        a.writeU8(0x33); a.add(1).writeU8(0xC0); a.add(2).writeU8(0xC3);
        crcOk++;
    }
    send({t: 'info', msg: 'ApolloCT CRC: ' + crcOk + '/' + crcAddrs.length});
} catch(e) { send({t: 'info', msg: 'ApolloCT未加载'}); }

// ═══ 定期报告 ═══
setInterval(function() {
    send({t: 'report', kills: KILLS, exits: EXITS, swallow: APOLLO_EX, hair: HAIR});
}, 5000);

send({t: 'ready', msg: '全部就绪 — 进房间测试'});
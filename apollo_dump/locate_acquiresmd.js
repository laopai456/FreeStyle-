'use strict';

// locate_acquiresmd.js — Frida 定位 DGraphicAcquireSMD 入口
// 原理:
//   1. Memory.scan(.text, "SSKF") → 定位函数体内魔数比较处
//   2. 从命中地址往回扫描 x86 函数序言 (push ebp; mov ebp, esp)
//   3. hook 候选入口, 验证是否被调用 + 捕获参数

var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var textSection = null;
fsMod.enumerateSections().forEach(function(s) {
    if (s.name === '.text') textSection = s;
});

var textStart = null;
var textSize = null;
var textEnd = null;
var FOUND_ADDR = null;
var HOOKED_ADDR = null;
var SSKF_COUNT = 0;

function boot() {
    if (!textSection) {
        send({t: 'FATAL', msg: '.text section not found'});
        return;
    }
    textStart = textSection.address;
    textSize = textSection.size;
    textEnd = textStart.add(textSize);
    setTimeout(run, 100);
}

function run() {
    send({t: 'INIT', msg: 'locate_acquiresmd.js — Scanning for DGraphicAcquireSMD entry...'});
    send({t: 'PHASE', msg: 'base=' + base + ' .text=' + textStart + ' size=' + textSize});

    Memory.scan(textStart, textSize, "53 53 4B 46", {
        onMatch: function(address, size) {
            SSKF_COUNT++;
            var offset = address.sub(base).toInt32();
            send({t: 'SSKF_HIT', offset: '0x' + offset.toString(16), addr: address.toString()});
            if (FOUND_ADDR === null) FOUND_ADDR = address;
        },
        onComplete: function() {
            send({t: 'PHASE', msg: 'SSKF scan done: ' + SSKF_COUNT + ' hits'});
            if (SSKF_COUNT === 0) {
                send({t: 'FATAL', msg: 'SSKF not found in .text!'});
                return;
            }
            setTimeout(findPrologue, 20);
        }
    });
}

function findPrologue() {
    send({t: 'PHASE', msg: 'Back-scanning for function prologue from SSKF (0x' + (FOUND_ADDR.sub(base).toInt32()).toString(16) + ')...'});

    var searchStart = FOUND_ADDR.sub(0x1000);
    if (searchStart.compare(textStart) < 0) searchStart = textStart;
    var searchLen = FOUND_ADDR.sub(searchStart).toInt32();

    send({t: 'PHASE', msg: 'Back-scan range: 0x' + (FOUND_ADDR.sub(base).toInt32()).toString(16) + ' - 0x1000 = 0x' + (searchStart.sub(base).toInt32()).toString(16) + ' (' + searchLen + ' bytes)'});

    var candidates = [];
    Memory.scan(searchStart, searchLen, "55", {
        onMatch: function(addr, size) {
            if (addr.compare(FOUND_ADDR) >= 0) return;
            var b2 = addr.add(1).readU8();
            var b3 = addr.add(2).readU8();
            var pattern = null;

            if (b2 === 0x8B && b3 === 0xEC) pattern = 'push ebp; mov ebp, esp';
            else if (b2 === 0x89 && b3 === 0xE5) pattern = 'push ebp; mov ebp, esp (alt)';
            else if (b2 === 0x83 && (b3 & 0xE0) === 0xE0) pattern = 'push ebp; sub esp, imm8';
            else if (b2 === 0x81) pattern = 'push ebp; sub esp, imm32';
            else if (b2 === 0xC8) pattern = 'enter XX, XX';

            if (pattern) {
                var offset = addr.sub(base).toInt32();
                var dist = FOUND_ADDR.sub(addr).toInt32();
                candidates.push({addr: addr, offset: offset, dist: dist, pattern: pattern});
                send({t: 'CANDIDATE', offset: '0x' + offset.toString(16), dist: dist, pattern: pattern});
            }
        },
        onComplete: function() {
            if (candidates.length > 0) {
                candidates.sort(function(a, b) { return a.dist - b.dist; });
                var best = candidates[0];
                HOOKED_ADDR = best.addr;
                send({t: 'SELECT', offset: '0x' + best.offset.toString(16), pattern: best.pattern, msg: 'Selected candidate @ FreeStyle+0x' + best.offset.toString(16) + ' [' + best.pattern + '] (' + best.dist + 'B before SSKF)'});
                setTimeout(hookCandidate, 20);
                return;
            }

            send({t: 'WARN', msg: 'No standard prologue. Scanning for FPO/hotpatch patterns...'});
            var fpoCandidates = [];
            Memory.scan(searchStart, searchLen, "81 EC", {
                onMatch: function(addr) {
                    if (addr.compare(FOUND_ADDR) >= 0) return;
                    var offset = addr.sub(base).toInt32();
                    var dist = FOUND_ADDR.sub(addr).toInt32();
                    fpoCandidates.push({addr: addr, offset: offset, dist: dist, pattern: 'sub esp, imm32 (FPO)'});
                },
                onComplete: function() {
                    if (fpoCandidates.length > 0) {
                        fpoCandidates.sort(function(a, b) { return a.dist - b.dist; });
                        var best = fpoCandidates[0];
                        HOOKED_ADDR = best.addr;
                        send({t: 'SELECT', offset: '0x' + best.offset.toString(16), pattern: best.pattern, msg: 'FPO candidate @ FreeStyle+0x' + best.offset.toString(16) + ' (' + best.dist + 'B before SSKF)'});
                        setTimeout(hookCandidate, 20);
                        return;
                    }

                    send({t: 'WARN', msg: 'No FPO either. Dumping hex around SSKF for manual analysis...'});
                    var dumpStart = FOUND_ADDR.sub(0x200);
                    if (dumpStart.compare(textStart) < 0) dumpStart = textStart;
                    var dumpBytes = [];
                    for (var i = 0; i < 0x200; i++) {
                        dumpBytes.push(dumpStart.add(i).readU8().toString(16).padStart(2, '0'));
                    }
                    send({t: 'HEXDUMP', offset: '0x' + dumpStart.sub(base).toInt32().toString(16), data: dumpBytes.join(' ')});
                    HOOKED_ADDR = FOUND_ADDR.sub(200);
                    send({t: 'SELECT', offset: '0x' + HOOKED_ADDR.sub(base).toInt32().toString(16), pattern: 'GUESS', msg: 'Guessing entry ~200B before SSKF @ FreeStyle+0x' + HOOKED_ADDR.sub(base).toInt32().toString(16)});
                    setTimeout(hookCandidate, 20);
                }
            });
        }
    });
}

function hookCandidate() {
    if (!HOOKED_ADDR) {
        send({t: 'FATAL', msg: 'No candidate address to hook'});
        return;
    }

    var hookedOffset = HOOKED_ADDR.sub(base).toInt32();
    send({t: 'PHASE', msg: 'Installing hook @ FreeStyle+0x' + hookedOffset.toString(16) + '...'});

    try {
        Interceptor.attach(HOOKED_ADDR, {
            onEnter: function(args) {
                var stack = Thread.backtrace(this.context, Backtracer.FUZZY).map(function(v) {
                    var mod = Process.findModuleByAddress(v);
                    if (mod) return mod.name + '+0x' + v.sub(mod.base).toInt32().toString(16);
                    return v.toString();
                }).join(' <- ');

                var argInfo = '';
                for (var i = 0; i < Math.min(args.length, 6); i++) {
                    try {
                        var ap = args[i];
                        if (ap.isNull()) { argInfo += ' arg' + i + '=NULL'; continue; }
                        var str = ap.readUtf16String();
                        if (str && str.length > 0 && str.length < 200) { argInfo += ' arg' + i + '="' + str + '"'; }
                        else { argInfo += ' arg' + i + '=' + ap.toString(); }
                    } catch(e) { argInfo += ' arg' + i + '=' + args[i].toString(); }
                }

                send({t: 'HOOK_HIT',
                    offset: '0x' + hookedOffset.toString(16),
                    args: argInfo,
                    tid: Process.getCurrentThreadId(),
                    stack: stack
                });
            },
            onLeave: function(retval) {
                send({t: 'HOOK_LEAVE', offset: '0x' + hookedOffset.toString(16), retval: retval.toString()});
            }
        });
        send({t: 'SUCCESS', msg: 'Hook live @ FreeStyle+0x' + hookedOffset.toString(16) + '. Waiting for calls...'});
    } catch(e) {
        send({t: 'ERROR', msg: 'Hook installation failed: ' + e});
    }
}

setTimeout(boot, 300);
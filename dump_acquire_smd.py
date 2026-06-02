"""
dump_acquire_smd.py — 反汇编 AcquireSMD 候选函数
dump 函数字节码 + 尝试从调用者栈帧读 SString
"""
import frida, subprocess, os, sys, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def find_pid():
    r = subprocess.run(['tasklist','/FI','IMAGENAME eq FreeStyle.exe','/FO','CSV','/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if 'freestyle' in line.lower():
            parts = line.split(',')
            if len(parts) >= 2:
                return int(parts[1].strip('"'))
    return None

JS_CODE = r'''
'use strict';

var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;

// ── 要 dump 的候选函数 ──────────────────────────
var CANDIDATES = [
    { name: 'AcquireSMD',      rva: 0x1eec130, size: 0x800 },  // ~2KB, calls ReadFile twice
    { name: 'AcquireSMD_caller', rva: 0x1eeba30, size: 0x200 }, // 179B caller
    { name: 'ReadFile_wrapper', rva: 0x1de25b0, size: 0x100 },  // 85B direct ReadFile caller
];

// ── 已知返回地址 ────────────────────────────────
var KNOWN_RETS = [
    { rva: 0x1eec93e, label: 'hdr_ret' },
    { rva: 0x1eecba7, label: 'body_ret' },
];

// ── 1. Dump bytes ──────────────────────────────
function hexDump(addr, size) {
    var lines = [];
    for (var off = 0; off < size; off += 16) {
        var hex = '';
        var ascii = '';
        var chunk = Math.min(16, size - off);
        for (var i = 0; i < chunk; i++) {
            var b = addr.add(off + i).readU8();
            hex += ('0' + b.toString(16)).slice(-2) + ' ';
            ascii += (b >= 0x20 && b < 0x7f) ? String.fromCharCode(b) : '.';
        }
        hex = hex.padEnd(49);
        lines.push('  +' + off.toString(16).padStart(4, '0') + '  ' + hex + ' ' + ascii);
    }
    return lines;
}

send({t:'info', msg: 'Dumping candidate functions...'});

for (var c = 0; c < CANDIDATES.length; c++) {
    var cand = CANDIDATES[c];
    var addr = base.add(cand.rva);
    send({t:'DUMP', name: cand.name, rva: '0x' + cand.rva.toString(16), abs: addr.toString()});

    // Try to read bytes
    try {
        var lines = hexDump(addr, cand.size);
        for (var l = 0; l < lines.length; l++) {
            send({t:'HEX', line: lines[l]});
        }
    } catch(e) {
        send({t:'DUMP_ERR', name: cand.name, err: e.message});
    }
}

// ── 2. Hook at known return addresses to read AcquireSMD args ──
// Hook at the CALLER of AcquireSMD: +1eeba30
// When it calls AcquireSMD, [ESP] = ret addr, [ESP+4] = arg0 (SString*)
var hookCount = 0;

var callerAddr = base.add(0x1eeba30);
send({t:'info', msg: 'Hooking AcquireSMD caller at ' + callerAddr + '...'});

// Instead of hooking the entry, hook the specific call site
// From the call stack: AcquireSMD_caller (entry +1eeba30, 179 bytes) calls AcquireSMD
// Let's find the CALL instruction inside +1eeba30 that calls +1eec130
// Scan for E8 xx xx xx xx (relative call) that targets +1eec130
var callerBase = base.add(0x1eeba30);
var targetAddr = base.add(0x1eec130);
var callSites = [];

send({t:'info', msg: 'Scanning for CALL AcquireSMD in caller function...'});

for (var off = 0; off < 0x200; off++) {
    try {
        var b = callerBase.add(off).readU8();
        if (b === 0xE8) {  // CALL rel32
            var rel = callerBase.add(off + 1).readS32();
            var dest = callerBase.add(off + 5).add(rel);
            if (dest.equals(targetAddr)) {
                callSites.push({
                    offset: off,
                    abs: callerBase.add(off).toString(),
                    rva: '0x' + (0x1eeba30 + off).toString(16)
                });
                send({t:'CALL_SITE', found: true, offset: '0x' + off.toString(16),
                      abs: callerBase.add(off).toString(), target: dest.toString()});
            }
        }
        // Also check indirect call: FF 15 xx xx xx xx (call [imm32])
        if (b === 0xFF) {
            var b2 = callerBase.add(off + 1).readU8();
            if (b2 === 0x15) {
                // indirect call — skip for now
            }
        }
    } catch(e) {}
}

// Also scan AcquireSMD itself for any SString/string references
var acquireBase = base.add(0x1eec130);
send({t:'info', msg: 'Scanning AcquireSMD for string pushes...'});

var stringRefs = [];
for (var off = 0; off < 0x800; off++) {
    try {
        var b = acquireBase.add(off).readU8();
        // PUSH imm32 (68 xx xx xx xx)
        if (b === 0x68) {
            var val = acquireBase.add(off + 1).readU32();
            // Check if it's a pointer to a readable string
            try {
                var p = ptr(val);
                var s = p.readAnsiString(64);
                if (s && s.length > 2 && s.length < 60 && /[a-z]/i.test(s)) {
                    stringRefs.push({offset: '0x' + off.toString(16), str: s, addr: p.toString()});
                }
            } catch(e) {}
        }
        // LEA reg, [imm32] patterns
        // Also look for MOV reg, imm32 that could be string pointers
    } catch(e) {}
}

if (stringRefs.length > 0) {
    send({t:'info', msg: 'Found string references in AcquireSMD:'});
    for (var i = 0; i < stringRefs.length; i++) {
        send({t:'STR_REF', offset: stringRefs[i].offset, str: stringRefs[i].str});
    }
} else {
    send({t:'info', msg: 'No string references found in AcquireSMD'});
}

// ── 3. Now try the real approach: hook at the call site ──
if (callSites.length > 0) {
    var cs = callSites[0]; // Use first call site
    var hookAddr = base.add(0x1eeba30).add(cs.offset);

    // We want to intercept AFTER the call returns, not at the call itself
    // Better: hook at the instruction AFTER the CALL (the return address)
    // The CALL is 5 bytes (E8 + rel32), so ret addr = callSite + 5
    // But we want to read args BEFORE the call, so hook just before the CALL

    // Actually, let's hook AcquireSMD entry directly and scan stack
    var acquireEntry = base.add(0x1eec130);
    send({t:'info', msg: 'Hooking AcquireSMD entry at ' + acquireEntry + '...'});

    Interceptor.attach(acquireEntry, {
        onEnter: function(args) {
            hookCount++;
            if (hookCount > 20) return; // limit noise

            var esp = this.context.esp;
            var ebp = this.context.ebp;

            var info = {
                n: hookCount,
                esp: esp.toString(),
                ebp: ebp.toString(),
                ret: esp.readPointer().toString(),
            };

            // Read args: cdecl, [ESP+4]=arg0, [ESP+8]=arg1, etc.
            var argPtrs = [];
            for (var i = 0; i < 6; i++) {
                try {
                    var a = esp.add(4 + i * 4).readPointer();
                    var s = null;
                    try { s = a.readAnsiString(128); } catch(e) {}
                    var s4 = null;
                    try { s4 = a.add(4).readAnsiString(128); } catch(e) {}
                    var s8 = null;
                    try { s8 = a.add(8).readAnsiString(128); } catch(e) {}
                    var w = null;
                    try { w = a.readUtf16String(128); } catch(e) {}
                    argPtrs.push({
                        idx: i,
                        val: a.toString(),
                        str: s,
                        str4: s4,
                        str8: s8,
                        wide: w
                    });
                } catch(e) {
                    argPtrs.push({idx: i, err: e.message});
                }
            }
            info.args = argPtrs;

            // Also scan deeper stack for .smd strings
            var stackStrings = [];
            for (var off = 0; off < 0x200; off += 4) {
                try {
                    var p = esp.add(off).readPointer();
                    var s = null;
                    try { s = p.readAnsiString(128); } catch(e) {}
                    if (s && s.length > 2 && (s.indexOf('.smd') >= 0 || s.indexOf('.bml') >= 0)) {
                        stackStrings.push({off: '0x' + off.toString(16), str: s, ptr: p.toString()});
                    }
                    // try deref+4
                    try {
                        var s4 = p.add(4).readAnsiString(128);
                        if (s4 && s4.length > 2 && (s4.indexOf('.smd') >= 0 || s4.indexOf('.bml') >= 0)) {
                            stackStrings.push({off: '0x' + off.toString(16) + '+4', str: s4, ptr: p.toString()});
                        }
                    } catch(e) {}
                } catch(e) {}
            }
            info.stackStrings = stackStrings;

            send({t:'ACQUIRE', info: info});
        }
    });

    send({t:'READY', msg: 'AcquireSMD entry hook installed. Trigger SMD loading now.'});
} else {
    send({t:'info', msg: 'No direct CALL to AcquireSMD found in caller. May be indirect call.'});

    // Fallback: just hook AcquireSMD entry directly
    var acquireEntry = base.add(0x1eec130);
    send({t:'info', msg: 'Hooking AcquireSMD entry directly at ' + acquireEntry + '...'});

    Interceptor.attach(acquireEntry, {
        onEnter: function(args) {
            hookCount++;
            if (hookCount > 20) return;

            var esp = this.context.esp;
            var argPtrs = [];
            for (var i = 0; i < 6; i++) {
                try {
                    var a = esp.add(4 + i * 4).readPointer();
                    var s = null;
                    try { s = a.readAnsiString(128); } catch(e) {}
                    var s4 = null;
                    try { s4 = a.add(4).readAnsiString(128); } catch(e) {}
                    var s8 = null;
                    try { s8 = a.add(8).readAnsiString(128); } catch(e) {}
                    argPtrs.push({idx: i, val: a.toString(), str: s, str4: s4, str8: s8});
                } catch(e) {
                    argPtrs.push({idx: i, err: e.message});
                }
            }

            var stackStrings = [];
            for (var off = 0; off < 0x200; off += 4) {
                try {
                    var p = esp.add(off).readPointer();
                    var s = null;
                    try { s = p.readAnsiString(128); } catch(e) {}
                    if (s && s.length > 2 && (s.indexOf('.smd') >= 0 || s.indexOf('.bml') >= 0)) {
                        stackStrings.push({off: '0x' + off.toString(16), str: s, ptr: p.toString()});
                    }
                } catch(e) {}
            }

            send({t:'ACQUIRE', info: {n: hookCount, esp: esp.toString(),
                  args: argPtrs, stackStrings: stackStrings}});
        }
    });

    send({t:'READY', msg: 'AcquireSMD entry hook installed (fallback). Trigger SMD loading.'});
}
''';

def main():
    pid = find_pid()
    if not pid:
        print('[ERROR] FreeStyle.exe not running')
        return

    print(f'PID: {pid}')
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    dump_log = open(os.path.join(SCRIPT_DIR, 'dump_acquire_log.txt'), 'w', encoding='utf-8')

    def log(msg):
        print(msg)
        dump_log.write(msg + '\n')
        dump_log.flush()

    current_dump_name = ''

    def on_msg(msg, data):
        nonlocal current_dump_name
        if msg['type'] == 'error':
            log(f'[JS ERROR] {msg.get("description", msg)}')
            return

        p = msg.get('payload', {})
        t = p.get('t', '')

        if t == 'info':
            log(f'[*] {p["msg"]}')
        elif t == 'DUMP':
            current_dump_name = p['name']
            log(f'\n{"="*60}')
            log(f'DUMP: {p["name"]} at RVA={p["rva"]} abs={p["abs"]}')
            log(f'{"="*60}')
        elif t == 'HEX':
            log(p['line'])
        elif t == 'DUMP_ERR':
            log(f'[ERR] {p["name"]}: {p["err"]}')
        elif t == 'CALL_SITE':
            log(f'[CALL] Found CALL AcquireSMD at offset {p["offset"]} abs={p["abs"]}')
        elif t == 'STR_REF':
            log(f'[STR] @{p["offset"]}: "{p["str"]}"')
        elif t == 'ACQUIRE':
            info = p['info']
            log(f'\n[ACQUIRE #{info["n"]}] ESP={info["esp"]} EBP={info.get("ebp","?")}')
            if 'args' in info:
                for a in info['args']:
                    parts = [f'arg{a["idx"]}={a.get("val","?")}']
                    if a.get('str'): parts.append(f'str="{a["str"]}"')
                    if a.get('str4'): parts.append(f'+4="{a["str4"]}"')
                    if a.get('str8'): parts.append(f'+8="{a["str8"]}"')
                    if a.get('wide'): parts.append(f'wide="{a["wide"]}"')
                    if a.get('err'): parts.append(f'ERR={a["err"]}')
                    log(f'  {" | ".join(parts)}')
            if 'stackStrings' in info and info['stackStrings']:
                log(f'  Stack .smd/.bml refs:')
                for s in info['stackStrings']:
                    log(f'    ESP+{s["off"]}: "{s["str"]}" (ptr={s["ptr"]})')
            if 'ret' in info:
                log(f'  Ret addr: {info["ret"]}')
        elif t == 'READY':
            log(f'\n[READY] {p["msg"]}')
        else:
            log(f'[{t}] {p}')

    script.on('message', on_msg)
    script.load()
    log('Script loaded. Waiting for dumps and game events...\n')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nDetaching...')
    finally:
        session.detach()
        dump_log.close()
        print(f'Log saved.')

if __name__ == '__main__':
    main()

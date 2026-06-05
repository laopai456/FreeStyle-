"""
scan_verify.py — 验证 Memory.scan 是否正常
"""
import subprocess, frida

def get_pid():
    r = subprocess.run(['powershell', '-Command',
        "(Get-Process -Name FreeStyle* -ErrorAction SilentlyContinue | Select -First 1).Id"],
        capture_output=True, text=True)
    out = r.stdout.strip()
    return int(out) if (out and out.isdigit()) else None

pid = get_pid()
if not pid:
    print('FreeStyle.exe not running.')
    exit(1)

session = frida.attach(pid)
js = """
var m = Process.getModuleByName('FreeStyle.exe');
send({t: 'module', base: String(m.base), size: m.size});

// 1. Scan .text for pattern "50 75 73 68" (PUSH instr, should be everywhere)
var textHits = [];
try {
    Memory.scan(m.base, Math.min(m.size, 1024*1024), "55 8B EC", {
        onMatch: function(addr) { textHits.push(String(addr)); },
        onComplete: function() {}
    });
} catch(e) { send({t: 'err', step: 'text', msg: String(e)}); }
send({t: 'text_hits', count: textHits.length, first3: textHits.slice(0,3)});

// 2. Scan for "ChangeWindowMessageFilter" in kernel32
var k32 = Process.getModuleByName('kernel32.dll');
try {
    var exportNames = k32.enumerateExports().slice(0, 5).map(function(e) { return e.name; });
    send({t: 'k32_exports', names: exportNames});
} catch(e) { send({t: 'err', step: 'k32', msg: String(e)}); }

// 3. Try Enum all modules and check if enumerateRanges works
var ranges = Process.enumerateRanges({protection: 'rw-', coalesce: true});
send({t: 'rw_ranges', count: ranges.length, first: ranges[0] ? String(ranges[0].base) + ' +' + ranges[0].size : 'none'});

// 4. Direct read test: read 8 bytes at a known heap addr
// From earlier hook, we saw buf=0x6e8b51d0 (stack), let's try reading FreeStyle+0x1000
try {
    var test = m.base.add(0x1000).readByteArray(16);
    send({t: 'read_test', hex: hexdump(test, {offset: 0, length: 16, header: false})});
} catch(e) { send({t: 'err', step: 'read', msg: String(e)}); }

// 5. Try scanning a small known range for ASCII "MSVCR"
var msvcr = Process.getModuleByName('MSVCR100.dll');
var pat = '4d 53 56 43 52'; // "MSVCR"
var msvcrHits = 0;
try {
    Memory.scan(msvcr.base, Math.min(msvcr.size, 1024*1024), pat, {
        onMatch: function(addr) { msvcrHits++; },
        onComplete: function() {}
    });
} catch(e) { send({t: 'err', step: 'msvcr_scan', msg: String(e)}); }
send({t: 'msvcr_hits', count: msvcrHits});

send({t: 'done'});
"""
script = session.create_script(js)
script.on('message', lambda msg, _: print(msg.get('payload', msg)) if msg['type'] == 'send' else print(msg))
script.load()
session.detach()
"""
scan_string.py — 扫描 ANSI + UTF-16LE + 短码
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

print(f'PID={pid}')

session = frida.attach(pid)
js = r"""
var targets = [
    {name: 'ANSI', pat: '69 35 30 31 32 33 39 37 31 5f 6d 73'},
    {name: 'ANSI_short', pat: '35 30 31 32 33 39 37 31'},
    {name: 'UTF16LE', pat: '69 00 35 00 30 00 31 00 32 00 33 00 39 00 37 00 31 00 5f 00 6d 00 73 00'},
    {name: 'UTF16LE_short', pat: '35 00 30 00 31 00 32 00 33 00 39 00 37 00 31 00'},
];

var allMatches = [];

targets.forEach(function(t) {
    Process.enumerateRanges({protection: 'rw-', coalesce: true}).forEach(function(r) {
        if (r.size > 256 * 1024 * 1024) return;
        try {
            Memory.scan(r.base, r.size, t.pat, {
                onMatch: function(addr) {
                    var ctx = {};
                    ctx.tag = t.name;
                    ctx.addr = String(addr);
                    ctx.range = String(r.base) + ' +' + r.size;
                    try {
                        var m = Process.findModuleByAddress(addr);
                        ctx.module = m ? m.name : '?';
                    } catch(e) { ctx.module = '?'; }
                    allMatches.push(ctx);
                },
                onComplete: function() {}
            });
        } catch(e) {}
    });
});

// Also scan r-- ranges for ANSI (read-only data section)
targets.slice(0,2).forEach(function(t) {
    Process.enumerateRanges({protection: 'r--', coalesce: true}).forEach(function(r) {
        if (r.size > 256 * 1024 * 1024) return;
        try {
            Memory.scan(r.base, r.size, t.pat, {
                onMatch: function(addr) {
                    var ctx = {};
                    ctx.tag = t.name + '_ro';
                    ctx.addr = String(addr);
                    ctx.range = String(r.base) + ' +' + r.size;
                    try {
                        var m = Process.findModuleByAddress(addr);
                        ctx.module = m ? m.name : '?';
                    } catch(e) { ctx.module = '?'; }
                    allMatches.push(ctx);
                },
                onComplete: function() {}
            });
        } catch(e) {}
    });
});

var byModule = {};
allMatches.forEach(function(m) {
    var key = m.tag + '|' + m.module;
    if (!byModule[key]) byModule[key] = [];
    byModule[key].push(String(m.addr));
});

send({t:'result', total: allMatches.length, byModule: byModule});
send({t:'done'});
"""
script = session.create_script(js)
script.on('message', lambda msg, _: print(msg.get('payload', msg)) if msg['type'] == 'send' else print(msg))
script.load()
session.detach()
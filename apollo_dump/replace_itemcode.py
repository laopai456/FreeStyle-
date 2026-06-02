"""
replace_itemcode.py — Scan and replace item code in game memory

Replaces ALL occurrences of SRC item code with DST in writable memory.
Both must be same length.

Usage:
    1. Equip the SRC item in game (make it active/visible)
    2. Run: py replace_itemcode.py i50122721 i50125711
    3. Switch scene or re-equip to trigger re-render
"""
import frida
import sys
import subprocess
import time

LOG_FILE = r"D:\py\asmd_log.txt"


def find_pid():
    result = subprocess.run(
        ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
        capture_output=True, text=True, timeout=10
    )
    for line in result.stdout.strip().split('\n'):
        if 'FreeStyle.exe' in line:
            return int(line.split(',')[1].strip('"'))
    return 0


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "i50122721"
    dst = sys.argv[2] if len(sys.argv) > 2 else "i50125711"

    if len(src) != len(dst):
        log(f"ERROR: lengths differ! {len(src)} vs {len(dst)}")
        return 1

    pid = find_pid()
    if not pid:
        log("FreeStyle.exe not running!")
        return 1

    log(f"=== Replace Item Code ===")
    log(f"PID: {pid}")
    log(f"Replace: {src} -> {dst}")

    js = f"""
var SRC = '{src}';
var DST = '{dst}';
var SRC_LEN = SRC.length;

// Build hex pattern for Memory.scan
var pattern = '';
for (var i = 0; i < SRC_LEN; i++) {{
    pattern += ('0' + SRC.charCodeAt(i).toString(16)).slice(-2) + ' ';
}}

// Build replacement bytes
var dstBytes = [];
for (var i = 0; i < DST.length; i++) {{
    dstBytes.push(DST.charCodeAt(i));
}}

var ranges = Process.enumerateRanges('rw-');
send({{t: 'INFO', msg: 'Scanning ' + ranges.length + ' rw ranges for "' + SRC + '"'}});

var hits = [];

for (var ri = 0; ri < ranges.length; ri++) {{
    var range = ranges[ri];
    if (range.size > 0x400000) continue;
    try {{
        Memory.scan(range.base, range.size, pattern, {{
            onMatch: function(address, size) {{
                hits.push(address);
            }},
            onComplete: function() {{}},
            onError: function() {{}}
        }});
    }} catch(e) {{}}
}}

setTimeout(function() {{
    send({{t: 'RESULT', msg: 'Found ' + hits.length + ' occurrences of "' + SRC + '"'}});

    var replaced = 0;
    var failed = 0;

    for (var i = 0; i < hits.length; i++) {{
        var addr = hits[i];
        try {{
            // Read context before replacement
            var ctx = '';
            try {{
                var start = addr.sub(16);
                var buf = start.readByteArray(SRC_LEN + 48);
                var view = new Uint8Array(buf);
                for (var j = 0; j < view.length; j++) {{
                    var ch = view[j];
                    ctx += (ch >= 0x20 && ch < 0x7F) ? String.fromCharCode(ch) : '.';
                }}
            }} catch(e) {{}}

            // Replace
            addr.writeByteArray(dstBytes);

            // Verify
            var verify = '';
            try {{
                verify = addr.readUtf8String(SRC_LEN);
            }} catch(e) {{}}

            if (verify === DST) {{
                send({{t: 'REPLACED', idx: i+1, addr: addr.toString(), ctx: ctx}});
                replaced++;
            }} else {{
                send({{t: 'VERIFY_FAIL', idx: i+1, addr: addr.toString()}});
                failed++;
            }}
        }} catch(e) {{
            send({{t: 'WRITE_FAIL', idx: i+1, addr: addr.toString(), err: e.message}});
            failed++;
        }}
    }}

    send({{t: 'DONE', msg: 'Replaced ' + replaced + '/' + hits.length + ', failed ' + failed}});
}}, 6000);
"""

    log("Attaching...")
    session = frida.attach(pid)

    replaced_count = 0

    def on_message(msg, data):
        nonlocal replaced_count
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            if t == 'REPLACED':
                replaced_count += 1
                log(f"  #{p.get('idx')} @ {p.get('addr')}  ctx: {p.get('ctx','')}")
            elif t == 'DONE':
                log(f"RESULT: {p.get('msg')}")
            else:
                log(f"  {t}: {p.get('msg','')}")
        elif msg['type'] == 'error':
            log(f"  ERROR: {msg.get('description','')}")

    script = session.create_script(js)
    script.on('message', on_message)
    script.load()

    log("Scanning & replacing (~10s)...")
    time.sleep(12)

    session.detach()

    if replaced_count > 0:
        log(f"\n{replaced_count} locations replaced!")
        log("Now switch scene or re-equip to see if visual changes.")
    else:
        log("No replacements made. Make sure the item is equipped/active.")

    return 0


if __name__ == '__main__':
    sys.exit(main())

"""
hook_call_site.py — Hook at the CALL instruction to AcquireSMD

Instead of hooking AcquireSMD itself (which crashes), we hook at the
call site RVA 0x1EEB9B2 where the CALL E8 instruction is.
At this point ECX and stack args are fully set up.

Usage: py hook_call_site.py [src_item] [dst_item]
"""
import frida
import sys
import os
import subprocess
import time

LOG_FILE = r"D:\py\asmd_log.txt"
CALL_SITE_RVA = 0x1EEB9B2
ACQUIRE_SMD_RVA = 0x01EED020

DEFAULT_SRC = "i50123971"
DEFAULT_DST = "i50123972"


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
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DST

    if len(src) != len(dst):
        log(f"ERROR: lengths differ ({len(src)} vs {len(dst)})")
        return 1

    pid = find_pid()
    if not pid:
        log("FreeStyle.exe not running!")
        return 1

    log(f"=== Call Site Hook === PID:{pid}")
    log(f"Hooking CALL at RVA 0x{CALL_SITE_RVA:X}, target AcquireSMD 0x{ACQUIRE_SMD_RVA:X}")
    log(f"Source: {src} -> Target: {dst}")

    js = f"""
var SRC = '{src}';
var DST = '{dst}';
var CALL_SITE = Process.getModuleByName('FreeStyle.exe').base.add(0x{CALL_SITE_RVA:X});
var ACQ_SMD = Process.getModuleByName('FreeStyle.exe').base.add(0x{ACQUIRE_SMD_RVA:X});

// Verify call site
var siteBytes = CALL_SITE.readByteArray(8);
var siteHex = Array.from(new Uint8Array(siteBytes)).map(function(b) {{
    return ('0' + b.toString(16)).slice(-2);
}}).join(' ');
send({{t: 'INFO', msg: 'Call site @ 0x' + CALL_SITE + ': ' + siteHex}});

var callCount = 0;

Interceptor.attach(CALL_SITE, {{
    onEnter: function(args) {{
        callCount++;
        var count = callCount;

        // At this point, the next instruction IS the CALL to AcquireSMD.
        // All parameters are set:
        //   ECX = this pointer (from mov ecx, [global])
        //   Stack = function args (pushed before this point)
        //   ESP points to return address of OUR call site

        var esp = this.context.esp;
        var ecx = this.context.ecx;

        send({{t: 'CALL', n: count, esp: esp.toString(), ecx: ecx.toString()}});

        // First 5 calls: dump everything
        if (count > 5) return;

        // 1. Read ECX as pointer - try to find SString in the object
        try {{
            var ecxBytes = ecx.readByteArray(64);
            var ecxHex = Array.from(new Uint8Array(ecxBytes)).map(function(b) {{
                return ('0' + b.toString(16)).slice(-2);
            }}).join(' ');
            send({{t: 'ECX', n: count, hex: ecxHex}});

            // Try reading ECX as SString directly (SSO inline)
            var ecxStr = '';
            try {{ ecxStr = ecx.readUtf8String(64); }} catch(e) {{}}
            if (ecxStr && ecxStr.length > 2) {{
                send({{t: 'ECX_STR', n: count, str: ecxStr}});
            }}

            // ECX might point to an object whose first field is a vtable ptr
            // SString might be at offset +4, +8, etc.
            for (var off = 4; off <= 48; off += 4) {{
                try {{
                    var field = ecx.add(off).readUtf8String(64);
                    if (field && field.length > 3 && field.indexOf('smd') >= 0) {{
                        send({{t: 'ECX_FIELD', n: count, offset: '+0x' + off.toString(16), str: field}});
                    }}
                }} catch(e) {{}}
            }}
        }} catch(e) {{
            send({{t: 'ECX_ERR', msg: e.message}});
        }}

        // 2. Read stack args - ESP points to our return addr, args are above
        // But actually ESP here = return addr for the call site function
        // The CALL instruction hasn't executed yet, so:
        //   [ESP] = return address of call site's caller
        //   [ESP+4], [ESP+8]... = args to the function containing the call site
        // Wait - we need the args that will be passed to AcquireSMD.
        // Those are pushed between the call site function's frame and the CALL.
        // Since it's a thiscall: ECX = this, stack args are what was pushed.

        // Scan stack: ESP+0 to ESP+0x80
        try {{
            var stackData = esp.readByteArray(0x200);
            var view = new Uint8Array(stackData);

            // Find ASCII runs >= 6 chars
            var runStart = -1;
            for (var pos = 0; pos < 0x200; pos++) {{
                var ch = view[pos];
                if (ch >= 0x20 && ch < 0x7F) {{
                    if (runStart < 0) runStart = pos;
                }} else {{
                    if (runStart >= 0 && (pos - runStart) >= 6) {{
                        try {{
                            var s = esp.add(runStart).readUtf8String(pos - runStart);
                            if (s && s.length >= 6) {{
                                send({{t: 'STACK_STR', n: count, offset: '+0x' + runStart.toString(16),
                                      str: s}});
                            }}
                        }} catch(e) {{}}
                    }}
                    runStart = -1;
                }}
            }}

            // Also look for pointers on stack that might point to SStrings
            for (var off = 0; off < 0x100; off += 4) {{
                try {{
                    var ptrVal = esp.add(off).readPointer();
                    var ptrNum = parseInt(ptrVal.toString());
                    if (ptrNum > 0x10000 && ptrNum < 0x7FFFFFFF) {{
                        var ps = '';
                        try {{ ps = ptrVal.readUtf8String(64); }} catch(e) {{}}
                        if (ps && ps.length > 3 && (ps.indexOf('smd') >= 0 || ps.indexOf('i501') >= 0 || ps.indexOf('res') >= 0)) {{
                            send({{t: 'STACK_PTR', n: count, offset: '+0x' + off.toString(16),
                                  ptr: ptrVal.toString(), str: ps}});
                        }}
                    }}
                }} catch(e) {{}}
            }}
        }} catch(e) {{
            send({{t: 'STACK_ERR', msg: e.message}});
        }}
    }}
}});

send({{t: 'HOOKED', msg: 'Call site hook active at 0x' + CALL_SITE}});
"""

    log("Attaching...")
    session = frida.attach(pid)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            m = p.get('msg', '')

            if t == 'CALL':
                log(f"CALL #{p.get('n','')} esp={p.get('esp','')} ecx={p.get('ecx','')}")
            elif t == 'ECX':
                log(f"  ECX hex: {p.get('hex','')}")
            elif t == 'ECX_STR':
                log(f"  ECX as string: \"{p.get('str','')}\"")
            elif t == 'ECX_FIELD':
                log(f"  ECX{p.get('offset','')} = \"{p.get('str','')}\"")
            elif t == 'STACK_STR':
                log(f"  STACK {p.get('offset','')} = \"{p.get('str','')}\"")
            elif t == 'STACK_PTR':
                log(f"  STACK PTR {p.get('offset','')} -> {p.get('ptr','')} = \"{p.get('str','')}\"")
            elif t == 'HOOKED':
                log(f"HOOK ACTIVE: {m}")
            else:
                log(f"  {t}: {m}")
        elif msg['type'] == 'error':
            log(f"FRIDA ERROR: {msg.get('description','')}")

    script = session.create_script(js)
    script.on('message', on_message)
    script.load()

    log("Hook active. Go to shop/equip. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    log("Detaching...")
    session.detach()
    return 0


if __name__ == '__main__':
    sys.exit(main())

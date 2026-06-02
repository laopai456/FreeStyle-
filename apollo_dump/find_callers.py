"""
find_callers.py — Find CALL instructions that target 0x01EED020

Scans .text section for E8/E9 rel32 calls/jumps to the AcquireSMD function.
These are the callers we need to hook instead of the function itself.

Read-only, no hooks, safe.
"""
import frida
import sys
import subprocess
import time

LOG_FILE = r"D:\py\asmd_log.txt"
TARGET_RVA = 0x01EED020


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


JS_CODE = r"""
var base = Process.getModuleByName('FreeStyle.exe').base;
var target = base.add(0x01EED020);
var targetVA = target.toInt32();

// Scan .text section (from base to base+moduleSize)
var modSize = Process.getModuleByName('FreeStyle.exe').size;
// Limit scan to reasonable range (first 32MB should cover .text)
var scanSize = Math.min(modSize, 0x2000000);

send({t: 'INFO', msg: 'Scanning ' + scanSize + ' bytes for calls to 0x' + target.toString()});

var buf = base.readByteArray(scanSize);
var view = new Uint8Array(buf);

var callers = [];

for (var i = 0; i < scanSize - 5; i++) {
    // E8 xx xx xx xx = CALL rel32
    if (view[i] === 0xE8) {
        var rel32 = view[i+1] | (view[i+2] << 8) | (view[i+3] << 16) | (view[i+4] << 24);
        // Sign extend
        if (rel32 & 0x80000000) rel32 = rel32 - 0x100000000;
        var dest = base.add(i).add(5).add(rel32).toInt32();
        if (dest === targetVA) {
            callers.push({rva: i, type: 'CALL', addr: base.add(i).toString()});
        }
    }
    // E9 xx xx xx xx = JMP rel32 (tail call)
    if (view[i] === 0xE9) {
        var rel32 = view[i+1] | (view[i+2] << 8) | (view[i+3] << 16) | (view[i+4] << 24);
        if (rel32 & 0x80000000) rel32 = rel32 - 0x100000000;
        var dest = base.add(i).add(5).add(rel32).toInt32();
        if (dest === targetVA) {
            callers.push({rva: i, type: 'JMP', addr: base.add(i).toString()});
        }
    }
}

send({t: 'RESULT', msg: 'Found ' + callers.length + ' callers'});

for (var i = 0; i < callers.length; i++) {
    var c = callers[i];
    // Read surrounding bytes for context
    var ctxAddr = base.add(c.rva - 8);
    var ctxBytes = '';
    try {
        var cb = ctxAddr.readByteArray(24);
        var cv = new Uint8Array(cb);
        for (var j = 0; j < 24; j++) ctxBytes += ('0' + cv[j].toString(16)).slice(-2) + ' ';
    } catch(e) { ctxBytes = 'unreadable'; }

    send({t: 'CALLER', idx: i+1, rva: '0x' + c.rva.toString(16),
          type: c.type, addr: c.addr, bytes: ctxBytes});
}

// Also check: is there indirect call via register? (FF D0 = call eax, etc)
// This is harder to find statically, but let's also scan for push instructions
// that reference strings containing "smd" near the call site
if (callers.length === 0) {
    send({t: 'WARN', msg: 'No direct CALL/JMP found! Function may be called via pointer/vtable.'});
    send({t: 'INFO', msg: 'Will search for function pointer references...'});
}
"""


def main():
    pid = find_pid()
    if not pid:
        print("FreeStyle.exe not running!")
        return 1

    log(f"PID: {pid}, finding callers of 0x01EED020...")

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            if t == 'CALLER':
                log(f"  #{p.get('idx')} {p.get('type')} at RVA {p.get('rva')} ({p.get('addr')})")
                log(f"    bytes: {p.get('bytes')}")
            else:
                log(f"  {t}: {p.get('msg','')}")
        elif msg['type'] == 'error':
            log(f"  ERROR: {msg.get('description','')}")

    script.on('message', on_message)
    script.load()

    time.sleep(3)
    session.detach()
    log("Done.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

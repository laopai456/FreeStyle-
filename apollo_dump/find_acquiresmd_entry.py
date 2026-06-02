"""
find_acquiresmd_entry.py — Scan memory to find AcquireSMD's real function entry

0x01EEC130 takes integer args — it's an inner function, not AcquireSMD.
0x01EED020 has "AcquireSMD"/"SSKF" string refs — the real logic is here.
This script scans backwards from 0x01EED020 to find the enclosing function's prologue.

No hooks — safe, read-only.
"""
import frida
import sys
import os
import subprocess
import time

LOG_FILE = r"D:\py\asmd_log.txt"
ACQUIRE_RVA = 0x01EED020  # Known string-ref location
SCAN_RANGE = 0x2000       # Scan 8KB backwards


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

// Read 8KB of memory ending at target
var scanStart = target.sub(0x2000);
var buf = scanStart.readByteArray(0x2000);
var view = new Uint8Array(buf);

// Also read 256 bytes AT target for context
var targetBuf = target.readByteArray(256);
var targetView = new Uint8Array(targetBuf);

send({t: 'INFO', msg: 'Base: 0x' + base + ', Target: 0x' + target});

// Show bytes at target
var hex = '';
for (var i = 0; i < 64; i++) hex += ('0' + targetView[i].toString(16)).slice(-2) + ' ';
send({t: 'DUMP', msg: 'Bytes at 0x01EED020: ' + hex});

// Scan backwards for CC padding (int3) followed by prologue patterns
// MSVC prologues: 55 (push ebp), 83 EC xx (sub esp,xx), 8B FF (mov edi,edi)
// CC padding means we're at a function boundary

var results = [];

for (var i = 0x2000 - 4; i >= 2; i--) {
    var b0 = view[i];
    var b1 = view[i + 1];
    var b2 = view[i + 2];

    // Pattern 1: CC CC ... then 55 8B EC (push ebp; mov ebp, esp)
    if (b0 === 0xCC && b1 === 0x55 && b2 === 0x8B) {
        var addr = scanStart.add(i + 1);
        var rva = addr.sub(base).toInt32();
        // Show some preceding CCs
        var ccCount = 0;
        for (var j = i; j >= 0 && view[j] === 0xCC; j--) ccCount++;
        results.push({rva: rva, addr: addr.toString(), type: 'push ebp; mov ebp,esp', ccPad: ccCount});
    }

    // Pattern 2: CC CC ... then 83 EC xx (sub esp, xx)
    if (b0 === 0xCC && b1 === 0x83 && b2 === 0xEC) {
        var addr = scanStart.add(i + 1);
        var rva = addr.sub(base).toInt32();
        var subVal = view[i + 3];
        results.push({rva: rva, addr: addr.toString(), type: 'sub esp,0x' + subVal.toString(16)});
    }

    // Pattern 3: CC CC ... then 8B FF (mov edi, edi) — hotspot pad
    if (b0 === 0xCC && b1 === 0x8B && b2 === 0xFF) {
        var addr = scanStart.add(i + 1);
        var rva = addr.sub(base).toInt32();
        results.push({rva: rva, addr: addr.toString(), type: 'mov edi,edi (hotpad)'});
    }

    // Pattern 4: CC CC ... then 56 (push esi) or 57 (push edi) or 53 (push ebx)
    if (b0 === 0xCC && (b1 === 0x56 || b1 === 0x57 || b1 === 0x53 || b1 === 0x51)) {
        var regName = {0x56:'esi', 0x57:'edi', 0x53:'ebx', 0x51:'ecx'}[b1];
        var addr = scanStart.add(i + 1);
        var rva = addr.sub(base).toInt32();
        results.push({rva: rva, addr: addr.toString(), type: 'push ' + regName});
    }
}

// Sort by RVA (closest to target first = highest RVA)
results.sort(function(a, b) { return b.rva - a.rva; });

send({t: 'RESULT', msg: 'Found ' + results.length + ' prologue candidates:'});
for (var i = 0; i < Math.min(results.length, 20); i++) {
    var r = results[i];
    var offset = 0x01EED020 - r.rva;
    send({t: 'ENTRY', rva: '0x' + r.rva.toString(16), offset: '+' + offset,
          addr: r.addr, type: r.type, ccPad: r.ccPad || 0});
}

// Also dump the first 16 bytes of the top 5 candidates
for (var i = 0; i < Math.min(results.length, 5); i++) {
    var r = results[i];
    var entryAddr = base.add(r.rva);
    try {
        var eb = entryAddr.readByteArray(16);
        var ehex = '';
        var eview = new Uint8Array(eb);
        for (var j = 0; j < 16; j++) ehex += ('0' + eview[j].toString(16)).slice(-2) + ' ';
        send({t: 'PROLOGUE', rva: '0x' + r.rva.toString(16), bytes: ehex});
    } catch(e) {}
}
"""


def main():
    pid = find_pid()
    if not pid:
        print("FreeStyle.exe not running!")
        return 1

    log(f"PID: {pid}, scanning for AcquireSMD entry near 0x01EED020...")

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            m = p.get('msg', '')
            if t == 'ENTRY':
                log(f"  CANDIDATE: RVA={p.get('rva')} offset={p.get('offset')} type={p.get('type')} ccPad={p.get('ccPad')}")
            elif t == 'PROLOGUE':
                log(f"  PROLOGUE {p.get('rva')}: {p.get('bytes')}")
            else:
                log(f"  {t}: {m}")
        elif msg['type'] == 'error':
            log(f"  ERROR: {msg.get('description', '')}")

    script.on('message', on_message)
    script.load()

    time.sleep(2)
    session.detach()
    log("Done — no hooks, game should be fine.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

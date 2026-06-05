"""
hook_callsite_manual.py — Manual inline hook before CALL to AcquireSMD

Frida Interceptor can't hook at CALL E8 instructions (rel32 relocation issue).
Instead, we manually patch the instruction BEFORE the CALL:
  0x1EEB9AC: 8b 0d 68 53 a9 02  = mov ecx, [0x02A95368]  (6 bytes)
  0x1EEB9B2: e8 69 16 00 00     = call AcquireSMD         (5 bytes)

We replace the 6-byte MOV ECX with a JMP to our stub.
The stub saves regs, calls a Frida NativeCallback for logging,
restores regs, executes the original MOV ECX, then JMPs back.

Usage: py hook_callsite_manual.py
"""
import frida
import sys
import subprocess
import time

LOG_FILE = r"D:\py\asmd_log.txt"
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

    pid = find_pid()
    if not pid:
        log("FreeStyle.exe not running!")
        return 1

    log(f"=== Manual Inline Hook === PID:{pid}")
    log(f"Source: {src} -> Target: {dst}")

    js = f"""
var SRC = '{src}';
var DST = '{dst}';
var base = Process.getModuleByName('FreeStyle.exe').base;

// The patch point: 6 bytes at 0x1EEB9AC (mov ecx, [0x02A95368])
var PATCH_RVA = 0x1EEB9AC;
var CALL_RVA = 0x1EEB9B2;
var patchAddr = base.add(PATCH_RVA);
var callAddr = base.add(CALL_RVA);
var acqSMD = base.add(0x01EED020);

// Read original bytes at patch site
var origBytes = patchAddr.readByteArray(6);
var origHex = Array.from(new Uint8Array(origBytes)).map(function(b) {{
    return ('0' + b.toString(16)).slice(-2);
}}).join(' ');
send({{t: 'INFO', msg: 'Patch site @ 0x' + patchAddr + ': ' + origHex}});

// Read bytes at CALL site for verification
var callBytes = callAddr.readByteArray(5);
var callHex = Array.from(new Uint8Array(callBytes)).map(function(b) {{
    return ('0' + b.toString(16)).slice(-2);
}}).join(' ');
send({{t: 'INFO', msg: 'Call site  @ 0x' + callAddr + ': ' + callHex}});

var callCount = 0;

// NativeCallback: minimal — just log, no memory scanning
var onCallSite = new NativeCallback(function(ecxVal, espVal) {{
    callCount++;
    send({{t: 'CALL', n: callCount, ecx: '0x' + ecxVal.toString(16), esp: '0x' + espVal.toString(16)}});
}}, 'void', ['int', 'int']);

// Allocate shellcode page
var sc = Memory.alloc(Process.pageSize);

// Shellcode:
//   pushad              ; save all regs
//   pushfd              ; save flags
//   push esp            ; pass ESP
//   push ecx            ; pass ECX
//   call onCallSite     ; call our NativeCallback
//   add esp, 8          ; clean 2 args
//   popfd               ; restore flags
//   popad               ; restore regs
//   <original 6 bytes>  ; mov ecx, [0x02A95368]
//   jmp callAddr+5      ; jump to instruction after the CALL

var scBytes = [];
// pushad
scBytes.push(0x60);
// pushfd
scBytes.push(0x9C);
// push esp
scBytes.push(0x54);
// push ecx
scBytes.push(0x51);
// call onCallSite (using mov + call abs)
// mov eax, onCallSite
scBytes.push(0xB8);
var cbAddr = onCallSite;
// Write address as 4 bytes LE
var cbVal = parseInt(cbAddr.toString());
scBytes.push(cbVal & 0xFF);
scBytes.push((cbVal >> 8) & 0xFF);
scBytes.push((cbVal >> 16) & 0xFF);
scBytes.push((cbVal >> 24) & 0xFF);
// call eax
scBytes.push(0xFF);
scBytes.push(0xD0);
// add esp, 8
scBytes.push(0x83);
scBytes.push(0xC4);
scBytes.push(0x08);
// popfd
scBytes.push(0x9D);
// popad
scBytes.push(0x61);
// Original bytes: 8b 0d 68 53 a9 02
var orig = new Uint8Array(origBytes);
for (var i = 0; i < orig.length; i++) scBytes.push(orig[i]);
// jmp to callAddr+5 (instruction after the CALL)
// We need to compute: callAddr+5 - (scAddr + scBytes.length + 5)
// But scAddr isn't known yet... use indirect jmp instead
// push callAddr+5; ret
var retAddr = callAddr.add(5);
var retVal = parseInt(retAddr.toString());
scBytes.push(0x68);  // push imm32
scBytes.push(retVal & 0xFF);
scBytes.push((retVal >> 8) & 0xFF);
scBytes.push((retVal >> 16) & 0xFF);
scBytes.push((retVal >> 24) & 0xFF);
scBytes.push(0xC3);  // ret

// Write shellcode
sc.writeByteArray(scBytes);

send({{t: 'INFO', msg: 'Shellcode at 0x' + sc + ' (' + scBytes.length + ' bytes)'}});

// Now patch the call site: replace 6 bytes with JMP to shellcode
// E9 rel32 where rel32 = sc - (patchAddr + 5)
Memory.protect(patchAddr, 6, 'rwx');
var jmpOffset = sc.sub(patchAddr.add(5));
var jmpBytes = new Uint8Array([0xE9,
    jmpOffset.toInt32() & 0xFF,
    (jmpOffset.toInt32() >> 8) & 0xFF,
    (jmpOffset.toInt32() >> 16) & 0xFF,
    (jmpOffset.toInt32() >> 24) & 0xFF,
    0x90  // NOP for the 6th byte
]);
patchAddr.writeByteArray(jmpBytes);

// Verify patch
var patchedBytes = patchAddr.readByteArray(6);
var patchedHex = Array.from(new Uint8Array(patchedBytes)).map(function(b) {{
    return ('0' + b.toString(16)).slice(-2);
}}).join(' ');
send({{t: 'INFO', msg: 'Patched: ' + patchedHex}});

send({{t: 'HOOKED', msg: 'Manual inline hook active'}});
"""

    log("Attaching...")
    session = frida.attach(pid)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            if t == 'CALL':
                log(f"CALL #{p.get('n','')} ecx={p.get('ecx','')} esp={p.get('esp','')}")
            elif t == 'ECX':
                log(f"  ECX hex: {p.get('hex','')}")
            elif t == 'PTR':
                log(f"  PTR {p.get('offset','')} -> {p.get('ptr','')} = \"{p.get('str','')}\"")
            elif t == 'STR':
                log(f"  STR {p.get('offset','')} = \"{p.get('str','')}\"")
            elif t == 'HOOKED':
                log(f"HOOK: {p.get('msg','')}")
            else:
                log(f"  {t}: {p.get('msg','')}")
        elif msg['type'] == 'error':
            log(f"ERROR: {msg.get('description','')}")

    script = session.create_script(js)
    script.on('message', on_message)
    script.load()

    log("Manual hook active. Trigger shop/equip. Ctrl+C to stop.\n")

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

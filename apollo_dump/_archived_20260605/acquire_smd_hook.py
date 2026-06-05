"""
acquire_smd_hook.py — Hook AcquireSMD to replace SMD file paths via Frida

Usage:
    py acquire_smd_hook.py [src_item] [dst_item]
    py acquire_smd_hook.py i50123971 i50123972

Prerequisites:
    1. sc stop ApolloProtect (管理员 PowerShell)
    2. 启动游戏, 等到大厅界面
    3. py x32dbg_enabler.py  (另一个终端, VirtualQuery欺骗+CRC patch)
    4. py acquire_smd_hook.py  (本脚本)

Item codes MUST be the same length (SString SSO buffer constraint).
"""
import frida
import sys
import os
import time
import subprocess
import ctypes
import ctypes.wintypes as wintypes
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(SCRIPT_DIR, "acquire_smd_hook.js")
LOG_FILE = r"D:\py\asmd_log.txt"

DEFAULT_SRC = "i50123971"
DEFAULT_DST = "i50123972"

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)

# Key ntdll functions Frida needs to parse — must have original mov eax,N; sysenter stubs
SYSCALL_STUBS = [
    "NtSetInformationThread",
    "NtQueryInformationProcess",
    "NtQueryVirtualMemory",
    "NtProtectVirtualMemory",
    "NtReadVirtualMemory",
    "NtWriteVirtualMemory",
    "NtAllocateVirtualMemory",
    "NtFreeVirtualMemory",
    "NtQuerySystemInformation",
    "NtClose",
    "NtCreateThreadEx",
    "NtResumeThread",
    "NtSuspendThread",
    "NtOpenProcess",
    "NtOpenThread",
    "NtGetContextThread",
    "NtSetContextThread",
    "NtTerminateProcess",
    "NtMapViewOfSection",
    "NtUnmapViewOfSection",
]


def restore_syscall_stubs(pid):
    """Restore ntdll syscall stubs in target process so Frida can parse them.

    Apollo.sys hooks ntdll by replacing `mov eax, N` with a JMP.
    Frida's GetSysCallIndex32 expects the original pattern and crashes if it finds JMPs.
    We copy clean stubs from our own process's ntdll into the target's ntdll.
    """
    PAGE_EXECUTE_READWRITE = 0x40
    PROCESS_ALL_ACCESS = 0x1F0FFF

    # Open target process
    handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle:
        log(f"  Cannot open process for stub restore: {ctypes.get_last_error()}")
        return False

    # Get ntdll base in our process (same in all processes due to ASLR sharing)
    ntdll_base = kernel32.GetModuleHandleW('ntdll.dll')
    if not ntdll_base:
        log("  Cannot find ntdll.dll base")
        kernel32.CloseHandle(handle)
        return False

    # Get our own ntdll module info to find function addresses
    our_ntdll = ctypes.WinDLL('ntdll')

    restored = 0
    skipped = 0

    for name in SYSCALL_STUBS:
        try:
            func_ptr = getattr(our_ntdll, name)
            func_addr = ctypes.cast(func_ptr, ctypes.c_void_p).value
        except AttributeError:
            continue

        if not func_addr:
            continue

        # Read the original stub bytes from OUR process (not hooked by Apollo in Python)
        # The stub is typically: mov eax, N (5 bytes: B8 xx xx xx xx) + sysenter/int 2e
        STUB_SIZE = 8  # Read 8 bytes: mov eax,N (5) + sysenter pattern (2-3)

        # Read from our process via ctypes memmove
        our_stub = ctypes.create_string_buffer(STUB_SIZE)
        ctypes.memmove(our_stub, func_addr, STUB_SIZE)
        our_bytes = our_stub.raw

        # Read target process stub
        target_buf = ctypes.create_string_buffer(STUB_SIZE)
        n_read = ctypes.c_size_t()
        ok = kernel32.ReadProcessMemory(
            handle, ctypes.c_void_p(func_addr),
            target_buf, STUB_SIZE, ctypes.byref(n_read)
        )
        if not ok or n_read.value != STUB_SIZE:
            skipped += 1
            continue

        target_bytes = target_buf.raw

        # Check if already original (starts with B8 = mov eax)
        if our_bytes[0] == 0xB8 and target_bytes[0] == 0xB8 and our_bytes == target_bytes:
            skipped += 1
            continue

        # Check if our stub is clean (has mov eax pattern)
        if our_bytes[0] != 0xB8:
            # Our own ntdll is also hooked (shouldn't happen for Python process)
            skipped += 1
            continue

        # Write our clean stub to target process
        old_prot = wintypes.DWORD()
        kernel32.VirtualProtectEx(
            handle, ctypes.c_void_p(func_addr), STUB_SIZE,
            PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot)
        )

        n_written = ctypes.c_size_t()
        ok = kernel32.WriteProcessMemory(
            handle, ctypes.c_void_p(func_addr),
            our_stub, STUB_SIZE, ctypes.byref(n_written)
        )

        # Restore protection
        kernel32.VirtualProtectEx(
            handle, ctypes.c_void_p(func_addr), STUB_SIZE,
            old_prot.value, ctypes.byref(old_prot)
        )

        if ok:
            syscall_num = struct.unpack_from('<I', our_bytes, 1)[0]
            log(f"  Restored {name}: syscall 0x{syscall_num:03X}")
            restored += 1
        else:
            log(f"  FAILED to restore {name}")

    kernel32.CloseHandle(handle)
    log(f"  Restored {restored} stubs, skipped {skipped}")
    return restored > 0


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
        log(f"ERROR: source({len(src)}) != target({len(dst)}) length!")
        return 1

    pid = find_pid()
    if not pid:
        log("FreeStyle.exe not running!")
        return 1

    log(f"=== AcquireSMD Hook ===")
    log(f"PID: {pid}")
    log(f"Source: {src} -> Target: {dst}")

    # Load JS and replace placeholders
    with open(JS_FILE, 'r', encoding='utf-8') as f:
        js_code = f.read()
    js_code = js_code.replace('SRC_PLACEHOLDER', src)
    js_code = js_code.replace('DST_PLACEHOLDER', dst)

    log("Restoring ntdll syscall stubs...")
    restore_syscall_stubs(pid)

    log("Attaching...")
    session = frida.attach(pid)

    def on_message(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '?')
            m = p.get('msg', '')

            if t == 'CALL':
                log(f"CALL #{p.get('n','')} esp={p.get('esp','')} arg0={p.get('arg0','')} arg1={p.get('arg1','')}")
            elif t == 'FOUND':
                log(f"  FOUND #{p.get('n','')} at stack {p.get('stackAddr','')} offset={p.get('offset','')} ctx=\"{p.get('context','')}\"")
            elif t == 'ARG':
                log(f"  ARG[{p.get('idx','')}] @ {p.get('val','')} = \"{p.get('str','')}\"")
            elif t == 'REP':
                log(f"  REPLACED @ {p.get('addr','')}: {p.get('before', p.get('context',''))}")
            elif t == 'RET':
                log(f"  RET #{p.get('n','')} = {p.get('val','')} replaced={p.get('replaced')}")
            elif t == 'HOOKED':
                log(f"HOOK ACTIVE: {m}")
            else:
                log(f"  {t}: {m}")
        elif msg['type'] == 'error':
            log(f"FRIDA ERROR: {msg.get('description', '')}")
            log(f"  {msg.get('stack', '')}")

    script = session.create_script(js_code)
    script.on('message', on_message)
    script.load()

    log("")
    log("Hook active! Go to shop/equip to trigger AcquireSMD.")
    log(f"Log: {LOG_FILE}")
    log("Press Ctrl+C to stop.\n")

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

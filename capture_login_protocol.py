"""
capture_login_protocol.py — WS2_32.connect inline hook + TCP proxy
Phase 1: 透明重定向游戏流量 → 捕获登录协议包

用法:
  py capture_login_protocol.py

流程:
  1. 启动 TCP 代理 (127.0.0.1:23001 → 42.193.73.163:10005)
  2. CREATE_SUSPENDED 启动游戏 → ResumeThread → CRC绕过
  3. Hook WS2_32.connect: 游戏以为连 42.193.73.163:10005, 实际连 127.0.0.1:23001
  4. 代理双向转发 + 捕获所有包 → apollo_dump/login_packets.bin
  5. 用户手动登录一次后, 连接自然断开, 脚本自动恢复hook并退出
"""
import ctypes
import ctypes.wintypes as wintypes
import struct
import subprocess
import threading
import socket
import time
import os
import sys

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

CREATE_SUSPENDED = 0x00000004
PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
TH32CS_SNAPMODULE = 0x00000008

GAME_PATH = r"C:\Program Files (x86)\T2CN\街头篮球\FreeStyle.exe"
GAME_DIR = r"C:\Program Files (x86)\T2CN\街头篮球"
LOGIN_PARAM = "42.193.73.163:10005"
REAL_HOST = "42.193.73.163"
REAL_PORT = 10005
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 23001

CRC_RVA1 = 0x001A3C54
CRC_RVA2 = 0x001BE222
CRC_PATCH = b'\x33\xC0\xC3'

LOG_FILE = r"d:\py\反编译\FreeStyle\apollo_dump\login_capture_log.txt"
PKT_FILE = r"d:\py\反编译\FreeStyle\apollo_dump\login_packets.bin"


class SI(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
        ('lpReserved2', wintypes.LPBYTE),
        ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]


class PI(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD),
        ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', wintypes.LPVOID),
        ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE),
        ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260),
    ]


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def rd(hp, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok and n.value > 0 else None


def wr(hp, addr, data):
    n = ctypes.c_size_t()
    old = wintypes.DWORD()
    kernel32.VirtualProtectEx(hp, ctypes.c_void_p(addr), len(data),
                              PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    ok = kernel32.WriteProcessMemory(hp, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))
    kernel32.VirtualProtectEx(hp, ctypes.c_void_p(addr), len(data), old, ctypes.byref(old))
    return ok and n.value == len(data)


def virt_alloc(hp, size):
    addr = kernel32.VirtualAllocEx(hp, None, size, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    return addr or 0


def enum_modules(pid):
    mods = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    if snap == -1:
        return mods
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    if kernel32.Module32First(snap, ctypes.byref(me)):
        while True:
            mods.append({
                'name': me.szModule.decode('gbk', errors='replace'),
                'base': me.modBaseAddr, 'size': me.modBaseSize,
            })
            if not kernel32.Module32Next(snap, ctypes.byref(me)):
                break
    kernel32.CloseHandle(snap)
    return mods


def find_export(hp, base, name):
    try:
        dos = rd(hp, base, 0x40)
        e_lfanew = struct.unpack_from('<I', dos, 0x3C)[0]
        nt = rd(hp, base + e_lfanew, 0xF8)
        export_rva = struct.unpack_from('<I', nt, 0x78)[0]
        export = rd(hp, base + export_rva, 0x28)
        n_names = struct.unpack_from('<I', export, 0x18)[0]
        rva_funcs = struct.unpack_from('<I', export, 0x1C)[0]
        rva_names = struct.unpack_from('<I', export, 0x20)[0]
        rva_ords = struct.unpack_from('<I', export, 0x24)[0]
        for i in range(min(n_names, 2000)):
            n_data = rd(hp, base + rva_names + i * 4, 4)
            name_rva = struct.unpack_from('<I', n_data, 0)[0]
            fname = rd(hp, base + name_rva, 128).split(b'\x00')[0]
            if fname == name.encode():
                ord_val = struct.unpack_from('<H', rd(hp, base + rva_ords + i * 2, 2), 0)[0]
                func_rva = struct.unpack_from('<I', rd(hp, base + rva_funcs + ord_val * 4, 4), 0)[0]
                return base + func_rva
    except Exception:
        pass
    return 0


def build_trampoline(orig_bytes, connect_addr):
    """
    Build x86 shellcode trampoline that rewrites sockaddr on connect().

    Checks if destination is 42.193.73.163:10005 → rewrites to 127.0.0.1:23001.
    Non-matching connections pass through unchanged.

    Layout (0x3B = 59 bytes):
      00: pushad
      01: mov ebx, [esp+0x28]       ; sockaddr* name from stack
      08: movzx eax, word [ebx]     ; sin_family
      0B: cmp ax, 2                 ; AF_INET?
      0F: jne restore               ; no → skip
      11: cmp word [ebx+2], 0x1527  ; sin_port == htons(10005)?
      18: jne restore               ; no → skip
      1A: cmp dword [ebx+4], 0x2AC149A3  ; sin_addr == 42.193.73.163?
      21: jne restore               ; no → skip
      23: mov dword [ebx+4], 0x7F000001  ; sin_addr = 127.0.0.1
      2A: mov word [ebx+2], 0xD959       ; sin_port = htons(23001)
      30: popad (restore label)
      31: [5 bytes original]        ; patched at runtime
      36: jmp REL32 → connect+5     ; patched at runtime
    """
    sc = bytearray()
    sc += b'\x60'
    sc += b'\x8B\x9C\x24\x28\x00\x00\x00'
    sc += b'\x0F\xB7\x03'
    sc += b'\x66\x83\xF8\x02'
    sc += b'\x75\x1F'
    sc += b'\x66\x81\x7B\x02\x27\x15'
    sc += b'\x75\x16'
    sc += b'\x81\x7B\x04\xA3\x49\xC1\x2A'
    sc += b'\x75\x0D'
    sc += b'\xC7\x43\x04\x01\x00\x00\x7F'
    sc += b'\x66\xC7\x43\x02\x59\xD9'
    sc += b'\x61'

    assert len(sc) == 0x31, f"Shellcode header size mismatch: {len(sc):#x} != 0x31"

    sc += orig_bytes

    assert len(sc) == 0x36, f"Shellcode + orig size mismatch: {len(sc):#x} != 0x36"

    rel = connect_addr + 5 - (0 + 0x36 + 5)
    sc += b'\xE9' + struct.pack('<i', rel)

    assert len(sc) == 0x3B, f"Final shellcode size mismatch: {len(sc):#x} != 0x3B"
    return bytes(sc)


def install_connect_hook(hp, pid):
    modules = enum_modules(pid)
    ws2_base = 0
    for m in modules:
        if m['name'].lower() == 'ws2_32.dll':
            ws2_base = m['base']
            break
    if not ws2_base:
        log("ERROR: WS2_32.dll not found")
        return 0, None

    connect_addr = find_export(hp, ws2_base, 'connect')
    if not connect_addr:
        log("ERROR: connect not found in WS2_32 exports")
        return 0, None

    log(f"WS2_32 @ 0x{ws2_base:08X}, connect @ 0x{connect_addr:08X}")

    orig_bytes = rd(hp, connect_addr, 5)
    if not orig_bytes or len(orig_bytes) < 5:
        log("ERROR: Cannot read connect entry point")
        return 0, None
    log(f"connect original bytes: {orig_bytes.hex()}")

    trampoline_addr = virt_alloc(hp, 128)
    if not trampoline_addr:
        log("ERROR: VirtualAllocEx failed")
        return 0, None
    log(f"Trampoline @ 0x{trampoline_addr:08X}")

    trampoline = build_trampoline(orig_bytes, connect_addr)
    if not wr(hp, trampoline_addr, trampoline):
        log("ERROR: WriteProcessMemory trampoline failed")
        return 0, None

    jmp_offset = trampoline_addr - connect_addr - 5
    jmp_code = b'\xE9' + struct.pack('<i', jmp_offset)
    if not wr(hp, connect_addr, jmp_code):
        log("ERROR: WriteProcessMemory JMP hook failed")
        return 0, None

    verify = rd(hp, connect_addr, 5)
    log(f"connect hook installed: {verify.hex() if verify else 'FAIL'}")

    return trampoline_addr, orig_bytes


def restore_connect_hook(hp, connect_addr, orig_bytes):
    log("Restoring connect hook...")
    if wr(hp, connect_addr, orig_bytes):
        verify = rd(hp, connect_addr, 5)
        log(f"connect restored: {verify.hex() if verify else 'FAIL'}")
    else:
        log("WARNING: Failed to restore connect")


def launch_game():
    log("--- Killing old FreeStyle.exe ---")
    subprocess.run(['taskkill', '/F', '/IM', 'FreeStyle.exe'], capture_output=True)
    time.sleep(1)

    log(f"--- Launching: {GAME_PATH} {LOGIN_PARAM} ---")
    si = SI()
    si.cb = ctypes.sizeof(SI)
    pi = PI()

    ok = kernel32.CreateProcessW(
        GAME_PATH, f'"{GAME_PATH}" {LOGIN_PARAM}',
        None, None, False, CREATE_SUSPENDED,
        None, GAME_DIR, ctypes.byref(si), ctypes.byref(pi),
    )
    if not ok:
        err = ctypes.get_last_error()
        log(f"CreateProcess failed: {ctypes.WinError(err)}")
        return None, 0, None

    hp, ht, pid = pi.hProcess, pi.hThread, pi.dwProcessId
    log(f"Game PID={pid}, handle=0x{hp:X}")

    time.sleep(0.5)
    kernel32.ResumeThread(ht)
    kernel32.CloseHandle(ht)
    log("Main thread resumed")

    apollo_base = 0
    for attempt in range(15):
        time.sleep(1)
        for m in enum_modules(pid):
            if 'apolloct' in m['name'].lower():
                apollo_base = m['base']
                break
        if apollo_base:
            break
        if attempt % 3 == 2:
            log(f"  Waiting for ApolloCT.dll... ({attempt + 1}/15)")

    if apollo_base:
        c1 = apollo_base + CRC_RVA1
        c2 = apollo_base + CRC_RVA2
        log(f"ApolloCT @ 0x{apollo_base:08X}")

        ok1 = wr(hp, c1, CRC_PATCH)
        ok2 = wr(hp, c2, CRC_PATCH)
        v1 = rd(hp, c1, 3)
        v2 = rd(hp, c2, 3)
        if v1 == CRC_PATCH and v2 == CRC_PATCH:
            log("CRC patch OK ✓")
        else:
            log(f"CRC patch verify: CRC1={v1.hex() if v1 else 'FAIL'} CRC2={v2.hex() if v2 else 'FAIL'}")
    else:
        log("WARNING: ApolloCT.dll not found, proceeding without CRC patch")

    return hp, pid, pi


def run_proxy():
    log(f"Proxy starting: {PROXY_HOST}:{PROXY_PORT} → {REAL_HOST}:{REAL_PORT}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((PROXY_HOST, PROXY_PORT))
    server.listen(1)
    server.settimeout(120.0)

    log("Proxy listening ✓")
    log("")
    log("!" * 60)
    log("!!  GAME WILL CONNECT VIA PROXY AUTOMATICALLY     !!")
    log("!!  1. Wait for login screen                       !!")
    log("!!  2. Enter username (000101) + password          !!")
    log("!!  3. Click LOGIN                                 !!")
    log("!!  Script captures all packets automatically      !!")
    log("!" * 60)

    with open(PKT_FILE, 'wb') as pkt_f:
        try:
            client, addr = server.accept()
            log(f"\nGame connected from {addr}")
        except socket.timeout:
            log("Timeout: game did not connect within 120s")
            server.close()
            return False

        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.settimeout(10.0)
        try:
            remote.connect((REAL_HOST, REAL_PORT))
            log(f"Proxy connected to {REAL_HOST}:{REAL_PORT}")
        except Exception as e:
            log(f"ERROR connecting to remote: {e}")
            client.close()
            server.close()
            return False

        proxy_start = time.time()
        stopped = threading.Event()

        def forward(src, dst, tag):
            total = 0
            try:
                while not stopped.is_set():
                    try:
                        src.settimeout(0.5)
                        data = src.recv(65536)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    elapsed = time.time() - proxy_start
                    hdr = f"\n--- {tag} {len(data)} bytes @ {elapsed:.1f}s ---\n".encode()
                    pkt_f.write(hdr)
                    pkt_f.write(data)
                    pkt_f.flush()
                    log(f"  [{tag}] {len(data)} bytes @ {elapsed:.1f}s")
                    total += len(data)
                    dst.sendall(data)
            except Exception:
                pass
            stopped.set()
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass
            log(f"  [{tag}] closed, {total} bytes transferred")

        t1 = threading.Thread(target=forward, args=(client, remote, "CLIENT→SERVER"))
        t2 = threading.Thread(target=forward, args=(remote, client, "SERVER→CLIENT"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    server.close()
    fsize = os.path.getsize(PKT_FILE)
    log(f"\nProxy session complete. Captured → {PKT_FILE} ({fsize} bytes)")
    return True


def main():
    open(LOG_FILE, 'w', encoding='utf-8').close()
    log("=" * 60)
    log("  CAPTURE LOGIN PROTOCOL — WS2_32.connect Hook")
    log("=" * 60)

    proxy_thread = threading.Thread(target=run_proxy)
    proxy_thread.start()
    time.sleep(0.5)

    hp, pid, pi = launch_game()
    if not hp:
        log("ERROR: Failed to launch game")
        return 1

    connect_addr = 0
    orig_bytes = b''
    trampoline_addr = 0

    try:
        for m in enum_modules(pid):
            if m['name'].lower() == 'ws2_32.dll':
                connect_addr = find_export(hp, m['base'], 'connect')
                break
        if not connect_addr:
            log("WARNING: WS2_32.connect not found, hook skipped")

        if connect_addr:
            trampoline_addr, orig_bytes = install_connect_hook(hp, pid)
            if trampoline_addr:
                log("connect hook active ✓")
            else:
                log("WARNING: connect hook install failed")

        proxy_thread.join()

    except KeyboardInterrupt:
        log("\nInterrupted by user")
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        log(traceback.format_exc())
    finally:
        if connect_addr and orig_bytes:
            restore_connect_hook(hp, connect_addr, orig_bytes)
        try:
            kernel32.CloseHandle(hp)
        except Exception:
            pass

    log("\n--- Done ---")
    log(f"  Log: {LOG_FILE}")
    log(f"  Packets: {PKT_FILE}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
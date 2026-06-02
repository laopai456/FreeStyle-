"""
APOLLO Killer + Auto-Login (Keyboard Edition)

Flow:
1. Launch game + CRC patch (CREATE_SUSPENDED)
2. Wait for loading screen to finish
3. Type password via keyboard scan codes + Enter
4. Keep monitoring
"""
import ctypes
import ctypes.wintypes as wintypes
import frida
import json
import subprocess
import time
import os
import sys
import traceback
from collections import deque

try:
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Console
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

CREATE_SUSPENDED = 0x00000004
PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_WRITECOPY = 0x80

GAME_PATH = r"C:\Program Files (x86)\T2CN\街头篮球\FreeStyle.exe"
GAME_DIR = r"C:\Program Files (x86)\T2CN\街头篮球"
LOGIN_PARAM = "42.193.73.163:10005"
CRC_RVA1 = 0x001A3C54
CRC_RVA2 = 0x001BE222
CRC_PATCH = b'\x33\xC0\xC3'
PASSWORD = "880234dan"

LOG_FILE = r"d:\py\反编译\FreeStyle\apollo_dump\launch_log.txt"
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

SCANCODES = {
    '0': 0x0B, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05,
    '5': 0x06, '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A,
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, 'd': 0x20, 'e': 0x12,
    'f': 0x21, 'g': 0x22, 'h': 0x23, 'i': 0x17, 'j': 0x24,
    'k': 0x25, 'l': 0x26, 'm': 0x32, 'n': 0x31, 'o': 0x18,
    'p': 0x19, 'q': 0x10, 'r': 0x13, 's': 0x1F, 't': 0x14,
    'u': 0x16, 'v': 0x2F, 'w': 0x11, 'x': 0x2D, 'y': 0x15,
    'z': 0x2C,
}


class SI(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
        ('lpReserved2', wintypes.LPBYTE),
        ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE)]

class PI(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD),
        ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', wintypes.LPVOID),
        ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE),
        ('szModule', ctypes.c_char * 256), ('szExePath', ctypes.c_char * 260)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint), ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_uint), ("u", INPUT_UNION)]


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line); sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def enum_modules(pid):
    mods = []
    snap = kernel32.CreateToolhelp32Snapshot(0x00000008 | 0x00000010, pid)
    if snap == -1:
        return mods
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    if kernel32.Module32First(snap, ctypes.byref(me)):
        while True:
            mods.append({'name': me.szModule.decode('gbk', errors='replace'),
                'base': me.modBaseAddr, 'size': me.modBaseSize})
            if not kernel32.Module32Next(snap, ctypes.byref(me)):
                break
    kernel32.CloseHandle(snap)
    return mods


def rd(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok and n.value > 0 else None


def wr(handle, addr, data):
    n = ctypes.c_size_t()
    old = wintypes.DWORD()
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    ok = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), len(data), old, ctypes.byref(old))
    return ok and n.value == len(data)


def send_key(sc):
    arr = (INPUT * 2)()
    arr[0].type = INPUT_KEYBOARD
    arr[0].ki.wScan = sc
    arr[0].ki.dwFlags = KEYEVENTF_SCANCODE
    arr[1].type = INPUT_KEYBOARD
    arr[1].ki.wScan = sc
    arr[1].ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))


def find_game_window(pid):
    result = ctypes.c_void_p(0)
    def cb(hwnd, _):
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            result.value = hwnd
            return False
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(cb), 0)
    return result.value or 0


def force_foreground(hwnd):
    user32.SystemParametersInfoW(0x2001, 0, ctypes.c_void_p(0), 0)
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    cur = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(cur, tid, True)
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    user32.keybd_event(0x12, 0x38, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x12, 0x38, 2, 0)
    time.sleep(0.05)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(cur, tid, False)
    time.sleep(0.3)
    return user32.GetForegroundWindow() == hwnd


def wait_for_loading(hwnd):
    log("Waiting for loading screen to finish...")
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    offsets = [(0,0),(50,50),(-50,-50),(100,30),(-100,-30),(0,-80),(0,80),(-60,0),(60,0)]
    prev = None
    stable = 0
    for tick in range(120):
        time.sleep(1)
        pixels = []
        for dx, dy in offsets:
            dc = user32.GetWindowDC(hwnd)
            c = ctypes.windll.gdi32.GetPixel(dc, cx+dx-rect.left, cy+dy-rect.top)
            user32.ReleaseDC(hwnd, dc)
            pixels.append(c)
        h = tuple(pixels)
        if h == prev:
            stable += 1
        else:
            stable = 0
            prev = h
        if stable >= 5:
            log(f"Screen stable {stable}s, loading done!")
            return True
        if tick % 10 == 9:
            log(f"  ...loading ({tick+1}s, stable={stable}s)")
    log("Loading timeout, continuing anyway")
    return False


def post_char(hwnd, ch):
    """SendMessage WM_CHAR — 同步发送，等待窗口处理"""
    user32.SendMessageW(hwnd, 0x0102, ord(ch), 0)  # WM_CHAR
    time.sleep(0.02)

def post_vkey(hwnd, vk):
    """SendMessage WM_KEYDOWN + WM_KEYUP"""
    user32.SendMessageW(hwnd, 0x0100, vk, 0)
    time.sleep(0.02)
    user32.SendMessageW(hwnd, 0x0101, vk, 0)
    time.sleep(0.02)

def post_string(hwnd, text, delay=0.03):
    """逐字 SendMessage WM_CHAR"""
    for ch in text:
        user32.SendMessageW(hwnd, 0x0102, ord(ch), 0)
        time.sleep(delay)

def send_key(sc):
    """备用: SendInput 键盘扫描码"""
    arr = (INPUT * 2)()
    arr[0].type = INPUT_KEYBOARD
    arr[0].ki.wScan = sc
    arr[0].ki.dwFlags = KEYEVENTF_SCANCODE
    arr[1].type = INPUT_KEYBOARD
    arr[1].ki.wScan = sc
    arr[1].ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))


ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, 'apollo_dump')
LABEL_FILE = os.path.join(OUT_DIR, 'opcode_labels.json')
JS_MONITOR = os.path.join(ROOT, 'frida_monitor.js')
JS_INBOUND = os.path.join(ROOT, 'frida_inbound_v2.js')
JS_DINPUT = os.path.join(ROOT, 'frida_dinput_enter.js')
JS_E2      = os.path.join(ROOT, 'frida_e2_inbound.js')
JS_UDP      = os.path.join(ROOT, 'frida_udp.js')

rich_console = None
packet_queue = deque(maxlen=500)
pkt_count = {'OUT': 0, 'IN': 0, 'err': 0}
op_labels = {}
recording = False
recorded_pkts = []
filter_opcode = None
filter_dir = None
filter_plen = None


def load_op_labels():
    global op_labels
    if os.path.exists(LABEL_FILE):
        with open(LABEL_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            op_labels = {int(k): v for k, v in raw.items()}

def save_op_labels():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LABEL_FILE, 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in op_labels.items()}, f, ensure_ascii=False, indent=2)

def safe_input(prompt):
    try:
        return rich_console.input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return None


def do_label_ui():
    rich_console.print("\n[bold yellow]=== Label Opcode ===[/]")
    items = list(packet_queue)
    shown = {}
    for p in reversed(items):
        if p['d0'] not in shown and len(shown) < 10:
            shown[p['d0']] = p
    for d0, p in sorted(shown.items()):
        existing = op_labels.get(d0, '')
        rich_console.print(f"  0x{d0:02X} (plen={p['plen']}) [{existing}]")
    try:
        inp = safe_input("[bold]opcode hex (Enter=latest):[/] ")
        if inp is None: return
        d0 = items[-1]['d0'] if (not inp) else int(inp, 16)
        name = safe_input(f"[bold]Label for 0x{d0:02X}:[/] ")
        if name is None or not name: return
        op_labels[d0] = name
        save_op_labels()
        rich_console.print(f"[green]Saved: 0x{d0:02X} → {name}[/]")
    except (ValueError, KeyboardInterrupt):
        pass


def do_filter_ui():
    global filter_opcode, filter_dir, filter_plen
    rich_console.print("\n[bold yellow]=== Filter (d/o/p/x)[/]")
    try:
        cmd = safe_input("[bold]Filter:[/] ")
        if cmd is None: return
        cmd = cmd.lower()
        if cmd == 'd':
            d = safe_input("  OUT/IN/ALL: ")
            if d is None: return
            filter_dir = d if d.upper() in ('OUT', 'IN') else None
        elif cmd == 'o':
            v = safe_input("  opcode hex: ")
            if v is None: return
            filter_opcode = int(v, 16)
        elif cmd == 'p':
            v = safe_input("  plen: ")
            if v is None: return
            filter_plen = int(v)
        elif cmd == 'x':
            filter_opcode = None; filter_dir = None; filter_plen = None
        rich_console.print(f"[green]Filter: dir={filter_dir} opcode={f'0x{filter_opcode:02X}' if filter_opcode is not None else 'ALL'} plen={filter_plen}[/]")
    except (ValueError, KeyboardInterrupt):
        pass


def do_record_ui():
    global recording, recorded_pkts
    if recording:
        recording = False
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = os.path.join(OUT_DIR, f'recording_{ts}.json')
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(recorded_pkts, f, ensure_ascii=False, indent=2)
        rich_console.print(f"[green]Saved {len(recorded_pkts)} pkts → {fname}[/]")
        recorded_pkts = []
    else:
        recording = True; recorded_pkts = []
        rich_console.print("[bold red]● Recording started[/]")


# 全局 Frida session (由 main 中的后台线程设置)
g_frida_ses = None
g_frida_script = None
g_frida_inbound = None
g_frida_dinput = None
g_frida_e2 = None
g_frida_udp = None


def start_frida_monitor_ui():
    """启动交互式监控 UI (使用已有的 Frida session)"""
    global rich_console, packet_queue, pkt_count, g_frida_ses, g_frida_script, g_frida_inbound, g_frida_dinput, g_frida_e2, g_frida_udp
    from datetime import datetime

    if g_frida_ses is None:
        log("Frida session not available, can't start UI")
        return False

    rich_console = Console()
    load_op_labels()
    os.makedirs(OUT_DIR, exist_ok=True)

    log(f"Monitor active! OUT={pkt_count['OUT']} IN={pkt_count['IN']}  Keys: L/F/S/Q")
    log("")

    import msvcrt

    def make_table():
        t = Table(box=box.MINIMAL, header_style="bold cyan", show_lines=False, padding=(0, 1))
        t.add_column("#", width=4, style="dim")
        t.add_column("Dir", width=3)
        t.add_column("Seq", width=6)
        t.add_column("Op", width=10)
        t.add_column("Label", width=14)
        t.add_column("Len", width=4)
        t.add_column("Encrypted", width=20)
        t.add_column("Decrypted", width=20)

        for p in list(packet_queue)[-40:]:
            if filter_dir and p['dir'] != filter_dir: continue
            if filter_opcode is not None and p['d0'] != filter_opcode: continue
            if filter_plen is not None and p['plen'] != filter_plen: continue

            dir_style = "bold green" if p['dir'] == 'OUT' else "bold blue"
            dir_str = f"[{dir_style}]▶[/]" if p['dir'] == 'OUT' else f"[{dir_style}]◀[/]"
            label = op_labels.get(p['d0'], '')
            enc = ' '.join(p['enc'][i:i+2] for i in range(0, min(20, len(p['enc'])), 2))
            dec = ' '.join(p['dec'][i:i+2] for i in range(0, min(20, len(p['dec'])), 2))
            t.add_row(str(p['idx']), dir_str, str(p['seq']),
                      f"0x{p['d0']:02X}/0x{p['b0']:02X}", label, str(p['plen']), enc, dec)
        return t

    def do_dump():
        """一键 dump 全部包到 CSV"""
        pkts = list(packet_queue)
        if not pkts:
            rich_console.print("[yellow]No packets to dump[/]")
            time.sleep(1)
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = os.path.join(OUT_DIR, f'f12_{ts}.csv')
        with open(fname, 'w', encoding='utf-8') as f:
            f.write('idx,dir,f12,seq,plen,b0,d0,enc,dec\n')
            for p in pkts:
                f.write(f"{p['idx']},{p['dir']},{p['f12']},{p['seq']},{p['plen']},{p['b0']},{p['d0']},{p['enc']},{p['dec']}\n")
        rich_console.print(f"[bold green]Dumped {len(pkts)} packets to {os.path.basename(fname)}[/]")
        time.sleep(1.5)

    def check_keys():
        while msvcrt.kbhit():
            ch = msvcrt.getch().lower()
            if ch == b'l': do_label_ui()
            elif ch == b'f': do_filter_ui()
            elif ch == b's': do_record_ui()
            elif ch == b'd': do_dump()
            elif ch == b'q': return False
        return True

    try:
        while True:
            rich_console.clear()
            status = f"[bold]OUT: {pkt_count['OUT']}  IN: {pkt_count['IN']}  ERR: {pkt_count['err']}  {'[red]● REC[/]' if recording else ''}[/]"
            rich_console.print(status)

            title = "Packets"
            if filter_opcode is not None: title += f" | Op=0x{filter_opcode:02X}"
            if filter_dir: title += f" | Dir={filter_dir}"
            if filter_plen is not None: title += f" | Plen={filter_plen}"
            tbl = make_table()
            tbl.title = title
            rich_console.print(tbl)

            if op_labels:
                items = sorted(op_labels.items())[:15]
                text = "\n".join(f"0x{k:02X} → {v}" for k, v in items)
                rich_console.print(Panel(text, title=f"Labels ({len(op_labels)})"))

            if not check_keys():
                break
            time.sleep(0.2)

    except KeyboardInterrupt:
        pass
    finally:
        # 退出前自动 dump 全部包
        pkts = list(packet_queue)
        if pkts:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = os.path.join(OUT_DIR, f'f12_{ts}.csv')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write('idx,dir,f12,seq,plen,b0,d0,enc,dec\n')
                for p in pkts:
                    f.write(f"{p['idx']},{p['dir']},{p['f12']},{p['seq']},{p['plen']},{p['b0']},{p['d0']},{p['enc']},{p['dec']}\n")
            rich_console.print(f"\n[dim]Auto-saved {len(pkts)} packets to {os.path.basename(fname)}[/]")

        save_op_labels()
        try: g_frida_script.unload()
        except: pass
        try: g_frida_inbound.unload()
        except: pass
        try: g_frida_dinput.unload()
        except: pass
        try: g_frida_e2.unload()
        except: pass
        try: g_frida_udp.unload()
        except: pass
        try: g_frida_ses.detach()
        except: pass
        rich_console.clear()
        rich_console.print(f"\n[bold]Done: OUT={pkt_count['OUT']} IN={pkt_count['IN']} ERR={pkt_count['err']}[/]")
    return True


def on_monitor_msg(msg, data):
    if msg['type'] != 'send': return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except: return
    if isinstance(p, dict):
        t = p.get('type', '')
        if t == 'PKT':
            pkt_count[p['dir']] += 1
            packet_queue.append(p)
            if recording: recorded_pkts.append(p)
        elif t == 'err':
            pkt_count['err'] += 1

def on_inbound_msg(msg, data):
    """处理 frida_inbound_v2.js 的消息"""
    if msg['type'] != 'send': return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except: return
    if isinstance(p, dict):
        t = p.get('type', '')
        if t == 'PKT':
            pkt_count['IN'] += 1
            packet_queue.append(p)
            if recording: recorded_pkts.append(p)
        elif t == 'inbound':
            log(f"  [INB] {p['msg']}")
        elif t == 'iocp':
            log(f"  [IOCP] completion #{p['count']}: {p['bytes']} bytes, key={p.get('key','?')}")
        elif t == 'nt':
            log(f"  [NT] {p['msg']}")

def on_di_msg(msg, data):
    """处理 frida_dinput_enter.js 的消息"""
    if msg['type'] != 'send': return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except: return
    if isinstance(p, dict):
        t = p.get('type', '')
        if t in ('di_log', 'di_err'):
            log(f"  [DI] {p['msg']}")

def on_e2_msg(msg, data):
    """处理 frida_e2_inbound.js 的消息 (Plan C: E2 hook)"""
    if msg['type'] != 'send': return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except: return
    if isinstance(p, dict):
        t = p.get('type', '')
        if t == 'PKT':
            pkt_count['IN'] += 1
            packet_queue.append(p)
            if recording: recorded_pkts.append(p)
        elif t == 'e2':
            log(f"  [E2] {p['msg']}")

def on_udp_msg(msg, data):
    """处理 frida_udp.js 的消息 — UDP sendto/recvfrom hook"""
    if msg['type'] != 'send': return
    p = msg['payload']
    if isinstance(p, str):
        try: p = json.loads(p)
        except: return
    if isinstance(p, dict):
        t = p.get('type', '')
        if t == 'PKT':
            pkt_count[p['dir']] += 1
            packet_queue.append(p)
            if recording: recorded_pkts.append(p)
        elif t == 'udp':
            log(f"  [UDP] {p['msg']}")
        elif t == 'udp_heartbeat':
            pass  # 安静 heartbeat


# === 鼠标点击常量 ===
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000


def auto_login_keyboard(hwnd):
    """SetWindowText 写密码 → mouse_event 硬件级点击登录按钮"""
    log("=" * 50)
    log("  AUTO-LOGIN (Edit + mouse_event click)")
    log("=" * 50)

    tid = user32.GetWindowThreadProcessId(hwnd, None)
    cur_tid = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(cur_tid, tid, True)
    log(f"  AttachThreadInput: cur={cur_tid} game={tid}")

    # === 1. 枚举子窗口找 Edit 控件 ===
    edit_hwnds = []
    found_hwnds = []

    def enum_child_cb(child, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(child, buf, 256)
        cls = buf.value
        r = wintypes.RECT()
        user32.GetWindowRect(child, ctypes.byref(r))
        w = r.right - r.left; h = r.bottom - r.top
        txt_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(child, txt_buf, 256)
        found_hwnds.append((child, cls, (r.left, r.top, w, h), txt_buf.value))
        if cls and 'edit' in cls.lower():
            edit_hwnds.append((child, cls, (r.left, r.top, w, h), txt_buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumChildWindows(hwnd, WNDENUMPROC(enum_child_cb), 0)
    log(f"  Found {len(found_hwnds)} child windows, {len(edit_hwnds)} Edit controls")

    if not edit_hwnds:
        log("  No standard Edit controls — DirectX UI, cannot auto-fill")
        user32.AttachThreadInput(cur_tid, tid, False)
        return False

    pw_edit = edit_hwnds[0][0] if len(edit_hwnds) == 1 else edit_hwnds[-1][0]
    user32.SetWindowTextW(pw_edit, PASSWORD)
    time.sleep(0.1)
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(pw_edit, buf, 256)
    log(f"  Password field set: '{buf.value}'")

    # === 2. 计算登录按钮位置 ===
    # 按钮在 Edit 控件下方（Edit 在窗口中间偏上，按钮在偏下）
    # 登录按钮位置 = Edit 下方 ~Edit 高度 * 1.5 的距离
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    cw = r.right - r.left
    ch = r.bottom - r.top
    log(f"  Client area: {cw}x{ch}")

    # 登录按钮 = 水平居中, 垂直在 60% 位置（Edit 在 ~35-40%）
    btn_x = cw // 2
    btn_y = int(ch * 0.60)

    # 转屏幕坐标
    pt = wintypes.POINT(btn_x, btn_y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    log(f"  Login button estimated @ client({btn_x},{btn_y}) → screen({pt.x},{pt.y})")

    # === 3. 激活窗口 → 移动鼠标 → 点击 ===
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)

    # 保存旧鼠标位置
    old_pos = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(old_pos))

    # 移动到登录按钮
    user32.SetCursorPos(pt.x, pt.y)
    time.sleep(0.15)

    # 硬件级鼠标点击 (DirectInput 也挡不住)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    log("  mouse_event LEFT CLICK sent")

    # 恢复鼠标位置
    time.sleep(0.1)
    user32.SetCursorPos(old_pos.x, old_pos.y)

    user32.AttachThreadInput(cur_tid, tid, False)
    log("  Auto-login complete!")
    return True


def main():
    open(LOG_FILE, 'w', encoding='utf-8').close()
    log("=" * 60)
    log("  APOLLO Killer + Auto-Login (Keyboard Edition)")
    log("=" * 60)

    try:
        subprocess.run(['taskkill', '/F', '/IM', 'FreeStyle.exe'], capture_output=True)
        time.sleep(1)

        si = SI(); si.cb = ctypes.sizeof(SI); pi = PI()
        ok = kernel32.CreateProcessW(GAME_PATH, f'"{GAME_PATH}" {LOGIN_PARAM}',
            None, None, False, CREATE_SUSPENDED, None, GAME_DIR, ctypes.byref(si), ctypes.byref(pi))
        if not ok:
            log(f"CreateProcess: {ctypes.WinError(ctypes.get_last_error())}")
            return 1

        hp, pid = pi.hProcess, pi.dwProcessId
        kernel32.ResumeThread(pi.hThread)
        log(f"PID={pid} launched")

        # CRC patch
        apollo_base = 0
        for attempt in range(15):
            time.sleep(1)
            modules = enum_modules(pid)
            for m in modules:
                if 'apolloct' in m['name'].lower():
                    apollo_base = m['base']
            if apollo_base:
                break
            log(f"  Waiting Apollo... ({attempt+1}/15)")

        if apollo_base:
            c1, c2 = apollo_base + CRC_RVA1, apollo_base + CRC_RVA2
            orig1 = rd(hp, c1, 3)
            orig2 = rd(hp, c2, 3)
            log(f"  CRC#1 @ 0x{c1:08X}: orig={orig1.hex() if orig1 else 'FAIL'}")
            log(f"  CRC#2 @ 0x{c2:08X}: orig={orig2.hex() if orig2 else 'FAIL'}")
            wr(hp, c1, CRC_PATCH)
            wr(hp, c2, CRC_PATCH)
            verify1 = rd(hp, c1, 3)
            verify2 = rd(hp, c2, 3)
            if verify1 == CRC_PATCH and verify2 == CRC_PATCH:
                log("  CRC patched OK!")
            else:
                log("  WARNING: CRC patch verification FAILED!")
        else:
            log("  WARNING: ApolloCT.dll not found (game may have already loaded it)")

        # === 尽早启动 Frida (CRC patch 后, 窗口出现前) ===
        # 此时 DirectInput 尚未初始化, DirectInput8Create hook 能拦截设备创建
        log("")
        log("Starting Frida early (before DirectInput init)...")
        frida_ok = False
        if HAS_RICH:
            import threading
            monitor_started = threading.Event()

            def _start_monitor():
                nonlocal frida_ok
                try:
                    ses = frida.attach(pid)

                    # 1. 加载主监控脚本 (CRC patch + WSASend)
                    with open(JS_MONITOR, 'r', encoding='utf-8') as f:
                        js = f.read()
                    script = ses.create_script(js)
                    script.on('message', lambda msg, data: on_monitor_msg(msg, data))
                    script.load()
                    log("  frida_monitor.js loaded (CRC patch + WSASend)")

                    # 2. 加载入站包捕获脚本
                    with open(JS_INBOUND, 'r', encoding='utf-8') as f:
                        js2 = f.read()
                    inbound_script = ses.create_script(js2)
                    inbound_script.on('message', on_inbound_msg)
                    inbound_script.load()
                    log("  frida_inbound_v2.js loaded (NT-level: NtDevIoCtrl + NtReadFile + recv)")

                    # 3. 加载 DirectInput 绕过脚本
                    with open(JS_DINPUT, 'r', encoding='utf-8') as f:
                        js3 = f.read()
                    di_script = ses.create_script(js3)
                    di_script.on('message', on_di_msg)
                    di_script.load()
                    log("  frida_dinput_enter.js loaded (DirectInput bypass)")

                    # 4. 加载 E2 入站包捕获脚本 (Plan C)
                    with open(JS_E2, 'r', encoding='utf-8') as f:
                        js4 = f.read()
                    e2_script = ses.create_script(js4)
                    e2_script.on('message', on_e2_msg)
                    e2_script.load()
                    log("  frida_e2_inbound.js loaded (Plan C: E2 hook)")

                    # 5. 加载 UDP 捕获脚本 (sendto + recvfrom)
                    with open(JS_UDP, 'r', encoding='utf-8') as f:
                        js5 = f.read()
                    udp_script = ses.create_script(js5)
                    udp_script.on('message', on_udp_msg)
                    udp_script.load()
                    log("  frida_udp.js loaded (sendto/recvfrom — UDP capture)")

                    time.sleep(0.5)
                    global g_frida_ses, g_frida_script, g_frida_inbound, g_frida_dinput, g_frida_e2, g_frida_udp
                    g_frida_ses = ses
                    g_frida_script = script
                    g_frida_inbound = inbound_script
                    g_frida_dinput = di_script
                    g_frida_e2 = e2_script
                    g_frida_udp = udp_script
                    frida_ok = True
                    monitor_started.set()
                except Exception as e:
                    log(f"  Frida attach failed: {e}")
                    monitor_started.set()

            threading.Thread(target=_start_monitor, daemon=True).start()
            monitor_started.wait(timeout=15)
            log("  Frida all scripts loaded!")
        else:
            log("  Rich not installed, skipping packet monitor")

        log("")
        log("Waiting for login window...")
        hwnd = 0
        for attempt in range(90):
            hwnd = find_game_window(pid)
            if hwnd:
                break
            time.sleep(1)
        if not hwnd:
            log("Game window not found!")
            kernel32.CloseHandle(pi.hThread)
            kernel32.CloseHandle(hp)
            return 1

        log(f"Game window found (hwnd=0x{hwnd:08X})")
        wait_for_loading(hwnd)

        ec = wintypes.DWORD()
        kernel32.GetExitCodeProcess(hp, ctypes.byref(ec))
        if ec.value != 259:
            log(f"Game exited before login (code {ec.value})!")
            kernel32.CloseHandle(pi.hThread)
            kernel32.CloseHandle(hp)
            return 1

        # === 等用户确认登录界面就绪 ===
        log("Waiting for login screen to appear...")
        time.sleep(3)

        # === 填密码 + 等手动登录 ===
        log("")
        log("=" * 50)
        log("  Pre-fill password")
        log("=" * 50)

        tid = user32.GetWindowThreadProcessId(hwnd, None)
        cur_tid = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(cur_tid, tid, True)

        edit_hwnds = []
        def enum_child_cb(child, _):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(child, buf, 256)
            if buf.value and 'edit' in buf.value.lower():
                edit_hwnds.append(child)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumChildWindows(hwnd, WNDENUMPROC(enum_child_cb), 0)

        if edit_hwnds:
            pw_edit = edit_hwnds[0] if len(edit_hwnds) == 1 else edit_hwnds[-1]
            user32.SetWindowTextW(pw_edit, PASSWORD)
            time.sleep(0.1)
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(pw_edit, buf, 256)
            log(f"  Password filled: '{buf.value}'")
        else:
            log("  WARNING: No Edit control found")

        user32.AttachThreadInput(cur_tid, tid, False)

        log("")
        log("  >>> 请在游戏窗口里手动点登录 <<<")

        # 等待登录完成
        log("Waiting for login to complete (15s)...")
        for i in range(15):
            time.sleep(1)
            if pkt_count['OUT'] > 20 or pkt_count['IN'] > 5:
                log(f"  Packets flowing! (OUT={pkt_count['OUT']} IN={pkt_count['IN']})")
                break
            if i % 5 == 4:
                log(f"  ... waiting (OUT={pkt_count['OUT']} IN={pkt_count['IN']})")

        # === 进入交互式监控 UI ===
        if HAS_RICH and monitor_started.is_set():
            log(f"\nCaptured: OUT={pkt_count['OUT']} IN={pkt_count['IN']}")
            log("Switching to interactive monitor UI...")
            start_frida_monitor_ui()  # 接管原有的 session
        else:
            log("Game running. Press Ctrl+C to stop.")
            while True:
                time.sleep(2)
                ec = wintypes.DWORD()
                kernel32.GetExitCodeProcess(hp, ctypes.byref(ec))
                if ec.value != 259:
                    log(f"Game exited (code {ec.value})")
                    break

        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(hp)
        return 0

    except KeyboardInterrupt:
        log("Ctrl+C -- exiting")
        return 0
    except Exception as e:
        log(f"CRASH: {e}")
        log(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())

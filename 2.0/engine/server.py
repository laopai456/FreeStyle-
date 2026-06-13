# server.py — TCP 服务器，供 C# WPF 前端调用
# v2: DWORD扫描改用 Windows API (ReadProcessMemory/WriteProcessMemory)
#     在 Python 线程中执行，完全不阻塞游戏线程
import sys, json, socket, threading, os, traceback, struct, time
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ===== 文件日志（C#隐藏窗口，stdout不可见，写文件方便监控）=====
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine.log')
LOG_MAX_BYTES = 1 * 1024 * 1024  # 超过 1MB 时截断
LOG_KEEP_LINES = 500  # 截断时保留最后 500 行

def _trim_log():
    """启动时检查日志大小，超过阈值则截断保留尾部"""
    try:
        size = os.path.getsize(LOG_FILE)
        if size < LOG_MAX_BYTES:
            return
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        kept = lines[-LOG_KEEP_LINES:] if len(lines) > LOG_KEEP_LINES else lines
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(kept)
    except:
        pass

_trim_log()

def log(msg):
    ts = time.strftime('%H:%M:%S', time.localtime()) + f'.{int(time.time()*1000)%1000:03d}'
    line = f'[{ts}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass

log(f'=== engine start ===')
log(f'Python: {sys.executable}')
log(f'CWD: {os.getcwd()}')

import frida
log(f'frida: {frida.__version__} from {frida.__file__}')

from hook_manager import create_js
import itemshop_db

# 加载 c-code → 角色名映射表
_ccode_map = {}
_ccode_map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ccode_map.json')
if os.path.exists(_ccode_map_path):
    try:
        with open(_ccode_map_path, 'r', encoding='utf-8') as f:
            _ccode_map = json.load(f)
        log(f'[INIT] ccode_map loaded: {len(_ccode_map)} entries')
    except Exception as e:
        log(f'[INIT] ccode_map load failed: {e}')

HOST = '127.0.0.1'
PORT = 18731

session = None
script = None
replace_map = {}
effect_map_store = {}
collected_slots = {}
collected_ccodes = []  # JS 端收集的角色码 (c%d.xml)
connected_pid = None
memory_scanned = False  # JS 端是否实际做过内存扫描（bruteScan/dwordScan）

# ===== Hook 日志缓冲区（供 C# UI 实时获取） =====
hook_log_buffer = []
HOOK_LOG_MAX = 200

# ===== Windows API 内存扫描 =====
import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_READONLY = 0x02
PAGE_EXECUTE_READ = 0x20

WRITABLE_PROTECTS = {PAGE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY}
READABLE_PROTECTS = {PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY}

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

def native_dword_scan(pid, rmap, emap=None):
    """用 Windows API 扫描游戏内存，替换 ItemCode + 写入特效
    在 Python 线程中执行，不阻塞游戏"""
    t0 = time.time()
    log(f'[SCAN] 开始 native_dword_scan pid={pid} rmap={rmap} emap={emap}')

    access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        log(f'[SCAN] OpenProcess 失败: error={err}')
        return 0, 0

    try:
        # 枚举内存区域
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while True:
            ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
            if ret == 0:
                break
            base_addr = mbi.BaseAddress or 0
            region_size = mbi.RegionSize or 0
            if mbi.State == MEM_COMMIT and mbi.Protect in WRITABLE_PROTECTS:
                regions.append((base_addr, region_size))
            addr = base_addr + region_size
            if addr == 0 or addr > 0x7FFFFFFFFFFF:
                break

        log(f'[SCAN] 枚举到 {len(regions)} 个可写内存区域, {time.time()-t0:.2f}s')

        total_replaced = 0
        total_effects = 0

        # 第一步：替换 SRC → DST（仅属性表条目，+0x04 == 0x00010000）
        flag_bytes = struct.pack('<I', 0x00010000)
        for src_str, dst_str in rmap.items():
            src_val = int(src_str) & 0xFFFFFFFF
            dst_val = int(dst_str) & 0xFFFFFFFF
            src_bytes = struct.pack('<I', src_val)
            dst_bytes = struct.pack('<I', dst_val)

            for base, size in regions:
                if size > 200 * 1024 * 1024:
                    continue

                buf = ctypes.create_string_buffer(size)
                read_bytes = ctypes.c_size_t()
                if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read_bytes)):
                    continue

                data = buf.raw[:read_bytes.value]
                offset = 0
                while True:
                    idx = data.find(src_bytes, offset)
                    if idx < 0:
                        break

                    # 只替换属性表条目：+0x04 必须是 0x00010000
                    # 商城/背包等数据没有此标志，不会被替换
                    if idx + 8 <= len(data):
                        flag = struct.unpack_from('<I', data, idx + 4)[0]
                        if flag == 0x00010000:
                            write_addr = base + idx
                            written = ctypes.c_size_t()
                            if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(write_addr), dst_bytes, len(dst_bytes), ctypes.byref(written)):
                                total_replaced += 1

                    offset = idx + 4

        log(f'[SCAN] ItemCode 替换完成: {total_replaced} 处, {time.time()-t0:.2f}s')

        # 第二步：对 DST 属性表写入特效
        if emap:
            for src_str, dst_str in rmap.items():
                effect_id = emap.get(dst_str, 0)
                if effect_id <= 0:
                    continue

                dst_val = int(dst_str) & 0xFFFFFFFF
                dst_bytes = struct.pack('<I', dst_val)
                effect_data = struct.pack('<II', effect_id, 0x00010000)

                for base, size in regions:
                    if size > 200 * 1024 * 1024:
                        continue

                    buf = ctypes.create_string_buffer(size)
                    read_bytes = ctypes.c_size_t()
                    if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read_bytes)):
                        continue

                    data = buf.raw[:read_bytes.value]
                    offset = 0
                    while True:
                        idx = data.find(dst_bytes, offset)
                        if idx < 0:
                            break

                        # 检查 +0x04 处标志位 == 0x00010000
                        if idx + 12 <= len(data):
                            flag = struct.unpack_from('<I', data, idx + 4)[0]
                            if flag == 0x00010000:
                                effect_addr = base + idx + 8
                                written = ctypes.c_size_t()
                                if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(effect_addr), effect_data, len(effect_data), ctypes.byref(written)):
                                    total_effects += 1

                        offset = idx + 4

        elapsed = time.time() - t0
        log(f'[SCAN] 全部完成: {total_replaced} 替换, {total_effects} 特效, {elapsed:.2f}s')
        return total_replaced, total_effects

    finally:
        kernel32.CloseHandle(handle)


def native_brute_scan(pid, rmap, emap=None):
    """练习场专用：暴力 DWORD 扫描（无 flag 检查）
    练习场数据没有 0x00010000 标志，必须无差别替换
    退出练习场时 need_restore_shop 会恢复非属性表条目"""
    t0 = time.time()
    log(f'[BRUTE] 开始 native_brute_scan pid={pid} rmap={rmap}')

    access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        log(f'[BRUTE] OpenProcess 失败: error={err}')
        return 0, 0

    try:
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while True:
            ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
            if ret == 0:
                break
            base_addr = mbi.BaseAddress or 0
            region_size = mbi.RegionSize or 0
            if mbi.State == MEM_COMMIT and mbi.Protect in WRITABLE_PROTECTS:
                regions.append((base_addr, region_size))
            addr = base_addr + region_size
            if addr == 0 or addr > 0x7FFFFFFFFFFF:
                break

        log(f'[BRUTE] 枚举到 {len(regions)} 个可写内存区域, {time.time()-t0:.2f}s')

        total_replaced = 0
        total_effects = 0

        # 第一步：暴力替换 SRC → DST（无 flag 检查）
        for src_str, dst_str in rmap.items():
            src_val = int(src_str) & 0xFFFFFFFF
            dst_val = int(dst_str) & 0xFFFFFFFF
            src_bytes = struct.pack('<I', src_val)
            dst_bytes = struct.pack('<I', dst_val)

            for base, size in regions:
                if size > 200 * 1024 * 1024:
                    continue

                buf = ctypes.create_string_buffer(size)
                read_bytes = ctypes.c_size_t()
                if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read_bytes)):
                    continue

                data = buf.raw[:read_bytes.value]
                offset = 0
                while True:
                    idx = data.find(src_bytes, offset)
                    if idx < 0:
                        break

                    write_addr = base + idx
                    written = ctypes.c_size_t()
                    if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(write_addr), dst_bytes, len(dst_bytes), ctypes.byref(written)):
                        total_replaced += 1

                    offset = idx + 4

        log(f'[BRUTE] ItemCode 替换完成: {total_replaced} 处, {time.time()-t0:.2f}s')

        # 第二步：对 DST 属性表写入特效（有 flag 检查，只写属性表条目）
        if emap:
            flag_bytes = struct.pack('<I', 0x00010000)
            for src_str, dst_str in rmap.items():
                effect_id = emap.get(dst_str, 0)
                if effect_id <= 0:
                    continue

                dst_val = int(dst_str) & 0xFFFFFFFF
                dst_bytes = struct.pack('<I', dst_val)
                effect_data = struct.pack('<II', effect_id, 0x00010000)

                for base, size in regions:
                    if size > 200 * 1024 * 1024:
                        continue

                    buf = ctypes.create_string_buffer(size)
                    read_bytes = ctypes.c_size_t()
                    if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read_bytes)):
                        continue

                    data = buf.raw[:read_bytes.value]
                    offset = 0
                    while True:
                        idx = data.find(dst_bytes, offset)
                        if idx < 0:
                            break

                        # 特效只写属性表条目
                        if idx + 12 <= len(data):
                            flag = struct.unpack_from('<I', data, idx + 4)[0]
                            if flag == 0x00010000:
                                effect_addr = base + idx + 8
                                written = ctypes.c_size_t()
                                if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(effect_addr), effect_data, len(effect_data), ctypes.byref(written)):
                                    total_effects += 1

                        offset = idx + 4

        elapsed = time.time() - t0
        log(f'[BRUTE] 全部完成: {total_replaced} 替换, {total_effects} 特效, {elapsed:.2f}s')
        return total_replaced, total_effects

    finally:
        kernel32.CloseHandle(handle)


def native_restore_shop(pid, rmap):
    """用 Windows API 恢复商城/背包数据：非属性表的 DST → SRC
    属性表条目（+0x04 == 0x00010000）不动，那些是装备定义数据"""
    t0 = time.time()
    log(f'[RESTORE] 开始 native_restore_shop pid={pid} rmap={rmap}')

    access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        log(f'[RESTORE] OpenProcess 失败: error={err}')
        return 0

    try:
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while True:
            ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
            if ret == 0:
                break
            base_addr = mbi.BaseAddress or 0
            region_size = mbi.RegionSize or 0
            if mbi.State == MEM_COMMIT and mbi.Protect in WRITABLE_PROTECTS:
                regions.append((base_addr, region_size))
            addr = base_addr + region_size
            if addr == 0 or addr > 0x7FFFFFFFFFFF:
                break

        log(f'[RESTORE] 枚举到 {len(regions)} 个可写内存区域, {time.time()-t0:.2f}s')

        total_restored = 0
        per_item_counts = {}  # 逐映射恢复计数

        # 扫描 DST DWORD → 只恢复非属性表条目（+0x04 != 0x00010000）
        flag_bytes = struct.pack('<I', 0x00010000)
        for src_str, dst_str in rmap.items():
            src_val = int(src_str) & 0xFFFFFFFF
            dst_val = int(dst_str) & 0xFFFFFFFF
            dst_bytes = struct.pack('<I', dst_val)
            src_bytes = struct.pack('<I', src_val)
            item_count = 0

            for base, size in regions:
                if size > 200 * 1024 * 1024:
                    continue

                buf = ctypes.create_string_buffer(size)
                read_bytes = ctypes.c_size_t()
                if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read_bytes)):
                    continue

                data = buf.raw[:read_bytes.value]
                offset = 0
                while True:
                    idx = data.find(dst_bytes, offset)
                    if idx < 0:
                        break

                    # 只恢复非属性表条目：+0x04 不是 0x00010000 的才恢复
                    if idx + 8 <= len(data):
                        flag = struct.unpack_from('<I', data, idx + 4)[0]
                        if flag != 0x00010000:
                            write_addr = base + idx
                            written = ctypes.c_size_t()
                            if kernel32.WriteProcessMemory(handle, ctypes.c_void_p(write_addr), src_bytes, len(src_bytes), ctypes.byref(written)):
                                total_restored += 1
                                item_count += 1

                    offset = idx + 4

            per_item_counts[f'{dst_str}→{src_str}'] = item_count

        elapsed = time.time() - t0
        log(f'[RESTORE] 完成: {total_restored} 处恢复, {elapsed:.2f}s, 逐项: {per_item_counts}')
        return total_restored

    finally:
        kernel32.CloseHandle(handle)


def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# ===== 启动游戏（绕过启动器，直接启动 + CRC patch）=====
LAUNCH_SERVER = "42.193.73.163:10005"  # 服务器地址
CRC_RVA1 = 0x001A3C54
CRC_RVA2 = 0x001BE222
CRC_PATCH = b'\x33\xC0\xC3'  # xor eax,eax; ret

def handle_launch_game(game_dir):
    """直接启动 FreeStyle.exe 并 patch CRC 校验"""
    import subprocess
    import psutil

    # 检查是否已运行
    existing_pid = find_pid()
    if existing_pid:
        return {'status': 'ok', 'pid': existing_pid, 'msg': 'FreeStyle.exe already running'}

    exe_path = os.path.join(game_dir, 'FreeStyle.exe')
    if not os.path.isfile(exe_path):
        return {'status': 'error', 'error': f'FreeStyle.exe not found: {exe_path}'}

    # 以 CREATE_SUSPENDED 启动
    log(f'[LAUNCH] starting {exe_path} {LAUNCH_SERVER}')
    CREATE_SUSPENDED = 0x4
    proc = subprocess.Popen(
        [exe_path, LAUNCH_SERVER],
        creationflags=CREATE_SUSPENDED,
        cwd=game_dir
    )
    pid = proc.pid
    log(f'[LAUNCH] PID={pid} (suspended)')

    # 等待进程初始化（模块加载）
    time.sleep(3)

    # CRC patch（写入 ApolloCT.dll 的 RVA，不在 .text 段内，安全）
    import pymem
    try:
        pm = pymem.Pymem()
        pm.open_process_from_id(pid)

        for rva, patch_bytes in [(CRC_RVA1, CRC_PATCH), (CRC_RVA2, CRC_PATCH)]:
            try:
                orig = pm.read_bytes(rva, 3)
                pm.write_bytes(rva, patch_bytes, len(patch_bytes))
                log(f'[LAUNCH] CRC patch 0x{rva:08X}: {orig.hex()} -> {patch_bytes.hex()}')
            except Exception as e:
                log(f'[LAUNCH] CRC patch 0x{rva:08X} failed: {e}')

        pm.close_process()
    except Exception as e:
        log(f'[LAUNCH] pymem error: {e}')
        return {'status': 'error', 'error': f'CRC patch failed: {e}'}

    # 恢复主线程
    log('[LAUNCH] resuming main thread')
    PROCESS_SUSPEND_RESUME = 0x0800
    handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
    if handle:
        # NtResumeProcess
        ntdll = ctypes.WinDLL('ntdll')
        ntdll.NtResumeProcess(handle)
        kernel32.CloseHandle(handle)

    log(f'[LAUNCH] game launched PID={pid}')
    return {'status': 'ok', 'pid': pid, 'msg': 'Game launched with CRC patched'}

def on_message(msg, data):
    global collected_slots, hook_log_buffer, memory_scanned
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        hook_line = None  # 写入 C# UI 的简短日志
        if t == 'collect':
            collected_slots[str(p['slot'])] = p['code']
            log(f'[HOOK] collect slot {p["slot"]}: {p["code"]} ({itemshop_db.get_name(p["code"])})')
        elif t == 'collect_ccode':
            if p['code'] not in collected_ccodes:
                collected_ccodes.append(p['code'])
                en_name = _ccode_map.get(str(p['code']), '???')
                log(f'[HOOK] collect_ccode: {p["code"]} ({en_name})')
        elif t == 'sprintf_fmt':
            log(f'[DEBUG] sprintf fmt="{p["fmt"]}" code={p["code"]} isC={p["isC"]}')
        elif t == 'dword_scan_done':
            memory_scanned = True
            effect_info = f', EFFECT_MAP=[{p.get("effectMap","")}]' if p.get('effectMap') else ''
            log(f'[HOOK] dword_scan_done: {p["total"]} 替换, {p["effects"]} 特效, {p["ms"]}ms, 方法={p.get("method","?")}, 区域={p.get("ranges","?")}{effect_info}')
            hook_line = f'DWORD扫描: {p["total"]}替换, {p["effects"]}特效, {p["ms"]}ms'
        elif t == 'dword_scan_per_map':
            log(f'[HOOK] 逐映射统计: {p.get("nonzero","?")}/{p.get("total_maps","?")}映射命中, max={p.get("max","?")}({p.get("max_src","")}→{p.get("max_dst","")}), min={p.get("min","?")}')
        elif t == 'dword_scan_trigger':
            log(f'[HOOK] dwordScan触发: src={p.get("src","")} dst={p.get("dst","")} effect={p.get("enable_effect","")} scene={p.get("scene","")}')
        elif t == 'mem_diag':
            log(f'[HOOK] 内存诊断: SRC={p.get("src","")} 出现{p.get("src_in_mem",0)}次, DST={p.get("dst","")} 出现{p.get("dst_in_mem",0)}次')
        elif t == 'dword_scan_debug':
            log(f'[HOOK] dword_scan_debug: EFFECT_MAP=[{p.get("effectMap","")}], 区域={p.get("ranges","?")}')
            hook_line = f'特效诊断: EFFECT_MAP=[{p.get("effectMap","")}]'
        elif t == 'dword_scan_fallback':
            log(f'[HOOK] dword_scan_fallback: {p["reason"]}, 已替换={p["replaced"]}，JS降级补扫特效')
        elif t == 'effect_detail':
            log(f'[HOOK] effect_write: addr={p["addr"]} dst={p["dst"]} effectId={p["effectId"]} 原值={p["curEffect"]} 回读={p["readback"]}')
            hook_line = f'特效写入: {p["dst"]}→effect={p["effectId"]} 原值={p["curEffect"]} 回读={p["readback"]}'
        elif t == 'effect_struct':
            slot_status = '有特效槽' if p.get('hasEffectSlot') else '无特效槽(跳过)'
            log(f'[HOOK] effect_struct: addr={p["addr"]} dst={p["dst"]} +08={p["val08"]} +0C=0x{p["val0C"]:08X} {slot_status}')
            hook_line = f'特效结构: {p["dst"]} +08={p["val08"]} +0C=0x{p["val0C"]:08X} {slot_status}'
        elif t == 'sprintf_hit':
            log(f'[HOOK] sprintf HIT: src={p["src"]} → dst={p["dst"]} ebp={p["ebp"]}处 idx={p["idx"]}')
            hook_line = f'sprintf命中: {p["src"]}→{p["dst"]} ({p["ebp"]}处)'
        elif t == 'sprintf_miss':
            is_dst = p.get('is_dst', False)
            dst_tag = f' [DST!←{p.get("matched_src","")}]' if is_dst else ''
            log(f'[HOOK] sprintf MISS: code={p["code"]} idx={p["idx"]}{dst_tag}')
            # 不推送到 UI，减少冗余
        elif t == 'sprintf_err':
            log(f'[HOOK] sprintf ERROR: {p["msg"]}')
            hook_line = f'sprintf错误: {p["msg"]}'
        elif t == 'strcpy_hit':
            log(f'[HOOK] strcpy HIT: src={p["src"]} → dst={p["dst"]} path={p["path"]}')
            hook_line = f'strcpy命中: {p["src"]}→{p["dst"]}'
        elif t == 'strcpy_miss':
            log(f'[HOOK] strcpy MISS: path={p["path"]}')
        elif t == 'strcpy_err':
            log(f'[HOOK] strcpy ERROR: {p["msg"]}')
            hook_line = f'strcpy错误: {p["msg"]}'
        elif t == 'strcpy_brute_result':
            log(f'[HOOK] strcpy bruteScan: {p["replaced"]} 替换 (练习场)')
            hook_line = f'暴力扫描: {p["replaced"]}替换'
        elif t == 'brute_scan_start':
            log(f'[HOOK] brute_scan_start: mapSize={p["mapSize"]}')
            hook_line = f'暴力扫描开始: {p["mapSize"]}个映射'
        elif t == 'ranges_filtered':
            log(f'[HOOK] 区域过滤: {p["total_ranges"]}→{p["private_ranges"]}个区域, {p["total_bytes"]//1024//1024}MB→{p["private_bytes"]//1024//1024}MB (MEM_PRIVATE)')
        elif t == 'brute_scan_cache':
            log(f'[HOOK] 区域缓存: {p["total"]}→{p["kept"]}个区域(跳过{p["skipped"]}), {p.get("total_bytes",0)//1024//1024}MB→{p.get("private_bytes",0)//1024//1024}MB')
        elif t == 'vq_error':
            log(f'[HOOK] VirtualQuery失败: {p["msg"]}')
        elif t == 'brute_scan_fallback':
            log(f'[HOOK] brute_scan_fallback: {p["reason"]}')
            hook_line = f'暴力扫描回退: {p["reason"]}'
        elif t == 'brute_scan_error':
            log(f'[HOOK] brute_scan_error: step={p["step"]} msg={p["msg"]}')
        elif t == 'cmodule_error':
            log(f'[HOOK] CModule编译失败: {p["msg"]}')
            hook_line = f'CModule编译失败: {p["msg"]}'
        elif t == 'cmodule_ok':
            log('[HOOK] CModule编译成功')
        elif t == 'precommit_done':
            log(f'[HOOK] 页面预提交完成: {p["bytes"]}字节, {p["ms"]}ms, {p["ranges"]}个区域')
        elif t == 'scene_change':
            scene_names = {'room': '大厅/房间', 'practice': '练习场', 'lobby': '大厅', 'unknown': '未知'}
            from_name = scene_names.get(p['from'], p['from'])
            to_name = scene_names.get(p['to'], p['to'])
            log(f'[场景] {from_name} → {to_name}')
            hook_line = f'进入{to_name}'
        elif t == 'brute_scan_done':
            memory_scanned = True
            method = p.get('method', '?')
            precommitted = p.get('precommitted', '?')
            private_mb = p.get('private_mb', '?')
            total_mb = p.get('total_mb', '?')
            precommit_ms = p.get('precommit_ms', 0)
            nonzero = p.get('nonzero_maps', '?')
            max_per = p.get('max_per_map', '?')
            max_src = p.get('max_src', '')
            log(f'[HOOK] brute_scan_done: {p["total"]} 替换, {p["ms"]}ms, method={method}, precommitted={precommitted}, scan={private_mb}MB/{total_mb}MB, precommit={precommit_ms}ms, maps={nonzero}, max={max_per}({max_src})')
            hook_line = f'暴力扫描完成: {p["total"]}替换, {p["ms"]}ms [{method}]'
        elif t == 'need_restore_shop':
            # 暂时禁用：native_restore_shop 会把房间装备数据也一起恢复，导致光头
            # 后续需要研究如何只恢复装备槽数据而不影响属性表
            log(f'[HOOK] need_restore_shop 收到但已禁用（避免退出练习场光头）')
            hook_line = '退出练习场→恢复已禁用'
        elif t == 'need_practice_cleanup':
            log('[HOOK] need_practice_cleanup: 已废弃，忽略')
        elif t == 'batch_reset':
            prev_count = p.get('prev_count', '?')
            reason = p.get('reason', '')
            if reason == 'char_switch':
                prev_char = p.get('prev_char', '?')
                new_char = p.get('new_char', '?')
                log(f'[HOOK] 角色切换隔离: c{prev_char}→c{new_char} (清空上一角色 {prev_count} 项收集)')
                hook_line = f'角色切换隔离: c{prev_char}→c{new_char} (清空{prev_count}项)'
            else:
                prev_scan = p.get('prev_scan_done', '?')
                log(f'[HOOK] 批次重置: {reason} prev={prev_count}项 scanDone={prev_scan}')
                hook_line = f'批次重置: {reason} ({prev_count}项)'
        elif t == 'ready':
            log(f'[HOOK] ready collect={p.get("collect")} map={p.get("map")} cmodule={p.get("cmodule")} scene={p.get("scene")}')
        elif t == 'need_practice_dword_scan':
            # 练习场：用 Python 暴力扫描（无 flag 检查）
            # 练习场数据没有 0x00010000 标志，flag 检查会替换 0 个
            # 退出练习场时 need_restore_shop 会恢复非属性表条目
            if replace_map and connected_pid:
                def do_practice_scan():
                    try:
                        r, e = native_brute_scan(connected_pid, replace_map, effect_map_store if effect_map_store else None)
                        log(f'[HOOK] 练习场暴力扫描完成: {r} 替换, {e} 特效')
                    except Exception as ex:
                        log(f'[HOOK] 练习场暴力扫描失败: {ex}')
                threading.Thread(target=do_practice_scan, daemon=True).start()
            else:
                log('[HOOK] 练习场扫描跳过: 无 replace_map 或 pid')
            hook_line = '练习场→Python暴力扫描'
        elif t == 'need_effect_scan':
            log('[HOOK] need_effect_scan 收到！立即用 Windows API 写特效')
            if effect_map_store and connected_pid:
                def do_effect():
                    try:
                        r, e = native_dword_scan(connected_pid, replace_map, effect_map_store)
                        log(f'[HOOK] 特效写入完成: {r} 替换, {e} 特效')
                    except Exception as ex:
                        log(f'[HOOK] 特效写入失败: {ex}')
                threading.Thread(target=do_effect, daemon=True).start()
            else:
                log('[HOOK] 特效写入跳过: 无 effect_map 或 pid')
        elif t == 'debug':
            log(f'[HOOK] debug: {p}')
        elif t == 'anomaly':
            code = p.get('code', 'unknown')
            msg = p.get('msg', '')
            log(f'[异常] [{code}] {msg}')
            hook_line = f'⚠ 异常[{code}]: {msg}'

        # 写入 hook 日志缓冲区
        if hook_line:
            hook_log_buffer.append(hook_line)
            if len(hook_log_buffer) > HOOK_LOG_MAX:
                hook_log_buffer = hook_log_buffer[-HOOK_LOG_MAX:]
    elif msg['type'] == 'error':
        log(f'[HOOK] frida error: {msg.get("description","")}')

def _unload_script():
    """安全卸载 script"""
    global script
    if script:
        try:
            script.unload()
        except:
            pass
        script = None

def _load_script(js_code):
    """安全加载 script"""
    global script
    script = session.create_script(js_code)
    script.on('message', on_message)
    script.load()

def handle_connect():
    global session, script, collected_slots, connected_pid
    log('[CMD] CONNECT')
    pid = find_pid()
    if not pid:
        log('[CMD] CONNECT 失败: FreeStyle.exe not running')
        return {'status': 'error', 'error': 'FreeStyle.exe not running'}

    try:
        _unload_script()
        if session:
            try:
                session.detach()
            except:
                pass

        t0 = time.time()
        session = frida.attach(pid)
        log(f'[CMD] frida.attach 耗时 {time.time()-t0:.2f}s')

        js = create_js({}, collect_mode=True)
        _load_script(js)
        connected_pid = pid
        collected_slots = {}
        collected_ccodes = []
        log(f'[CMD] CONNECT 成功 pid={pid}')
        # 连接后预提交页面，提前触发 page fault
        try:
            script.exports_sync.precommit_pages()
        except Exception as e:
            log(f'[CMD] precommitPages 失败（不影响功能）: {e}')
        return {'status': 'ok', 'pid': pid}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def handle_read_current():
    global collected_slots, script
    if not session:
        return {'status': 'error', 'error': 'not connected'}

    try:
        # 从 JS RPC 获取收集到的穿搭数据
        if script:
            try:
                raw = script.exports_sync.collected()
                js_collected = json.loads(raw) if raw else {}
                # 先清除旧数据，再用 JS 数据替换（避免切换角色后旧数据残留）
                collected_slots = {}
                for slot_str, code in js_collected.items():
                    collected_slots[slot_str] = code
                log(f'[CMD] JS RPC collected: {js_collected}')
            except Exception as e:
                log(f'[CMD] JS RPC collected 失败: {e}')
            try:
                raw_cc = script.exports_sync.collectedCCodes()
                js_ccodes = json.loads(raw_cc) if raw_cc else []
                collected_ccodes = js_ccodes
                log(f'[CMD] JS RPC collectedCCodes: {js_ccodes}')
            except Exception as e:
                log(f'[CMD] JS RPC collectedCCodes 失败: {e}')

        slots = {}
        for slot_str, code in collected_slots.items():
            slots[slot_str] = {
                'code': code,
                'name': itemshop_db.get_name(code),
                'pak': itemshop_db.get_pak(code)
            }
        hint = '请先进一次房间让 sprintf 触发收集，再点刷新' if not slots else ''
        log(f'[CMD] READ_CURRENT 返回 {len(slots)} 个格子')
        return {'status': 'ok', 'slots': slots, 'hint': hint}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def handle_recollect():
    global collected_slots, collected_ccodes, script
    if not session:
        return {'status': 'error', 'error': 'not connected'}

    try:
        collected_slots = {}
        # 不清空 collected_ccodes，角色码跨批次保留
        if script:
            try:
                script.exports_sync.reset_collect()
            except:
                pass
        return {'status': 'ok'}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def handle_replace(new_map, effect_map=None, enable_effect=True):
    global replace_map, effect_map_store, script, connected_pid, memory_scanned
    if not session:
        return {'status': 'error', 'error': 'not connected'}

    try:
        replace_map = {str(k): str(v) for k, v in new_map.items()}
        effect_map_store = {str(k): int(v) for k, v in (effect_map or {}).items()} if effect_map else {}
        memory_scanned = False  # 新脚本加载，重置内存扫描标记
        log(f'[CMD] REPLACE map={replace_map} effect={effect_map_store} enable_effect={enable_effect}')

        t0 = time.time()
        _unload_script()
        js = create_js(replace_map, effect_map=effect_map_store, collect_mode=True, enable_effect=enable_effect)
        _load_script(js)
        log(f'[CMD] JS reload 耗时 {time.time()-t0:.2f}s')

        # replace 后重新预提交页面（_load_script 会重置 JS 状态）
        try:
            script.exports_sync.precommit_pages()
        except Exception:
            pass

        # 不在这里扫描！等 sprintf hook 触发时（进房间）再通过 need_effect_scan 消息触发 Windows API 扫描
        return {'status': 'ok', 'map': replace_map}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def handle_restore():
    global replace_map, effect_map_store, script, connected_pid, memory_scanned
    try:
        # 先保存旧的 replace_map，用于恢复商城数据
        old_map = dict(replace_map)
        old_pid = connected_pid
        was_scanned = memory_scanned
        replace_map = {}
        effect_map_store = {}
        memory_scanned = False  # 重置标记
        _unload_script()
        if session:
            js = create_js({}, collect_mode=True)
            _load_script(js)
        # 只有实际做过内存扫描（bruteScan/dwordScan）时才需要恢复
        # 纯 sprintf 替换不会修改内存中的 ItemCode，不需要恢复
        if old_map and old_pid and was_scanned:
            def do_restore():
                try:
                    r = native_restore_shop(old_pid, old_map)
                    log(f'[CMD] RESTORE 商城恢复: {r} 处 (memory_scanned={was_scanned})')
                except Exception as ex:
                    log(f'[CMD] RESTORE 商城恢复失败: {ex}')
            threading.Thread(target=do_restore, daemon=True).start()
        else:
            log(f'[CMD] RESTORE 跳过内存恢复 (memory_scanned={was_scanned}, has_map={bool(old_map)})')
        return {'status': 'ok'}
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def handle_status():
    return {
        'status': 'ok',
        'connected': session is not None,
        'pid': connected_pid,
        'replace_map': replace_map,
        'collected': len(collected_slots)
    }

def handle_read_charname():
    """读取当前角色名：扫描 FSB_CHN\0 锚点，+0x1C 偏移处读 GBK 字符串"""
    if not connected_pid:
        return {'status': 'error', 'error': 'not connected'}

    try:
        access = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        handle = kernel32.OpenProcess(access, False, connected_pid)
        if not handle:
            return {'status': 'error', 'error': f'OpenProcess failed: {ctypes.get_last_error()}'}

        try:
            anchor = b'FSB_CHN\x00'
            name = None

            # 枚举可读内存区域
            addr = 0
            mbi = MEMORY_BASIC_INFORMATION()
            mbi_size = ctypes.sizeof(mbi)

            while True:
                ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
                if ret == 0:
                    break
                ba = mbi.BaseAddress or 0
                rs = mbi.RegionSize or 0

                if mbi.State == MEM_COMMIT and mbi.Protect in READABLE_PROTECTS and rs < 200 * 1024 * 1024:
                    buf = ctypes.create_string_buffer(rs)
                    rb = ctypes.c_size_t()
                    if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(ba), buf, rs, ctypes.byref(rb)):
                        data = buf.raw[:rb.value]
                        off = 0
                        while True:
                            idx = data.find(anchor, off)
                            if idx < 0:
                                break
                            match_addr = ba + idx
                            # 排除 FSB_CHN.GAMEFRAMEWORK（锚点后紧跟 '.' 而非 '\0'）
                            # anchor 已包含 \0，所以 idx 指向 FSB_CHN\0
                            # 但 FSB_CHN.GAMEFRAMEWORK 中 '.' 在 'N' 之后
                            # anchor 是 FSB_CHN\x00，GAMEFRAMEWORK 版本是 FSB_CHN.
                            # 所以 anchor 本身已经排除了 GAMEFRAMEWORK 版本

                            # 读 +0x1C 处的 GBK 字符串（最长 32 字节）
                            read_start = idx + 0x1C
                            if read_start + 32 <= len(data):
                                name_raw = data[read_start:read_start + 32]
                            else:
                                # 跨区域读取
                                cross_buf = ctypes.create_string_buffer(32)
                                cross_rb = ctypes.c_size_t()
                                read_addr = match_addr + 0x1C
                                if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(read_addr), cross_buf, 32, ctypes.byref(cross_rb)):
                                    name_raw = cross_buf.raw[:cross_rb.value]
                                else:
                                    off = idx + 1
                                    continue

                            null_pos = name_raw.find(b'\x00')
                            if null_pos > 0:
                                name_raw = name_raw[:null_pos]

                            # 验证是有效 GBK 文本（至少 2 字节，不含 '.'）
                            if len(name_raw) >= 2:
                                try:
                                    decoded = name_raw.decode('gbk')
                                    # 简单验证：不含路径字符，可打印
                                    if decoded.isprintable() and '.' not in decoded and len(decoded) >= 2:
                                        name = decoded
                                        log(f'[CHARNAME] found at 0x{match_addr:016X}: {name}')
                                        break
                                except:
                                    pass
                            off = idx + 1

                        if name:
                            break
                addr = ba + rs
                if addr == 0 or addr > 0x7FFFFFFFFFFF:
                    break

            if name:
                return {'status': 'ok', 'name': name}
            else:
                return {'status': 'ok', 'name': '', 'hint': '角色名未找到（可能还在加载中）'}
        finally:
            kernel32.CloseHandle(handle)
    except Exception as e:
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}


def handle_read_charinfo():
    """读取人物名 + 角色名（从 c-code 映射）"""
    # 1. 读取人物名（FSB_CHN 锚点）
    char_result = handle_read_charname()
    player_name = ''
    if char_result.get('status') == 'ok':
        player_name = char_result.get('name', '')

    # 2. 从 collected_ccodes 提取角色名
    char_names = []
    log(f'[CHARINFO] collected_ccodes={collected_ccodes}')
    for code in collected_ccodes:
        code_str = str(code)
        if code_str in _ccode_map:
            char_names.append(_ccode_map[code_str])
    log(f'[CHARINFO] char_names={char_names}')

    # 去重，取最后一个非 _T/_M 结尾的作为主角色名（最新角色）
    char_name = ''
    for n in reversed(char_names):
        if not n.endswith('_T') and not n.endswith('_M'):
            char_name = n
            break
    if not char_name and char_names:
        char_name = char_names[-1]

    # 去掉变身后缀: EX_TMAC → TMAC, L_TMAC → TMAC, HATHOR_T → HATHOR 等
    import re
    char_name = re.sub(r'^(EX_|L_|UL_|CREATOR_|NW_)', '', char_name)
    if char_name.endswith('_T'):
        char_name = char_name[:-2]
    if char_name.endswith('_M'):
        char_name = char_name[:-2]

    # 组合 key: 人物名_角色名
    combo_key = ''
    if player_name and char_name:
        combo_key = f'{player_name}_{char_name}'
    elif player_name:
        combo_key = player_name
    elif char_name:
        combo_key = char_name

    return {
        'status': 'ok',
        'player_name': player_name,
        'char_name': char_name,
        'combo_key': combo_key,
        'ccodes': char_names
    }


def handle_search(keyword):
    results = itemshop_db.search(keyword)
    return {'status': 'ok', 'results': results}

def handle_dword_scan():
    """手动触发 DWORD 扫描（用 Windows API，不阻塞游戏）"""
    if not connected_pid:
        return {'status': 'error', 'error': 'not connected'}
    try:
        r, e = native_dword_scan(connected_pid, replace_map, effect_map_store)
        return {'status': 'ok', 'replaced': r, 'effects': e}
    except Exception as ex:
        traceback.print_exc()
        return {'status': 'error', 'error': str(ex)}

def handle_hook_log(since=0):
    """获取 hook 日志缓冲区中 since 之后的条目"""
    global hook_log_buffer
    if since <= 0:
        lines = hook_log_buffer[:]
    else:
        lines = hook_log_buffer[since:]
    return {'status': 'ok', 'lines': lines, 'total': len(hook_log_buffer)}

def handle_command(data):
    cmd = data.get('cmd', '').upper()
    t0 = time.time()
    log(f'[CMD] >>> {cmd} {data}')
    try:
        if cmd == 'CONNECT':
            result = handle_connect()
        elif cmd == 'LAUNCH_GAME':
            result = handle_launch_game(data.get('game_dir', ''))
        elif cmd == 'READ_CURRENT':
            result = handle_read_current()
        elif cmd == 'RECOLLECT':
            result = handle_recollect()
        elif cmd == 'REPLACE':
            result = handle_replace(data.get('map', {}), effect_map=data.get('effect_map'), enable_effect=data.get('enable_effect', True))
        elif cmd == 'RESTORE':
            result = handle_restore()
        elif cmd == 'STATUS':
            result = handle_status()
        elif cmd == 'SEARCH':
            result = handle_search(data.get('keyword', ''))
        elif cmd == 'DWORD_SCAN':
            result = handle_dword_scan()
        elif cmd == 'HOOK_LOG':
            result = handle_hook_log(data.get('since', 0))
        elif cmd == 'READ_CHARNAME':
            result = handle_read_charname()
        elif cmd == 'READ_CHARINFO':
            result = handle_read_charinfo()
        else:
            result = {'status': 'error', 'error': f'unknown command: {cmd}'}
    except Exception as e:
        traceback.print_exc()
        result = {'status': 'error', 'error': f'{cmd} failed: {e}'}

    log(f'[CMD] <<< {cmd} {time.time()-t0:.2f}s => {result}')
    return result

def client_handler(conn, addr):
    log(f'[CONN] {addr}')
    buf = b''
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                try:
                    data = json.loads(line.decode('utf-8'))
                    result = handle_command(data)
                    conn.sendall((json.dumps(result, ensure_ascii=False) + '\n').encode('utf-8'))
                except json.JSONDecodeError as e:
                    conn.sendall(json.dumps({'status': 'error', 'error': str(e)}).encode() + b'\n')
                except Exception as e:
                    traceback.print_exc()
                    try:
                        conn.sendall(json.dumps({'status': 'error', 'error': str(e)}).encode() + b'\n')
                    except:
                        break
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        conn.close()
        log(f'[DISC] {addr}')

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    log(f'FS v2.0 engine listening on {HOST}:{PORT}')
    try:
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=client_handler, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log('shutting down')
        if session:
            try:
                session.detach()
            except:
                pass
        srv.close()

if __name__ == '__main__':
    main()

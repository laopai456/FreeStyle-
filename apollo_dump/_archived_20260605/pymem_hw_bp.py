# pymem_hw_bp.py
# 方案 B：Pymem + 硬件断点追踪 ItemCode 读取
#
# 策略：
#   1. Pymem 扫描 SRC_IC 地址（安全）
#   2. 用 Windows 调试 API 设硬件断点（DR0-DR3）
#   3. 捕获读取事件，记录调用栈
#
# 前提：sc stop ApolloProtect（否则 DR 被清零）
#
# 参考：
#   - failed_approaches.md §3.1：sc stop 后 HW bp 可用
#   - progress_20260527.md §77：Pymem ReadProcessMemory 成功

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'hwbp_trace_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

# Windows API
kernel32 = ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
DEBUG_PROCESS = 0x00000001
DEBUG_ONLY_THIS_PROCESS = 0x00000002
CREATE_NEW_CONSOLE = 0x00000010

EXCEPTION_DEBUG_EVENT = 1
EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007

# CONTEXT 结构 (x86)
class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", wintypes.DWORD),
        ("Dr0", wintypes.DWORD),
        ("Dr1", wintypes.DWORD),
        ("Dr2", wintypes.DWORD),
        ("Dr3", wintypes.DWORD),
        ("Dr6", wintypes.DWORD),
        ("Dr7", wintypes.DWORD),
        ("FloatSave", wintypes.BYTE * 112),
        ("SegGs", wintypes.DWORD),
        ("SegFs", wintypes.DWORD),
        ("SegEs", wintypes.DWORD),
        ("SegDs", wintypes.DWORD),
        ("Edi", wintypes.DWORD),
        ("Esi", wintypes.DWORD),
        ("Ebx", wintypes.DWORD),
        ("Edx", wintypes.DWORD),
        ("Ecx", wintypes.DWORD),
        ("Eax", wintypes.DWORD),
        ("Ebp", wintypes.DWORD),
        ("Eip", wintypes.DWORD),
        ("SegCs", wintypes.DWORD),
        ("EFlags", wintypes.DWORD),
        ("Esp", wintypes.DWORD),
        ("SegSs", wintypes.DWORD),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", ctypes.c_byte * 96),  # union
    ]

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", wintypes.LPVOID),
        ("ExceptionAddress", wintypes.LPVOID),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", wintypes.ULONG * 15),
    ]

def log(msg):
    ts = time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}'
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def scan_itemcode_pymem(pid, target):
    """用 Pymem 扫描 ItemCode 地址"""
    try:
        import pymem
        import pymem.process

        pm = pymem.Pymem()
        pm.open_process_from_id(pid)

        results = []

        # 扫描游戏主模块
        module = pymem.process.module_from_name(pm.process_handle, "FreeStyle.exe")
        if module:
            # 扫描模块内存
            base = module.lpBaseOfDll
            size = module.SizeOfImage

            log(f'扫描 FreeStyle.exe: base=0x{base:x} size={size//1024}KB')

            # 分块扫描避免超时
            chunk_size = 0x100000  # 1MB
            target_bytes = struct.pack('<I', target)

            for offset in range(0, size, chunk_size):
                chunk_end = min(offset + chunk_size, size)
                try:
                    data = pm.read_bytes(base + offset, chunk_end - offset)
                    # 搜索
                    pos = 0
                    while True:
                        idx = data.find(target_bytes, pos)
                        if idx == -1:
                            break
                        addr = base + offset + idx
                        results.append(addr)
                        pos = idx + 1
                except Exception as e:
                    pass

        # 扫描堆区（用 VirtualQueryEx 枚举所有可读内存）
        log('扫描堆区...')
        import pymem.memory
        addr_val = 0
        target_bytes = struct.pack('<I', target)
        while addr_val < 0x7FFFFFFF:
            try:
                mbi = pymem.memory.virtual_query(pm.process_handle, addr_val)
                if mbi.RegionSize == 0:
                    break
                base = mbi.BaseAddress
                size = mbi.RegionSize
                if mbi.State == 0x1000 and 0x1000 <= size <= 0x1000000:
                    if mbi.Protect & 0x02 or mbi.Protect & 0x04 or mbi.Protect & 0x40:
                        try:
                            data = pm.read_bytes(base, min(size, 0x100000))
                            pos = 0
                            while True:
                                idx = data.find(target_bytes, pos)
                                if idx == -1:
                                    break
                                results.append(base + idx)
                                pos = idx + 1
                                if len(results) > 100:
                                    break
                        except:
                            pass
                addr_val = base + size
                if addr_val <= base:
                    break
            except:
                break
            if len(results) > 100:
                break

        pm.close_process()
        return results

    except ImportError:
        log('Pymem 未安装，尝试用 ctypes 直接扫描...')
        return scan_itemcode_ctypes(pid, target)

def scan_itemcode_ctypes(pid, target):
    """用 ctypes 直接扫描"""
    # 打开进程
    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        log(f'OpenProcess 失败: {kernel32.GetLastError()}')
        return []

    results = []
    target_bytes = struct.pack('<I', target)

    # 枚举内存区域
    addr = 0
    mbi = ctypes.create_string_buffer(28)

    while addr < 0x7FFFFFFF:
        if kernel32.VirtualQueryEx(hProcess, ctypes.c_void_p(addr), mbi, 28) == 0:
            break

        # 解析 MEMORY_BASIC_INFORMATION
        base = struct.unpack_from('I', mbi, 0)[0]
        alloc_base = struct.unpack_from('I', mbi, 4)[0]
        region_size = struct.unpack_from('I', mbi, 12)[0]
        state = struct.unpack_from('I', mbi, 16)[0]
        protect = struct.unpack_from('I', mbi, 20)[0]

        if state == 0x1000 and region_size > 0x1000 and region_size < 0x1000000:  # MEM_COMMIT
            # 可读区域
            if protect & 0x02 or protect & 0x04 or protect & 0x40:  # READ
                try:
                    data = ctypes.create_string_buffer(region_size)
                    bytes_read = wintypes.DWORD()
                    if kernel32.ReadProcessMemory(hProcess, ctypes.c_void_p(base), data, region_size, ctypes.byref(bytes_read)):
                        # 搜索
                        pos = 0
                        while True:
                            idx = data.raw.find(target_bytes, pos)
                            if idx == -1:
                                break
                            results.append(base + idx)
                            pos = idx + 1
                            if len(results) > 50:
                                break
                except:
                    pass

        addr = base + region_size
        if addr <= base:
            break

    kernel32.CloseHandle(hProcess)
    return results

def attach_debugger(pid, watch_addrs):
    """附加调试器并设硬件断点"""
    log(f'附加调试器到 PID {pid}...')

    # 附加
    if not kernel32.DebugActiveProcess(pid):
        err = kernel32.GetLastError()
        log(f'DebugActiveProcess 失败: {err}')
        if err == 5:
            log('权限不足，需要管理员权限')
        elif err == 32:
            log('进程已被其他调试器附加')
        return False

    log('调试器附加成功')

    # 获取线程列表
    import psutil
    proc = psutil.Process(pid)
    threads = proc.threads()
    if threads:
        main_thread = threads[0].id
        log(f'主线程 ID: {main_thread}')
    else:
        log('无法获取线程列表')
        return False

    # 打开线程
    hThread = kernel32.OpenThread(0x1F03FF, False, main_thread)  # THREAD_ALL_ACCESS
    if not hThread:
        log(f'OpenThread 失败: {kernel32.GetLastError()}')
        return False

    # 获取上下文
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS | CONTEXT_FULL

    if not kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'GetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(hThread)
        return False

    log(f'当前 EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x}')
    log(f'DR0=0x{ctx.Dr0:x} DR1=0x{ctx.Dr1:x} DR2=0x{ctx.Dr2:x} DR3=0x{ctx.Dr3:x}')
    log(f'DR6=0x{ctx.Dr6:x} DR7=0x{ctx.Dr7:x}')

    # 设置硬件断点（最多 4 个）
    # DR7 控制位：每 2 位控制一个 DR
    # 类型：00=执行，01=写入，10=未定义，11=读/写
    # 长度：00=1字节，01=2字节，10=未定义，11=4字节

    bp_addrs = watch_addrs[:4]  # 最多 4 个
    dr7 = 0

    for i, addr in enumerate(bp_addrs):
        if i == 0:
            ctx.Dr0 = addr
            dr7 |= (3 << 16)  # DR0: 读/写，4字节
            dr7 |= (3 << 18)  # 长度 4 字节
        elif i == 1:
            ctx.Dr1 = addr
            dr7 |= (3 << 20)
            dr7 |= (3 << 22)
        elif i == 2:
            ctx.Dr2 = addr
            dr7 |= (3 << 24)
            dr7 |= (3 << 26)
        elif i == 3:
            ctx.Dr3 = addr
            dr7 |= (3 << 28)
            dr7 |= (3 << 30)

        dr7 |= (1 << (i * 2))  # 局部启用
        log(f'DR{i} = 0x{addr:x}')

    ctx.Dr7 = dr7
    ctx.Dr6 = 0

    # 设置上下文
    if not kernel32.SetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'SetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(hThread)
        return False

    log(f'DR7 设置为 0x{dr7:x}')
    log('硬件断点设置成功')

    kernel32.CloseHandle(hThread)
    return True

def debug_loop(pid, max_events=100):
    """调试事件循环"""
    log('进入调试循环...')
    log(f'最大事件数: {max_events}')
    log('进房间/练习场触发断点...')
    log('')

    event_count = 0
    exception_count = 0

    while event_count < max_events:
        event = DEBUG_EVENT()
        if not kernel32.WaitForDebugEvent(ctypes.byref(event), 1000):
            continue

        event_count += 1
        code = event.dwDebugEventCode
        tid = event.dwThreadId

        if code == EXCEPTION_DEBUG_EVENT:
            # 解析异常信息
            exc_info = EXCEPTION_DEBUG_INFO.from_buffer_copy(event.u)

            if exc_info.ExceptionCode == EXCEPTION_SINGLE_STEP:
                exception_count += 1

                # 获取线程上下文
                hThread = kernel32.OpenThread(0x1F03FF, False, tid)
                if hThread:
                    ctx = CONTEXT()
                    ctx.ContextFlags = CONTEXT_FULL
                    kernel32.GetThreadContext(hThread, ctypes.byref(ctx))

                    log(f'[HW_BP #{exception_count}] EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x}')
                    log(f'  DR6=0x{ctx.Dr6:x} (触发哪个断点)')

                    # 判断哪个 DR 触发
                    if ctx.Dr6 & 1:
                        log(f'  DR0 触发')
                    if ctx.Dr6 & 2:
                        log(f'  DR1 触发')
                    if ctx.Dr6 & 4:
                        log(f'  DR2 触发')
                    if ctx.Dr6 & 8:
                        log(f'  DR3 触发')

                    # 清除 DR6
                    ctx.Dr6 = 0
                    kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
                    kernel32.CloseHandle(hThread)

                # 继续
                kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

            elif exc_info.ExceptionCode == EXCEPTION_BREAKPOINT:
                log(f'[BP] EIP=0x{exc_info.ExceptionAddress:x}')
                kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

            else:
                log(f'[EXCEPTION] code=0x{exc_info.ExceptionCode:x} addr=0x{exc_info.ExceptionAddress:x}')
                kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_EXCEPTION_NOT_HANDLED)

        elif code == 1:  # CREATE_PROCESS_DEBUG_EVENT
            log(f'[CREATE_PROCESS] PID={event.dwProcessId}')
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

        elif code == 2:  # CREATE_THREAD_DEBUG_EVENT
            log(f'[CREATE_THREAD] TID={tid}')
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

        elif code == 3:  # EXIT_THREAD_DEBUG_EVENT
            log(f'[EXIT_THREAD] TID={tid}')
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

        elif code == 4:  # EXIT_PROCESS_DEBUG_EVENT
            log(f'[EXIT_PROCESS] PID={event.dwProcessId}')
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)
            break

        elif code == 6:  # LOAD_DLL_DEBUG_EVENT
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

        else:
            kernel32.ContinueDebugEvent(event.dwProcessId, tid, DBG_CONTINUE)

        if exception_count >= 20:
            log('捕获 20 次硬件断点，停止调试')
            break

    # 分离
    kernel32.DebugActiveProcessStop(pid)
    log('调试器已分离')

def main():
    global LOG_F

    print('=== Pymem + 硬件断点追踪 ===')
    print(f'SRC_IC: {SRC_IC}  DST_IC: {DST_IC}')
    print('')

    # 检查 Apollo 状态
    import subprocess
    result = subprocess.run(['sc', 'query', 'ApolloProtect'], capture_output=True, text=True)
    if 'RUNNING' in result.stdout:
        print('警告: ApolloProtect 正在运行，硬件断点会被清零')
        print('请先执行: sc stop ApolloProtect')
        print('')
        resp = input('是否继续？(y/n): ')
        if resp.lower() != 'y':
            return
    else:
        print('ApolloProtect 已停止 ✅')

    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Pymem + 硬件断点追踪 === PID:{pid} ===')
    log(f'SRC_IC: {SRC_IC}')
    log(f'日志: {LOG_FILE}')
    log('')

    # 步骤 1：扫描地址
    log('步骤 1：扫描 SRC_IC 地址...')
    addrs = scan_itemcode_pymem(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个地址')

    if len(addrs) == 0:
        log('未找到 SRC_IC 地址，退出')
        return

    # 显示前 10 个
    for i, addr in enumerate(addrs[:10]):
        log(f'  [{i}] 0x{addr:x}')

    # 步骤 2：设硬件断点
    log('')
    log('步骤 2：附加调试器并设硬件断点...')

    watch_addrs = addrs[:4]  # 最多 4 个

    if attach_debugger(pid, watch_addrs):
        log('')
        log('步骤 3：进入调试循环...')
        log('==============================')
        log('')

        debug_loop(pid)

    if LOG_F:
        LOG_F.close()
    print('完成。')

if __name__ == '__main__':
    main()
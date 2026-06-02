# pymem_hw_bp_v2.py
# 方案 B 修复版：在 CREATE_PROCESS 事件后设置硬件断点
#
# 修复：
#   1. 等待 CREATE_PROCESS_DEBUG_EVENT 后再设置断点
#   2. 在异常处理中设置 DR 寄存器
#   3. 正确处理线程上下文

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'hwbp_v2_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

# Windows API
kernel32 = ctypes.windll.kernel32

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
EXCEPTION_DEBUG_EVENT = 1
CREATE_PROCESS_DEBUG_EVENT = 3
CREATE_THREAD_DEBUG_EVENT = 2
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7

EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_ACCESS_VIOLATION = 0xC0000005

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007
CONTEXT_i386 = 0x00010000

# CONTEXT 结构 (x86) - 正确对齐
class CONTEXT(ctypes.Structure):
    _pack_ = 4
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
        ("ExtendedRegisters", wintypes.BYTE * 512),
    ]

# DEBUG_EVENT 结构
class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", wintypes.LPVOID),
        ("ExceptionAddress", wintypes.LPVOID),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", wintypes.ULONG * 15),
    ]

class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("hFile", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("lpBaseOfImage", wintypes.LPVOID),
        ("dwDebugInfoFileOffset", wintypes.DWORD),
        ("nDebugInfoSize", wintypes.DWORD),
        ("lpThreadLocalBase", wintypes.LPVOID),
        ("lpStartAddress", wintypes.LPVOID),
        ("lpImageName", wintypes.LPVOID),
        ("fUnicode", wintypes.WORD),
    ]

class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("hThread", wintypes.HANDLE),
        ("lpThreadLocalBase", wintypes.LPVOID),
        ("lpStartAddress", wintypes.LPVOID),
    ]

class DEBUG_EVENT_UNION(ctypes.Union):
    _pack_ = 4
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("CreateThread", CREATE_THREAD_DEBUG_INFO),
        ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
        ("padding", wintypes.BYTE * 96),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", DEBUG_EVENT_UNION),
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

def scan_itemcode(pid, target):
    """扫描 ItemCode 地址"""
    try:
        import pymem
        import pymem.process
        import pymem.memory

        pm = pymem.Pymem()
        pm.open_process_from_id(pid)
        results = []
        target_bytes = struct.pack('<I', target)

        # 扫描所有可读内存
        addr_val = 0
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
                            data = pm.read_bytes(base, min(size, 0x200000))
                            pos = 0
                            while True:
                                idx = data.find(target_bytes, pos)
                                if idx == -1:
                                    break
                                results.append(base + idx)
                                pos = idx + 1
                                if len(results) > 20:
                                    break
                        except:
                            pass
                addr_val = base + size
                if addr_val <= base:
                    break
            except:
                break

        pm.close_process()
        return results
    except ImportError:
        log('需要安装 pymem: pip install pymem')
        return []

def set_hw_breakpoint(hThread, addrs):
    """在指定线程设置硬件断点"""
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS

    if not kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'GetThreadContext 失败: {kernel32.GetLastError()}')
        return False

    log(f'  当前 EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x}')

    # 设置 DR
    dr7 = 0
    for i, addr in enumerate(addrs[:4]):
        if i == 0:
            ctx.Dr0 = addr
            dr7 |= (3 << 16) | (3 << 18) | 1  # 读/写, 4字节, 启用
        elif i == 1:
            ctx.Dr1 = addr
            dr7 |= (3 << 20) | (3 << 22) | 4
        elif i == 2:
            ctx.Dr2 = addr
            dr7 |= (3 << 24) | (3 << 26) | 16
        elif i == 3:
            ctx.Dr3 = addr
            dr7 |= (3 << 28) | (3 << 30) | 64
        log(f'  DR{i} = 0x{addr:x}')

    ctx.Dr7 = dr7
    ctx.Dr6 = 0

    if not kernel32.SetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'SetThreadContext 失败: {kernel32.GetLastError()}')
        return False

    log(f'  DR7 = 0x{dr7:x}')
    return True

def main():
    global LOG_F

    print('=== Pymem + 硬件断点 v2 ===')
    print(f'SRC_IC: {SRC_IC}')
    print('')

    # 检查 Apollo
    import subprocess
    result = subprocess.run(['sc', 'query', 'ApolloProtect'], capture_output=True, text=True)
    if 'RUNNING' in result.stdout:
        print('警告: ApolloProtect 正在运行')
        print('请先执行: sc stop ApolloProtect')
        return

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 硬件断点 v2 === PID:{pid} ===')

    # 扫描地址
    log('扫描 SRC_IC 地址...')
    addrs = scan_itemcode(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个地址')
    for i, addr in enumerate(addrs[:10]):
        log(f'  [{i}] 0x{addr:x}')

    if len(addrs) == 0:
        log('未找到地址')
        return

    # 附加调试器
    log('')
    log('附加调试器...')
    if not kernel32.DebugActiveProcess(pid):
        log(f'DebugActiveProcess 失败: {kernel32.GetLastError()}')
        return
    log('调试器附加成功')

    # 调试循环
    watch_addrs = addrs[:4]
    bp_set = False
    bp_count = 0
    max_bp = 30

    log('')
    log('进入调试循环...')
    log('===================')
    log('')

    while True:
        event = DEBUG_EVENT()
        if not kernel32.WaitForDebugEvent(ctypes.byref(event), 5000):
            log('WaitForDebugEvent 超时')
            continue

        code = event.dwDebugEventCode
        pid_evt = event.dwProcessId
        tid = event.dwThreadId

        if code == CREATE_PROCESS_DEBUG_EVENT:
            # 在 CREATE_PROCESS 事件后设置断点
            hThread = event.u.CreateProcessInfo.hThread
            log(f'[CREATE_PROCESS] TID={tid}')
            log('设置硬件断点...')
            if set_hw_breakpoint(hThread, watch_addrs):
                bp_set = True
            kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)

        elif code == CREATE_THREAD_DEBUG_EVENT:
            hThread = event.u.CreateThread.hThread
            kernel32.CloseHandle(hThread)
            kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)

        elif code == EXCEPTION_DEBUG_EVENT:
            exc = event.u.Exception
            exc_code = exc.ExceptionCode

            if exc_code == EXCEPTION_SINGLE_STEP:
                bp_count += 1

                # 获取上下文
                hThread = kernel32.OpenThread(0x1F03FF, False, tid)
                if hThread:
                    ctx = CONTEXT()
                    ctx.ContextFlags = CONTEXT_FULL
                    kernel32.GetThreadContext(hThread, ctypes.byref(ctx))

                    log(f'[HW_BP #{bp_count}] EIP=0x{ctx.Eip:x} TID={tid}')
                    log(f'  DR6=0x{ctx.Dr6:x}')

                    # 清除 DR6
                    ctx.Dr6 = 0
                    kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
                    kernel32.CloseHandle(hThread)

                kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)

                if bp_count >= max_bp:
                    log(f'捕获 {max_bp} 次，停止')
                    break

            elif exc_code == EXCEPTION_BREAKPOINT:
                # 系统断点，继续
                kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)

            elif exc_code == EXCEPTION_ACCESS_VIOLATION:
                log(f'[ACCESS_VIOLATION] addr=0x{exc.ExceptionAddress:x}')
                kernel32.ContinueDebugEvent(pid_evt, tid, DBG_EXCEPTION_NOT_HANDLED)

            else:
                log(f'[EXCEPTION] code=0x{exc_code:x}')
                kernel32.ContinueDebugEvent(pid_evt, tid, DBG_EXCEPTION_NOT_HANDLED)

        elif code == EXIT_PROCESS_DEBUG_EVENT:
            log(f'[EXIT_PROCESS]')
            kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)
            break

        else:
            kernel32.ContinueDebugEvent(pid_evt, tid, DBG_CONTINUE)

    # 分离
    kernel32.DebugActiveProcessStop(pid)
    log('调试器已分离')

    if LOG_F:
        LOG_F.close()
    print('完成。')

if __name__ == '__main__':
    main()
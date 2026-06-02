# pymem_hw_bp_v3.py
# 方案 B 修复版 v3：正确处理 DebugActiveProcess
#
# 关键修复：
#   1. DebugActiveProcess 附加后，第一个事件是 EXCEPTION_BREAKPOINT
#   2. 在这个断点处设置硬件断点
#   3. 然后继续执行

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'hwbp_v3_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

kernel32 = ctypes.windll.kernel32

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
THREAD_ALL_ACCESS = 0x1F03FF

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
OUTPUT_DEBUG_STRING_EVENT = 8

EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_ACCESS_VIOLATION = 0xC0000005
EXCEPTION_GUARD_PAGE = 0x80000001

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007

# CONTEXT (x86)
class CONTEXT(ctypes.Structure):
    _pack_ = 16
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

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", wintypes.LPVOID),
        ("ExceptionAddress", wintypes.LPVOID),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", wintypes.ULONG * 15),
    ]

class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hThread", wintypes.HANDLE),
        ("lpThreadLocalBase", wintypes.LPVOID),
        ("lpStartAddress", wintypes.LPVOID),
    ]

class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
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

class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("CreateThread", CREATE_THREAD_DEBUG_INFO),
        ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
        ("raw", wintypes.BYTE * 96),
    ]

class DEBUG_EVENT(ctypes.Structure):
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
        import pymem.memory

        pm = pymem.Pymem()
        pm.open_process_from_id(pid)
        results = []
        target_bytes = struct.pack('<I', target)

        addr_val = 0
        while addr_val < 0x7FFFFFFF:
            try:
                mbi = pymem.memory.virtual_query(pm.process_handle, addr_val)
                if mbi.RegionSize == 0:
                    break
                base = mbi.BaseAddress
                size = mbi.RegionSize
                if mbi.State == 0x1000 and 0x1000 <= size <= 0x2000000:
                    if mbi.Protect & 0x02 or mbi.Protect & 0x04 or mbi.Protect & 0x40:
                        try:
                            data = pm.read_bytes(base, min(size, 0x400000))
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

def set_hw_bp_on_thread(tid, addrs):
    """在指定线程设置硬件断点"""
    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
    if not hThread:
        log(f'  OpenThread({tid}) 失败: {kernel32.GetLastError()}')
        return False

    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS

    if not kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'  GetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(hThread)
        return False

    log(f'  EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x} EAX=0x{ctx.Eax:x}')

    # 清除旧断点
    ctx.Dr0 = 0
    ctx.Dr1 = 0
    ctx.Dr2 = 0
    ctx.Dr3 = 0
    ctx.Dr6 = 0
    ctx.Dr7 = 0

    # 设置新断点
    dr7 = 0
    for i, addr in enumerate(addrs[:4]):
        if i == 0:
            ctx.Dr0 = addr
            dr7 |= (0b11 << 16) | (0b11 << 18) | 1  # 读/写, 4字节, L0=1
        elif i == 1:
            ctx.Dr1 = addr
            dr7 |= (0b11 << 20) | (0b11 << 22) | 4  # L1=1
        elif i == 2:
            ctx.Dr2 = addr
            dr7 |= (0b11 << 24) | (0b11 << 26) | 16  # L2=1
        elif i == 3:
            ctx.Dr3 = addr
            dr7 |= (0b11 << 28) | (0b11 << 30) | 64  # L3=1
        log(f'  DR{i} = 0x{addr:x}')

    ctx.Dr7 = dr7

    if not kernel32.SetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'  SetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(hThread)
        return False

    log(f'  DR7 = 0x{dr7:x} (断点已设置)')

    # 验证
    ctx2 = CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    kernel32.GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'  验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    kernel32.CloseHandle(hThread)
    return True

def main():
    global LOG_F

    print('=== Pymem + 硬件断点 v3 ===')
    print(f'SRC_IC: {SRC_IC}')
    print('')

    # 检查 Apollo
    import subprocess
    result = subprocess.run(['sc', 'query', 'ApolloProtect'], capture_output=True, text=True)
    if 'RUNNING' in result.stdout:
        print('警告: ApolloProtect 正在运行')
        print('请先执行: sc stop ApolloProtect')
        print('')
        resp = input('是否继续？(y/n): ')
        if resp.lower() != 'y':
            return

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 硬件断点 v3 === PID:{pid} ===')

    # 扫描地址
    log('扫描 SRC_IC 地址...')
    addrs = scan_itemcode(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个地址')

    if len(addrs) == 0:
        log('未找到地址')
        return

    for i, addr in enumerate(addrs[:10]):
        log(f'  [{i}] 0x{addr:x}')

    watch_addrs = addrs[:4]

    # 附加调试器
    log('')
    log('附加调试器...')
    if not kernel32.DebugActiveProcess(pid):
        err = kernel32.GetLastError()
        log(f'DebugActiveProcess 失败: {err}')
        if err == 5:
            log('需要管理员权限')
        elif err == 32:
            log('进程已被其他调试器附加')
        return
    log('调试器附加成功')

    # 调试循环
    log('')
    log('进入调试循环...')
    log('===================')
    log('')

    bp_set = False
    bp_count = 0
    max_bp = 30
    first_bp = True
    main_tid = None

    while bp_count < max_bp:
        event = DEBUG_EVENT()
        if not kernel32.WaitForDebugEvent(ctypes.byref(event), 10000):
            log('WaitForDebugEvent 超时 (10s)')
            continue

        code = event.dwDebugEventCode
        evt_pid = event.dwProcessId
        tid = event.dwThreadId

        if code == EXCEPTION_DEBUG_EVENT:
            exc = event.u.Exception
            exc_code = exc.ExceptionCode
            exc_addr = exc.ExceptionAddress

            if exc_code == EXCEPTION_BREAKPOINT:
                if first_bp:
                    # 第一个断点是附加时的系统断点
                    first_bp = False
                    main_tid = tid
                    log(f'[FIRST_BP] TID={tid} addr=0x{exc_addr:x}')
                    log('设置硬件断点...')
                    if set_hw_bp_on_thread(tid, watch_addrs):
                        bp_set = True
                    else:
                        log('设置失败，尝试继续...')
                else:
                    log(f'[BP] TID={tid} addr=0x{exc_addr:x}')

                kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

            elif exc_code == EXCEPTION_SINGLE_STEP:
                bp_count += 1

                # 获取上下文
                hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
                if hThread:
                    ctx = CONTEXT()
                    ctx.ContextFlags = CONTEXT_FULL
                    kernel32.GetThreadContext(hThread, ctypes.byref(ctx))

                    # 判断哪个 DR 触发
                    dr6 = ctx.Dr6
                    dr_triggered = ''
                    if dr6 & 1: dr_triggered = 'DR0'
                    elif dr6 & 2: dr_triggered = 'DR1'
                    elif dr6 & 4: dr_triggered = 'DR2'
                    elif dr6 & 8: dr_triggered = 'DR3'

                    log(f'[HW_BP #{bp_count}] EIP=0x{ctx.Eip:x} {dr_triggered} TID={tid}')

                    # 读取触发地址附近的指令（可选）
                    try:
                        import pymem
                        pm = pymem.Pymem()
                        pm.open_process_from_id(evt_pid)
                        code_bytes = pm.read_bytes(ctx.Eip - 5, 20)
                        log(f'  code: {code_bytes.hex()}')
                        pm.close_process()
                    except:
                        pass

                    # 清除 DR6
                    ctx.Dr6 = 0
                    kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
                    kernel32.CloseHandle(hThread)

                kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

            elif exc_code == EXCEPTION_ACCESS_VIOLATION:
                log(f'[ACCESS_VIOLATION] addr=0x{exc_addr:x}')
                kernel32.ContinueDebugEvent(evt_pid, tid, DBG_EXCEPTION_NOT_HANDLED)

            elif exc_code == EXCEPTION_GUARD_PAGE:
                log(f'[GUARD_PAGE] addr=0x{exc_addr:x}')
                kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

            else:
                log(f'[EXCEPTION] code=0x{exc_code:x} addr=0x{exc_addr:x}')
                # 大多数异常应该继续
                kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

        elif code == CREATE_THREAD_DEBUG_EVENT:
            hThread = event.u.CreateThread.hThread
            kernel32.CloseHandle(hThread)
            kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

        elif code == EXIT_THREAD_DEBUG_EVENT:
            kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

        elif code == EXIT_PROCESS_DEBUG_EVENT:
            log('[EXIT_PROCESS]')
            kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)
            break

        elif code == LOAD_DLL_DEBUG_EVENT:
            kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

        else:
            kernel32.ContinueDebugEvent(evt_pid, tid, DBG_CONTINUE)

    # 分离
    log('')
    kernel32.DebugActiveProcessStop(pid)
    log('调试器已分离')

    if LOG_F:
        LOG_F.close()
    print('完成。')

if __name__ == '__main__':
    main()
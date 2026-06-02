# test_ntdll_setcontext.py
# 快速测试：绕过 Apollo hook Wow64SetThreadContext
#
# 方向 1: ntdll.NtSetContextThread (32位 ntdll)
# 方向 2: ntdll.NtSetInformationThread (未文档化)

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'ntdll_test_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

kernel32 = ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
THREAD_ALL_ACCESS = 0x1F03FF

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007

# WOW64_CONTEXT (32位)
class WOW64_CONTEXT(ctypes.Structure):
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

# NTSTATUS
NTSTATUS = wintypes.LONG

# NtSetContextThread 函数签名
NtSetContextThread = ntdll.NtSetContextThread
NtSetContextThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(WOW64_CONTEXT)]
NtSetContextThread.restype = NTSTATUS

# ThreadInfoClass (未文档化)
ThreadWow64Context = 0x2F  # 可能的值，需要测试

# NtSetInformationThread
class THREAD_WOW64_CONTEXT_INFO(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("ContextFlags", wintypes.DWORD),
        ("Dr0", wintypes.DWORD),
        ("Dr1", wintypes.DWORD),
        ("Dr2", wintypes.DWORD),
        ("Dr3", wintypes.DWORD),
        ("Dr6", wintypes.DWORD),
        ("Dr7", wintypes.DWORD),
    ]

NtSetInformationThread = ntdll.NtSetInformationThread
NtSetInformationThread.argtypes = [
    wintypes.HANDLE,  # ThreadHandle
    wintypes.DWORD,   # ThreadInformationClass
    wintypes.LPVOID,  # ThreadInformation
    wintypes.ULONG    # ThreadInformationLength
]
NtSetInformationThread.restype = NTSTATUS

# Wow64 函数（对比用）
Wow64GetThreadContext = kernel32.Wow64GetThreadContext
Wow64GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(WOW64_CONTEXT)]
Wow64GetThreadContext.restype = wintypes.BOOL

Wow64SetThreadContext = kernel32.Wow64SetThreadContext
Wow64SetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(WOW64_CONTEXT)]
Wow64SetThreadContext.restype = wintypes.BOOL

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
                                if len(results) > 10:
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
        log('需要 pymem')
        return []

def test_wow64_setcontext(hThread, addrs):
    """测试 Wow64SetThreadContext（已知失败，作为对照）"""
    log('  [对照] Wow64SetThreadContext...')

    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx))

    ctx.Dr0 = addrs[0]
    ctx.Dr7 = 0xFFFF0055

    ret = Wow64SetThreadContext(hThread, ctypes.byref(ctx))
    log(f'    返回: {ret}')

    # 验证
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'    验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    return ctx2.Dr0 == addrs[0]

def test_nt_setcontext(hThread, addrs):
    """测试 ntdll.NtSetContextThread"""
    log('  [方向1] NtSetContextThread...')

    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx))

    ctx.Dr0 = addrs[0]
    ctx.Dr7 = 0xFFFF0055

    status = NtSetContextThread(hThread, ctypes.byref(ctx))
    log(f'    NTSTATUS: 0x{status:x}')

    # 验证
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'    验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    return ctx2.Dr0 == addrs[0]

def test_nt_setinfo(hThread, addrs):
    """测试 ntdll.NtSetInformationThread"""
    log('  [方向2] NtSetInformationThread(ThreadWow64Context)...')

    # 构造最小化的上下文信息
    info = THREAD_WOW64_CONTEXT_INFO()
    info.ContextFlags = CONTEXT_DEBUG_REGISTERS
    info.Dr0 = addrs[0]
    info.Dr7 = 0xFFFF0055

    # ThreadWow64Context = 0x2F (猜测值)
    for class_val in [0x2F, 0x30, 0x31, 0x20, 0x21]:
        status = NtSetInformationThread(hThread, class_val, ctypes.byref(info), ctypes.sizeof(info))
        log(f'    Class=0x{class_val:x} NTSTATUS=0x{status:x}')
        if status == 0:  # STATUS_SUCCESS
            break

    # 验证
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'    验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    return ctx2.Dr0 == addrs[0]

def main():
    global LOG_F

    print('=== NtDll 绕过测试 ===')
    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== NtDll 测试 === PID:{pid} ===')

    # 扫描地址
    log('扫描 ItemCode...')
    addrs = scan_itemcode(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个')
    if not addrs:
        log('未找到')
        return

    # 获取线程
    import psutil
    proc = psutil.Process(pid)
    threads = proc.threads()
    log(f'线程数: {len(threads)}')

    # 测试第一个线程
    tid = threads[0].id
    log(f'测试线程 {tid}')

    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
    if not hThread:
        log(f'OpenThread 失败: {kernel32.GetLastError()}')
        return

    log(f'句柄: 0x{hThread:x}')

    # 暂停
    kernel32.SuspendThread(hThread)
    log('线程已暂停')

    # 获取当前状态
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx))
    log(f'当前: EIP=0x{ctx.Eip:x} DR0=0x{ctx.Dr0:x}')

    log('')
    log('========== 开始测试 ==========')
    log('')

    # 测试 1: Wow64SetThreadContext（已知失败）
    result1 = test_wow64_setcontext(hThread, addrs)
    log(f'  结果: {"成功" if result1 else "失败"}')

    log('')

    # 测试 2: NtSetContextThread
    result2 = test_nt_setcontext(hThread, addrs)
    log(f'  结果: {"成功 ✅" if result2 else "失败"}')

    log('')

    # 测试 3: NtSetInformationThread
    result3 = test_nt_setinfo(hThread, addrs)
    log(f'  结果: {"成功 ✅" if result3 else "失败"}')

    log('')
    log('========== 测试完成 ==========')

    # 恢复
    kernel32.ResumeThread(hThread)
    kernel32.CloseHandle(hThread)

    if LOG_F:
        LOG_F.close()
    print('')
    print('完成。')

if __name__ == '__main__':
    main()
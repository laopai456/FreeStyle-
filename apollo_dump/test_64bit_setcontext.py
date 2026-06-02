# test_64bit_setcontext.py
# 方向 1：从 64 位进程设置 32 位线程的硬件断点
#
# 原理：
#   - Apollo hook 驻留在 FreeStyle.exe (32位) 地址空间
#   - 64 位进程调 kernel32.Wow64SetThreadContext → 走 64 位 ntdll → 直接进内核
#   - 完全不经过 32 位进程的用户态地址空间，Apollo hook 无法拦截
#
# 注意：必须用 64 位 Python 运行

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'bit64_test_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

kernel32 = ctypes.windll.kernel32

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
THREAD_ALL_ACCESS = 0x1F03FF

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007

# WOW64_CONTEXT — 32 位上下文结构
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

# 64 位 kernel32.Wow64SetThreadContext
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

def main():
    global LOG_F

    # 检查是否 64 位 Python
    is_64bit = struct.calcsize("P") == 8

    print('=== 64 位进程 → WoW64 硬件断点 ===')
    print(f'Python 位宽: {"64位 ✅" if is_64bit else "32位 ❌"}')
    print(f'Python: {sys.executable}')
    print('')

    if not is_64bit:
        print('错误: 必须用 64 位 Python')
        print('尝试: py -3 test_64bit_setcontext.py')
        return

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 64位测试 === PID:{pid} ===')

    # 扫描地址
    log('扫描 ItemCode...')
    addrs = scan_itemcode(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个')
    if not addrs:
        log('未找到')
        return
    for i, a in enumerate(addrs[:5]):
        log(f'  [{i}] 0x{a:x}')

    # 获取线程
    import psutil
    proc = psutil.Process(pid)
    threads = proc.threads()
    log(f'线程数: {len(threads)}')

    tid = threads[0].id
    log(f'')
    log(f'测试线程 TID={tid}')

    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
    if not hThread:
        log(f'OpenThread 失败: {kernel32.GetLastError()}')
        return

    log(f'句柄: 0x{hThread:x}')

    # 暂停
    sc = kernel32.SuspendThread(hThread)
    log(f'线程已暂停 (suspend={sc})')

    # 读当前上下文
    log('')
    log('===== 步骤1: 读当前上下文 =====')
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS

    if not Wow64GetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'Wow64GetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.ResumeThread(hThread)
        kernel32.CloseHandle(hThread)
        return

    log(f'当前: EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x}')
    log(f'当前 DR: DR0=0x{ctx.Dr0:x} DR7=0x{ctx.Dr7:x}')

    # 设置 DR
    log('')
    log('===== 步骤2: 设置 DR =====')
    ctx.Dr0 = addrs[0]
    ctx.Dr1 = addrs[1] if len(addrs) > 1 else 0
    ctx.Dr2 = addrs[2] if len(addrs) > 2 else 0
    ctx.Dr3 = addrs[3] if len(addrs) > 3 else 0
    ctx.Dr6 = 0

    dr7 = 0
    for i in range(min(len(addrs), 4)):
        dr7 |= (1 << (i * 2))
        dr7 |= (3 << (16 + i * 4))
        dr7 |= (3 << (18 + i * 4))
    ctx.Dr7 = dr7

    log(f'设置: DR0=0x{ctx.Dr0:x} DR7=0x{ctx.Dr7:x}')

    # 关键：从 64 位进程调用
    log('')
    log('===== 步骤3: Wow64SetThreadContext (从64位进程!) =====')

    ret = Wow64SetThreadContext(hThread, ctypes.byref(ctx))
    log(f'返回: {ret}')

    # 验证
    log('')
    log('===== 步骤4: 验证 =====')
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    if ctx2.Dr0 == addrs[0]:
        log('')
        log('✅ 成功！硬件断点已设置')
    else:
        log('')
        log('❌ 失败，DR 未被修改')

    # 恢复
    kernel32.ResumeThread(hThread)
    kernel32.CloseHandle(hThread)

    if LOG_F:
        LOG_F.close()
    print('')
    print('完成。')

if __name__ == '__main__':
    main()
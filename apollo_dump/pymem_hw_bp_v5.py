# pymem_hw_bp_v5.py
# 方案 B 修复版 v5：使用 WoW64 API 设置 32 位线程的硬件断点
#
# 关键修复：
#   FreeStyle.exe 是 32 位程序，在 64 位 Windows 上运行
#   普通 GetThreadContext 返回 64 位上下文（全零）
#   需要用 Wow64GetThreadContext 获取 32 位上下文

import sys
import os
import time
import ctypes
from ctypes import wintypes
import struct

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'hwbp_v5_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461

kernel32 = ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
THREAD_ALL_ACCESS = 0x1F03FF
THREAD_GET_CONTEXT = 0x0008
THREAD_SET_CONTEXT = 0x0010
THREAD_SUSPEND_RESUME = 0x0002

CONTEXT_DEBUG_REGISTERS = 0x00010000
CONTEXT_FULL = 0x00010007
CONTEXT_i486 = 0x00010000

# WOW64_CONTEXT 结构 (32 位上下文)
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

# WoW64 函数签名 (kernel32, 不是 ntdll!)
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

def set_hw_bp_wow64(pid, tid, addrs):
    """使用 WoW64 API 设置 32 位线程的硬件断点"""
    # 打开线程
    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
    if not hThread:
        log(f'OpenThread({tid}) 失败: {kernel32.GetLastError()}')
        return False

    log(f'打开线程 {tid} 句柄=0x{hThread:x}')

    # 暂停线程
    suspend_count = kernel32.SuspendThread(hThread)
    if suspend_count == 0xFFFFFFFF:
        log(f'SuspendThread 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(hThread)
        return False
    log(f'线程已暂停 (suspend_count={suspend_count})')

    # 获取 32 位上下文
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS

    if not Wow64GetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'Wow64GetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.ResumeThread(hThread)
        kernel32.CloseHandle(hThread)
        return False

    log(f'当前状态: EIP=0x{ctx.Eip:x} ESP=0x{ctx.Esp:x}')
    log(f'当前 DR: DR0=0x{ctx.Dr0:x} DR7=0x{ctx.Dr7:x}')

    # 设置硬件断点
    ctx.Dr0 = addrs[0] if len(addrs) > 0 else 0
    ctx.Dr1 = addrs[1] if len(addrs) > 1 else 0
    ctx.Dr2 = addrs[2] if len(addrs) > 2 else 0
    ctx.Dr3 = addrs[3] if len(addrs) > 3 else 0
    ctx.Dr6 = 0

    # DR7: 启用 4 个断点，类型=读/写，长度=4字节
    dr7 = 0
    for i in range(min(len(addrs), 4)):
        # L(i) = 1 (局部启用)
        dr7 |= (1 << (i * 2))
        # R/W(i) = 11 (读/写) - 位于 bit 16+ i*4
        dr7 |= (3 << (16 + i * 4))
        # LEN(i) = 11 (4字节) - 位于 bit 18+ i*4
        dr7 |= (3 << (18 + i * 4))

    ctx.Dr7 = dr7

    log(f'设置: DR0=0x{ctx.Dr0:x} DR1=0x{ctx.Dr1:x}')
    log(f'      DR2=0x{ctx.Dr2:x} DR3=0x{ctx.Dr3:x}')
    log(f'      DR7=0x{dr7:x}')

    # 设置上下文
    if not Wow64SetThreadContext(hThread, ctypes.byref(ctx)):
        log(f'Wow64SetThreadContext 失败: {kernel32.GetLastError()}')
        kernel32.ResumeThread(hThread)
        kernel32.CloseHandle(hThread)
        return False

    # 验证
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_DEBUG_REGISTERS
    Wow64GetThreadContext(hThread, ctypes.byref(ctx2))
    log(f'验证: DR0=0x{ctx2.Dr0:x} DR7=0x{ctx2.Dr7:x}')

    # 恢复线程
    kernel32.ResumeThread(hThread)
    log('线程已恢复')

    kernel32.CloseHandle(hThread)
    return ctx2.Dr7 == dr7 and ctx2.Dr0 == addrs[0]

def main():
    global LOG_F

    print('=== 硬件断点 v5 (WoW64) ===')
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
    else:
        print('ApolloProtect 已停止 ✅')

    print('')

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== 硬件断点 v5 (WoW64) === PID:{pid} ===')

    # 扫描地址
    log('扫描 SRC_IC 地址...')
    addrs = scan_itemcode(pid, SRC_IC)
    log(f'找到 {len(addrs)} 个地址')

    if len(addrs) == 0:
        log('未找到地址')
        return

    for i, addr in enumerate(addrs[:10]):
        log(f'  [{i}] 0x{addr:x}')

    # 获取线程列表
    import psutil
    proc = psutil.Process(pid)
    threads = proc.threads()
    if not threads:
        log('无法获取线程列表')
        return

    log(f'进程有 {len(threads)} 个线程')

    # 尝试设置每个线程
    success = False
    success_tids = []

    for t in threads[:10]:  # 尝试前 10 个线程
        tid = t.id
        log('')
        log(f'尝试线程 {tid}...')
        if set_hw_bp_wow64(pid, tid, addrs[:4]):
            success = True
            success_tids.append(tid)
            log(f'✅ 线程 {tid} 设置成功')
            # 不 break，继续设置其他线程
        else:
            log(f'❌ 线程 {tid} 设置失败')

    if success_tids:
        log('')
        log('===================')
        log(f'成功设置的线程: {success_tids}')
        log('硬件断点已设置')
        log('')
        log('断点触发时会产生 EXCEPTION_SINGLE_STEP')
        log('由于没有调试器，异常会被游戏处理')
        log('')
        log('下一步：')
        log('1. 进房间/练习场观察游戏是否正常')
        log('2. 如果崩溃，记录崩溃地址')
        log('3. 或者用 x32dbg 附加捕获异常')
    else:
        log('所有线程都设置失败')

    if LOG_F:
        LOG_F.close()
    print('')
    print('完成。')

if __name__ == '__main__':
    main()
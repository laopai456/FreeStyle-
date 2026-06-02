# trace_actors_dr.py — 用 Pymem SetThreadContext 设置硬件断点 (DR0/DR1)
# 不写代码段，不触发 CRC 检测
#
# 原理:
#   DR0 = DDynamicActor 构造函数地址 (0x0229AE80)
#   DR1 = DStaticActor 构造函数地址 (0x024C5520)
#   DR7 = 启用 DR0/DR1 为执行断点
#   当断点命中时，读 EIP 和栈回溯
#
# 限制: 硬件断点只有 4 个 (DR0-DR3)，且需要线程在断点处暂停
# 本脚本用单线程轮询方式: 挂起→检查EIP→恢复

import pymem
import pymem.process
import struct
import time
import sys

BASE = 0x400000
DD_CTOR = 0x0229AE80  # DDynamicActor 构造函数
DS_CTOR = 0x024C5520  # DStaticActor 构造函数

# DR7 位定义:
# DR7[0] = L0 (DR0 local enable)
# DR7[1] = G0 (DR0 global enable)
# DR7[2] = L1 (DR1 local enable)
# DR7[3] = G1 (DR1 global enable)
# DR7[16:17] = R/W0 (00=exec, 01=write, 10=io, 11=rw)
# DR7[18:19] = Len0 (00=1byte, 01=2byte, 11=4byte)
# DR7[20:21] = R/W1
# DR7[22:23] = Len1
# 我们需要: DR0=exec, DR1=exec, 都 1 byte
# DR7 = 0x00000001 | 0x00000004 | (0b00 << 16) | (0b00 << 20) = 0x00000005
# 不对，R/W0 bits [17:16] = 00 for execute, Len0 bits [19:18] = 00 for 1 byte
# DR7 = bit0 (L0) | bit2 (L1) = 0x05
DR7_VAL = 0x00000005


def get_thread_list(pm, pid):
    """用 Windows API 枚举进程线程"""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    THREAD_QUERY_INFORMATION = 0x0040
    THREAD_SUSPEND_RESUME = 0x0002
    THREAD_GET_CONTEXT = 0x0008
    THREAD_SET_CONTEXT = 0x0010

    # 用 CreateToolhelp32Snapshot
    TH32CS_SNAPTHREAD = 0x00000004

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ('dwSize', wintypes.DWORD),
            ('cntUsage', wintypes.DWORD),
            ('th32ThreadID', wintypes.DWORD),
            ('th32OwnerProcessID', wintypes.DWORD),
            ('dwBasePri', wintypes.LONG),
            ('dwDeltaPri', wintypes.LONG),
            ('dwFlags', wintypes.DWORD),
        ]

    h = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if h == -1:
        return []

    te = THREADENTRY32()
    te.dwSize = ctypes.sizeof(THREADENTRY32)

    threads = []
    if kernel32.Thread32First(h, ctypes.byref(te)):
        while True:
            if te.th32OwnerProcessID == pid:
                threads.append(te.th32ThreadID)
            te.dwSize = ctypes.sizeof(THREADENTRY32)
            if not kernel32.Thread32Next(h, ctypes.byref(te)):
                break

    kernel32.CloseHandle(h)
    return threads


def setup_dr_breakpoint(tid, dr0, dr1):
    """在指定线程上设置 DR0/DR1 硬件断点"""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    THREAD_SUSPEND_RESUME = 0x0002
    THREAD_GET_CONTEXT = 0x0008
    THREAD_SET_CONTEXT = 0x0010
    CONTEXT_DEBUG_REGISTERS = 0x00010000

    # 打开线程
    ACCESS = THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT
    h = kernel32.OpenThread(ACCESS, False, tid)
    if not h:
        return False

    try:
        # 挂起
        kernel32.SuspendThread(h)

        # CONTEXT 结构 (x86)
        class CONTEXT(ctypes.Structure):
            _fields_ = [
                ('ContextFlags', wintypes.DWORD),
                ('Dr0', wintypes.DWORD),
                ('Dr1', wintypes.DWORD),
                ('Dr2', wintypes.DWORD),
                ('Dr3', wintypes.DWORD),
                ('Dr6', wintypes.DWORD),
                ('Dr7', wintypes.DWORD),
                ('FloatSave', ctypes.c_byte * 112),
                ('SegGs', wintypes.DWORD),
                ('SegFs', wintypes.DWORD),
                ('SegEs', wintypes.DWORD),
                ('SegDs', wintypes.DWORD),
                ('Edi', wintypes.DWORD),
                ('Esi', wintypes.DWORD),
                ('Ebx', wintypes.DWORD),
                ('Edx', wintypes.DWORD),
                ('Ecx', wintypes.DWORD),
                ('Eax', wintypes.DWORD),
                ('Ebp', wintypes.DWORD),
                ('Eip', wintypes.DWORD),
                ('SegCs', wintypes.DWORD),
                ('EFlags', wintypes.DWORD),
                ('Esp', wintypes.DWORD),
                ('SegSs', wintypes.DWORD),
            ]

        ctx = CONTEXT()
        ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS | 0x07  # CONTROL | INTEGER | SEGMENTS

        if not kernel32.GetThreadContext(h, ctypes.byref(ctx)):
            kernel32.ResumeThread(h)
            return False

        # 设置 DR0, DR1, DR7
        ctx.Dr0 = dr0
        ctx.Dr1 = dr1
        ctx.Dr7 = DR7_VAL
        ctx.Dr6 = 0
        ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS | 0x07

        if not kernel32.SetThreadContext(h, ctypes.byref(ctx)):
            kernel32.ResumeThread(h)
            return False

        # 恢复
        kernel32.ResumeThread(h)
        return True
    finally:
        kernel32.CloseHandle(h)


def read_stack(pm, esp, count=16):
    """读栈内容"""
    import ctypes
    result = []
    for i in range(count):
        try:
            val = pm.read_int(esp + i * 4)
            result.append(val)
        except:
            result.append(0)
    return result


def main():
    import subprocess

    # 找 PID
    pid = None
    try:
        result = subprocess.run(
            ['tasklist.exe', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                pid = int(line.split(',')[1].strip('"'))
    except:
        pass

    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    # 获取线程列表
    threads = get_thread_list(None, pid)
    print(f'[*] Found {len(threads)} threads')

    # 在所有线程上设置硬件断点
    ok = 0
    for tid in threads:
        if setup_dr_breakpoint(tid, DD_CTOR, DS_CTOR):
            ok += 1
    print(f'[*] DR breakpoints set on {ok}/{len(threads)} threads')
    print(f'    DR0 = 0x{DD_CTOR:08X} (DDynamicActor ctor)')
    print(f'    DR1 = 0x{DS_CTOR:08X} (DStaticActor ctor)')
    print(f'[*] 硬件断点已设置，不修改代码段')
    print(f'[*] 现在需要用调试器捕获断点，或...')
    print()
    print(f'[!] 注意: 硬件断点需要调试器才能捕获 (SingleStep exception)')
    print(f'    Pymem 无法接收异常，需要另一个方案')
    print()
    print(f'替代方案: 用 Pymem 轮询扫描对象创建')
    print(f'  - 周期性扫描 DDynamicActor vtable (0x0284A9EC) 在堆中的出现')
    print(f'  - 找到新对象后，记录地址和时间')
    print(f'  - 配合 ItemCode 变化推断创建点')


if __name__ == '__main__':
    main()

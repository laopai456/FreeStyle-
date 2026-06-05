# hwbp_driver_client.py
# 硬件断点内核驱动控制脚本
#
# 用法:
#   python hwbp_driver_client.py          # 交互模式
#   python hwbp_driver_client.py scan     # 扫描 ItemCode 地址
#   python hwbp_driver_client.py trace    # 设置断点并监控

import ctypes
from ctypes import wintypes

import struct
import sys
import os
import time

sys.stdout.reconfigure(encoding='utf-8')

kernel32 = ctypes.windll.kernel32

DRIVER_PATH = r"\\.\HwBpDriver"
SRC_IC = 50125461
DST_IC = 50125711

# IOCTL codes
IOCTL_SET_BP = (0x22 << 16) | (0x800 << 2)   # CTL_CODE: METHOD_BUFFERED
IOCTL_GET_HIT = (0x22 << 16) | (0x801 << 2)
IOCTL_CLEAR_BP = (0x22 << 16) | (0x802 << 2)
IOCTL_GET_STATE = (0x22 << 16) | (0x803 << 2)
IOCTL_LIST_THREADS = (0x22 << 16) | (0x804 << 2)
IOCTL_DETACH = (0x22 << 16) | (0x805 << 2)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

class SET_BP_REQUEST(ctypes.Structure):
    _fields_ = [
        ("ProcessId", wintypes.ULONG),
        ("ThreadId", wintypes.ULONG),
        ("Address", ctypes.c_uint64),
        ("Type", wintypes.ULONG),
        ("Length", wintypes.ULONG),
        ("DrIndex", wintypes.ULONG),
    ]

class BP_HIT_INFO(ctypes.Structure):
    _fields_ = [
        ("HitCount", wintypes.ULONG),
        ("TriggerAddress", ctypes.c_uint64),
        ("HitAddress", ctypes.c_uint64),
        ("DrIndex", wintypes.ULONG),
        ("Timestamp", ctypes.c_uint64),
        ("ThreadId", wintypes.ULONG),
        ("Rax", ctypes.c_uint64),
        ("Rbx", ctypes.c_uint64),
        ("Rcx", ctypes.c_uint64),
        ("Rdx", ctypes.c_uint64),
        ("Rbp", ctypes.c_uint64),
        ("Rsp", ctypes.c_uint64),
        ("Rsi", ctypes.c_uint64),
        ("Rdi", ctypes.c_uint64),
        ("R8", ctypes.c_uint64),
        ("R9", ctypes.c_uint64),
    ]

class HwBpDriverClient:
    def __init__(self):
        self.handle = None

    def open(self):
        self.handle = kernel32.CreateFileW(
            DRIVER_PATH,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )
        if self.handle == -1 or self.handle is None:
            err = kernel32.GetLastError()
            raise OSError(f"无法打开驱动设备 ({DRIVER_PATH}), 错误: {err}")
        return self

    def close(self):
        if self.handle and self.handle != -1:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *args):
        self.close()

    def _ioctl(self, code, in_buf=None, out_buf=None):
        if in_buf is not None:
            in_ptr = ctypes.byref(in_buf)
            in_size = ctypes.sizeof(in_buf)
        else:
            in_ptr = None
            in_size = 0

        if out_buf is not None:
            out_ptr = ctypes.byref(out_buf)
            out_size = ctypes.sizeof(out_buf)
        else:
            out_ptr = None
            out_size = 0

        bytes_returned = wintypes.DWORD()
        result = kernel32.DeviceIoControl(
            self.handle, code,
            in_ptr, in_size,
            out_ptr, out_size,
            ctypes.byref(bytes_returned),
            None
        )
        if not result:
            err = kernel32.GetLastError()
            raise OSError(f"DeviceIoControl 失败, 错误: {err}")
        return bytes_returned.value

    def set_breakpoint(self, pid, addr, dr_index=0, bp_type=2, length=4, tid=0):
        req = SET_BP_REQUEST()
        req.ProcessId = pid
        req.ThreadId = tid
        req.Address = addr
        req.Type = bp_type
        req.Length = length
        req.DrIndex = dr_index
        self._ioctl(IOCTL_SET_BP, req)
        return True

    def get_hit_info(self, index=0):
        info = BP_HIT_INFO()
        index_buf = ctypes.c_ulong(index)
        try:
            self._ioctl(IOCTL_GET_HIT, index_buf, info)
        except OSError as e:
            if 'NO_MORE_ENTRIES' in str(e) or '259' in str(e):
                return None
            raise
        return info

    def clear_breakpoint(self):
        self._ioctl(IOCTL_CLEAR_BP)
        return True

    def get_state(self):
        state_buf = (ctypes.c_ulong * 3)()
        self._ioctl(IOCTL_GET_STATE, out_buf=state_buf)
        return {
            'active_bps': state_buf[0],
            'hit_count': state_buf[1],
            'thread_count': state_buf[2]
        }

    def list_threads(self, pid):
        MAX = 64
        out_buf = (ctypes.c_ulong * MAX)()
        in_buf = ctypes.c_ulong(pid)
        bytes_returned = wintypes.DWORD()

        result = kernel32.DeviceIoControl(
            self.handle, IOCTL_LIST_THREADS,
            ctypes.byref(in_buf), 4,
            ctypes.byref(out_buf), MAX * 4,
            ctypes.byref(bytes_returned),
            None
        )
        if not result:
            return []
        count = bytes_returned.value // 4
        return [out_buf[i] for i in range(count)]

    def detach(self):
        self._ioctl(IOCTL_DETACH)
        return True


def find_freestyle_pid():
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
                return p.info['pid']
    except ImportError:
        import subprocess
        r = subprocess.run(['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    return None


def scan_itemcode_addresses(pid, target=SRC_IC):
    """扫描进程内存中的 ItemCode 地址。需要可读的进程句柄。"""
    try:
        import pymem
        import pymem.memory

        pm = pymem.Pymem()
        pm.open_process_from_id(pid)
        results = []
        target_bytes = struct.pack('<I', target)

        try:
            mbi = pymem.memory.virtual_query(pm.process_handle, 0x400000)
        except:
            pm.close_process()
            return []

        try:
            for base in range(0x400000, 0x7FFFFFFF, 0x10000):
                try:
                    mbi = pymem.memory.virtual_query(pm.process_handle, base)
                    if mbi.State == 0x1000 and mbi.Protect & 0x04:
                        if 0x1000 <= mbi.RegionSize <= 0x400000:
                            data = pm.read_bytes(mbi.BaseAddress, min(mbi.RegionSize, 0x400000))
                            pos = 0
                            while True:
                                idx = data.find(target_bytes, pos)
                                if idx == -1:
                                    break
                                results.append(mbi.BaseAddress + idx)
                                pos = idx + 1
                                if len(results) > 15:
                                    break
                except:
                    pass
        except:
            pass

        pm.close_process()
        return results
    except ImportError:
        return []


def format_hit(info):
    if info is None:
        return "N/A"
    return (f"#{info.HitCount:3d} | EIP=0x{info.TriggerAddress:08x} "
            f"| HitAddr=0x{info.HitAddress:08x} "
            f"| DR{info.DrIndex} "
            f"| TID={info.ThreadId} "
            f"| ECX=0x{info.Rcx:08x} EDX=0x{info.Rdx:08x}")


def cmd_scan(args):
    """扫描 ItemCode 地址"""
    pid = find_freestyle_pid()
    if not pid:
        print("[错误] FreeStyle.exe 未运行")
        return

    ic = int(args[0]) if args else SRC_IC
    print(f"[扫描] PID={pid}, ItemCode={ic}")
    addrs = scan_itemcode_addresses(pid, ic)
    if addrs:
        print(f"找到 {len(addrs)} 个地址:")
        for i, a in enumerate(addrs):
            print(f"  [{i}] 0x{a:08x}")
    else:
        print("未找到地址（可能需要内核驱动来读取内存）")


def cmd_trace(args):
    """设置硬件断点并监控"""
    pid = find_freestyle_pid()
    if not pid:
        print("[错误] FreeStyle.exe 未运行")
        return

    ic = int(args[0]) if args else SRC_IC
    print(f"[追踪] PID={pid}, ItemCode={ic}")

    # 扫描地址（尝试用户态，失败则跳过）
    addrs = scan_itemcode_addresses(pid, ic)
    if not addrs:
        print("[警告] 用户态内存扫描失败，请手动指定地址")
        if len(args) < 2:
            print("用法: trace <ItemCode> <地址1> [地址2] ...")
            return
        addrs = [int(a, 16) if a.startswith('0x') else int(a) for a in args[1:]]

    print(f"目标地址: {[f'0x{a:08x}' for a in addrs[:4]]}")

    try:
        client = HwBpDriverClient().open()
    except OSError as e:
        print(f"[错误] {e}")
        print("请先加载驱动: sc start HwBpDriver")
        return

    try:
        # 设置断点
        for i, addr in enumerate(addrs[:4]):
            try:
                client.set_breakpoint(pid, addr, dr_index=i, bp_type=2, length=4)
                print(f"[设置] DR{i} = 0x{addr:08x} (access) ✓")
            except OSError as e:
                print(f"[设置] DR{i} = 0x{addr:08x} 失败: {e}")

        state = client.get_state()
        print(f"[状态] 活跃断点={state['active_bps']:04b} 线程数={state['thread_count']}")

        # 监控循环
        print("\n[监控] 等待断点触发 (Ctrl+C 退出)...")
        last_count = 0
        while True:
            try:
                time.sleep(0.5)
                info = client.get_hit_info(last_count)
                while info is not None:
                    print(f"[命中] {format_hit(info)}")
                    last_count += 1
                    info = client.get_hit_info(last_count)
            except OSError:
                pass  # No more entries
            except KeyboardInterrupt:
                break

    finally:
        client.clear_breakpoint()
        client.close()
        print("\n[清理] 断点已清除")


def cmd_status(args):
    """查看驱动状态"""
    try:
        client = HwBpDriverClient().open()
        state = client.get_state()
        print(f"[状态]")
        print(f"  活跃断点:    {state['active_bps']:04b}")
        print(f"  触发记录数:  {state['hit_count']}")
        print(f"  目标线程数:  {state['thread_count']}")

        # 获取命中记录
        for i in range(min(state['hit_count'], 10)):
            info = client.get_hit_info(i)
            if info:
                print(f"  [{i}] {format_hit(info)}")

        client.close()
    except OSError as e:
        print(f"[错误] 驱动未加载或不可用: {e}")


def cmd_attach(args):
    """附加到进程并设置断点"""
    if len(args) < 1:
        print("用法: attach <地址> [类型] [长度] [PID]")
        print("  若未指定PID，自动查找FreeStyle.exe")
        return

    addr = int(args[0], 16) if args[0].startswith('0x') else int(args[0])
    bp_type = int(args[1]) if len(args) > 1 else 2
    length = int(args[2]) if len(args) > 2 else 4
    pid = int(args[3]) if len(args) > 3 else find_freestyle_pid()

    if not pid:
        print("[错误] FreeStyle.exe 未运行，请指定PID")
        return

    try:
        client = HwBpDriverClient().open()
        client.set_breakpoint(pid, addr, dr_index=0, bp_type=bp_type, length=length)
        state = client.get_state()
        print(f"[设置] 断点 @ 0x{addr:08x} type={bp_type} len={length}")
        print(f"[状态] 活跃={state['active_bps']:04b} 线程={state['thread_count']}")

        print("\n监控中 (Ctrl+C 停止)...")
        last_count = 0
        while True:
            try:
                time.sleep(0.5)
                info = client.get_hit_info(last_count)
                while info is not None:
                    print(f"[命中] {format_hit(info)}")
                    last_count += 1
                    info = client.get_hit_info(last_count)
            except OSError:
                pass
            except KeyboardInterrupt:
                break
    except OSError as e:
        print(f"[错误] {e}")
    finally:
        try:
            client.clear_breakpoint()
            client.close()
        except:
            pass


def read_veh_hits():
    """从 VEH DLL 的共享内存读取断点命中记录"""
    SHARED_MEM_NAME = "HwBpVEHSharedMem"

    class BPHitInfo(ctypes.Structure):
        _pack_ = 1  # 匹配 C 的 #pragma pack(push, 1)
        _fields_ = [
            ("HitCount", ctypes.c_uint32),
            ("TriggerAddress", ctypes.c_uint64),
            ("HitAddress", ctypes.c_uint64),
            ("DrIndex", ctypes.c_uint32),
            ("Timestamp", ctypes.c_uint64),
            ("ThreadId", ctypes.c_uint32),
            ("Rax", ctypes.c_uint64),
            ("Rbx", ctypes.c_uint64),
            ("Rcx", ctypes.c_uint64),
            ("Rdx", ctypes.c_uint64),
            ("Rbp", ctypes.c_uint64),
            ("Rsp", ctypes.c_uint64),
            ("Rsi", ctypes.c_uint64),
            ("Rdi", ctypes.c_uint64),
            ("R8", ctypes.c_uint64),
            ("R9", ctypes.c_uint64),
        ]

    # _pack_ = 1 后 sizeof(BPHitInfo) 应与 C 端一致（108 bytes）
    SHARED_DATA_SIZE = 4 + 200 * ctypes.sizeof(BPHitInfo) + 4

    # 用 OpenFileMappingW 打开已有共享内存
    FILE_MAP_READ = 0x0004
    kernel32 = ctypes.windll.kernel32
    # 64 位指针需要正确设置 restype，否则返回地址被截断
    kernel32.OpenFileMappingW.restype = ctypes.c_void_p
    kernel32.MapViewOfFile.restype = ctypes.c_void_p

    hMap = kernel32.OpenFileMappingW(FILE_MAP_READ, False, SHARED_MEM_NAME)
    if hMap is None or hMap == 0:
        err = kernel32.GetLastError()
        print(f"[VEH 共享内存] 不可用 (OpenFileMappingW 错误 {err})")
        print("提示: VEH DLL 可能尚未注入目标进程")
        return

    try:
        pData = kernel32.MapViewOfFile(hMap, FILE_MAP_READ, 0, 0, SHARED_DATA_SIZE)
        if pData is None or pData == 0 or pData == 0xFFFFFFFF:
            err = kernel32.GetLastError()
            print(f"[VEH 共享内存] MapViewOfFile 失败: {err}")
            return

        try:
            hit_count = ctypes.c_uint32.from_address(pData)
            initialized = ctypes.c_uint32.from_address(pData + SHARED_DATA_SIZE - 4)

            print(f"[VEH 共享内存]")
            print(f"  Initialized = {initialized.value}")
            print(f"  HitCount    = {hit_count.value}")

            if hit_count.value > 0:
                print()
                print("=== 断点命中记录 ===")
                for i in range(min(hit_count.value, 10)):
                    offset = pData + 4 + i * ctypes.sizeof(BPHitInfo)
                    info = BPHitInfo.from_address(offset)
                    print(f"  [{i}]")
                    print(f"    TriggerAddress: 0x{info.TriggerAddress:016x}")
                    print(f"    HitAddress:     0x{info.HitAddress:016x}")
                    print(f"    DrIndex:        DR{info.DrIndex}")
                    print(f"    ThreadId:       {info.ThreadId}")
                    print(f"    Timestamp:      {info.Timestamp} ms")
                    print(f"    RAX: 0x{info.Rax:016x}  RBX: 0x{info.Rbx:016x}")
                    print(f"    RCX: 0x{info.Rcx:016x}  RDX: 0x{info.Rdx:016x}")
                    print(f"    RSP: 0x{info.Rsp:016x}  RBP: 0x{info.Rbp:016x}")
                    print()
        finally:
            kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
            kernel32.UnmapViewOfFile(pData)
    finally:
        kernel32.CloseHandle(hMap)


def cmd_veh(args):
    """读取 VEH 共享内存中的断点命中记录"""
    read_veh_hits()


def cmd_clear(args):
    """清除所有断点"""
    try:
        client = HwBpDriverClient().open()
        client.clear_breakpoint()
        client.close()
        print("断点已清除")
    except OSError as e:
        print(f"[错误] {e}")


COMMANDS = {
    'scan': cmd_scan,
    'trace': cmd_trace,
    'attach': cmd_attach,
    'status': cmd_status,
    'veh': cmd_veh,
    'clear': cmd_clear,
    'help': lambda _: print("命令: scan [ItemCode] | trace [ItemCode] [地址...] | attach <地址> [类型] [长度] | status | veh | clear | help"),
}


def main():
    print("=== HwBpDriver Client ===")
    print(f"SRC_IC: {SRC_IC}")
    print("")

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in COMMANDS:
            COMMANDS[cmd](sys.argv[2:])
            return
        else:
            print(f"未知命令: {cmd}")
            COMMANDS['help']([])
            return

    # 交互模式
    COMMANDS['help']([])
    print("")
    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            if cmd in COMMANDS:
                COMMANDS[cmd](parts[1:])
            else:
                print(f"未知命令: {cmd}")
        except (KeyboardInterrupt, EOFError):
            break


if __name__ == '__main__':
    main()
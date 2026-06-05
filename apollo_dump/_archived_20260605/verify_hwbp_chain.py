"""
verify_hwbp_chain.py — 硬件断点链路端到端验证

目标: 验证 HwBpDriver + VEH 在 Apollo 保护下是否真的能工作

流程:
1. 扫描 ItemCode 地址 (用 Frida，因为需要精确地址)
2. 注入 veh_hook.dll
3. 启动驱动，设硬件断点
4. 监控共享内存看是否命中

前置:
- sc.exe stop ApolloProtect
- 游戏已启动并在房间内
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'verify_hwbp_{time.strftime("%Y%m%d_%H%M%S")}.txt')

# ============== 配置 ==============
SRC_IC = 50125461  # 美丽梦想发型
DRIVER_PATH = r"\\.\HwBpDriver"
VEH_DLL_PATH = os.path.join(SCRIPT_DIR, "veh_hook", "bin", "veh_hook.dll")
SHARED_MEM_NAME = "HwBpVEHSharedMem"

# IOCTL
IOCTL_SET_BP = (0x22 << 16) | (0x800 << 2)
IOCTL_GET_HIT = (0x22 << 16) | (0x801 << 2)
IOCTL_GET_STATE = (0x22 << 16) | (0x803 << 2)

# ============== 日志 ==============
log_lines = []
def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    log_lines.append(line)

def save_log():
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    log(f'日志已保存: {LOG_FILE}')

# ============== 进程查找 ==============
def find_pid():
    r = subprocess.run(['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
                       capture_output=True, text=True, timeout=10)
    for line in r.stdout.strip().split('\n'):
        if 'FreeStyle.exe' in line:
            return int(line.split(',')[1].strip('"'))
    return None

# ============== Frida 扫描 ==============
def scan_itemcode_with_frida(pid, target_ic=SRC_IC):
    """用 Frida 扫描 ItemCode 地址，返回地址列表"""
    import frida

    # 构建扫描模式
    ic_bytes = [
        target_ic & 0xFF,
        (target_ic >> 8) & 0xFF,
        (target_ic >> 16) & 0xFF,
        (target_ic >> 24) & 0xFF
    ]
    pattern = ' '.join(f'{b:02x}' for b in ic_bytes)

    js_code = f'''
    var hits = [];
    var pattern = '{pattern}';

    Process.enumerateRanges('rw-').forEach(function(range) {{
        var mod = Process.findModuleByAddress(range.base);
        if (mod) return;  // 跳过模块，只扫堆

        try {{
            var results = Memory.scanSync(range.base, range.size, pattern);
            results.forEach(function(r) {{
                hits.push(r.address.toString());
            }});
        }} catch(e) {{}}
    }});

    send({{t: 'scan_result', count: hits.length, addrs: hits}});
    '''

    log(f'Frida 附加进程 {pid}...')
    session = frida.attach(pid)
    script = session.create_script(js_code)

    results = []
    done = False

    def on_msg(msg, data):
        nonlocal done, results
        if msg['type'] == 'send':
            p = msg['payload']
            if p.get('t') == 'scan_result':
                results = p['addrs']
                log(f'扫描完成: {p["count"]} 个地址')
                done = True
        elif msg['type'] == 'error':
            log(f'JS错误: {msg.get("description")}')

    script.on('message', on_msg)
    script.load()

    # 等待扫描完成
    for _ in range(30):
        if done:
            break
        time.sleep(0.5)

    script.unload()
    session.detach()
    return results

# ============== DLL 注入 ==============
def inject_dll(pid, dll_path):
    """用 CreateRemoteThread 注入 DLL"""
    kernel32 = ctypes.windll.kernel32

    # 打开进程
    PROCESS_ALL_ACCESS = 0x1F0FFF
    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        log(f'OpenProcess 失败: {kernel32.GetLastError()}')
        return False

    # 分配内存
    dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
    remote_mem = kernel32.VirtualAllocEx(h_process, None, len(dll_path_bytes),
                                          0x1000 | 0x2000,  # MEM_COMMIT | MEM_RESERVE
                                          0x40)  # PAGE_EXECUTE_READWRITE
    if not remote_mem:
        log(f'VirtualAllocEx 失败: {kernel32.GetLastError()}')
        kernel32.CloseHandle(h_process)
        return False

    # 写入 DLL 路径
    written = wintypes.SIZE()
    if not kernel32.WriteProcessMemory(h_process, remote_mem, dll_path_bytes,
                                        len(dll_path_bytes), ctypes.byref(written)):
        log(f'WriteProcessMemory 失败: {kernel32.GetLastError()}')
        kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
        kernel32.CloseHandle(h_process)
        return False

    # 获取 LoadLibraryA 地址
    h_kernel32 = kernel32.GetModuleHandleW('kernel32.dll')
    load_library_addr = kernel32.GetProcAddress(h_kernel32, b'LoadLibraryA')

    # 创建远程线程
    tid = wintypes.DWORD()
    h_thread = kernel32.CreateRemoteThread(h_process, None, 0, load_library_addr,
                                            remote_mem, 0, ctypes.byref(tid))
    if not h_thread:
        log(f'CreateRemoteThread 失败: {kernel32.GetLastError()}')
        kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
        kernel32.CloseHandle(h_process)
        return False

    # 等待线程完成
    kernel32.WaitForSingleObject(h_thread, 5000)

    # 清理
    kernel32.CloseHandle(h_thread)
    kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
    kernel32.CloseHandle(h_process)

    log(f'DLL 注入成功: {dll_path}')
    return True

# ============== 驱动操作 ==============
class HwBpDriver:
    def __init__(self):
        self.handle = None
        self.kernel32 = ctypes.windll.kernel32

    def open(self):
        self.handle = self.kernel32.CreateFileW(
            DRIVER_PATH, 0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
            0, None, 3, 0x80, None  # OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL
        )
        if self.handle == -1 or not self.handle:
            err = self.kernel32.GetLastError()
            raise OSError(f'无法打开驱动 {DRIVER_PATH}, 错误: {err}')
        log(f'驱动已连接: {DRIVER_PATH}')
        return self

    def close(self):
        if self.handle and self.handle != -1:
            self.kernel32.CloseHandle(self.handle)

    def set_breakpoint(self, pid, addr, dr_index=0, bp_type=2, length=4):
        """设置硬件断点。bp_type: 0=执行, 1=写, 2=读写"""
        class BP_REQ(ctypes.Structure):
            _fields_ = [
                ("ProcessId", wintypes.ULONG),
                ("ThreadId", wintypes.ULONG),
                ("Address", ctypes.c_uint64),
                ("Type", wintypes.ULONG),
                ("Length", wintypes.ULONG),
                ("DrIndex", wintypes.ULONG),
            ]

        req = BP_REQ()
        req.ProcessId = pid
        req.ThreadId = 0  # 0 = 所有线程
        req.Address = addr
        req.Type = bp_type
        req.Length = length
        req.DrIndex = dr_index

        ret = wintypes.DWORD()
        result = self.kernel32.DeviceIoControl(
            self.handle, IOCTL_SET_BP,
            ctypes.byref(req), ctypes.sizeof(req),
            None, 0, ctypes.byref(ret), None
        )
        if not result:
            raise OSError(f'设置断点失败: {self.kernel32.GetLastError()}')
        log(f'断点已设置: PID={pid} addr=0x{addr:x} type={bp_type} DR{dr_index}')

    def get_state(self):
        state = (ctypes.c_ulong * 3)()
        ret = wintypes.DWORD()
        self.kernel32.DeviceIoControl(
            self.handle, IOCTL_GET_STATE, None, 0,
            ctypes.byref(state), 12, ctypes.byref(ret), None
        )
        return {'active_bps': state[0], 'hit_count': state[1], 'thread_count': state[2]}

# ============== 共享内存读取 ==============
class SharedMemReader:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.handle = None
        self.data = None

    def open(self):
        self.handle = self.kernel32.OpenFileMappingW(0xF001F, False, SHARED_MEM_NAME)  # FILE_MAP_ALL_ACCESS
        if not self.handle:
            err = self.kernel32.GetLastError()
            raise OSError(f'无法打开共享内存 {SHARED_MEM_NAME}, 错误: {err}')

        self.data = self.kernel32.MapViewOfFile(self.handle, 0xF001F, 0, 0, 0)
        if not self.data:
            self.kernel32.CloseHandle(self.handle)
            raise OSError('MapViewOfFile 失败')

        log(f'共享内存已连接: {SHARED_MEM_NAME}')
        return self

    def close(self):
        if self.data:
            self.kernel32.UnmapViewOfFile(self.data)
        if self.handle:
            self.kernel32.CloseHandle(self.handle)

    def read_hit_count(self):
        """读取命中计数"""
        if not self.data:
            return 0
        return ctypes.cast(self.data, ctypes.POINTER(ctypes.c_long)).contents.value

    def read_hits(self, max_count=10):
        """读取命中记录"""
        # 结构: HitCount(4) + Records[200] 每个记录约 120 字节
        # 简化: 只读前几条
        hits = []
        if not self.data:
            return hits

        import struct
        data = ctypes.string_at(self.data, 2048)
        hit_count = struct.unpack('<I', data[:4])[0]

        # 每条记录结构 (简化版)
        offset = 4
        record_size = 120  # 大约

        for i in range(min(hit_count, max_count)):
            if offset + 8 > len(data):
                break
            trigger_addr, hit_addr = struct.unpack('<QQ', data[offset:offset+16])
            hits.append({
                'n': i + 1,
                'trigger': hex(trigger_addr),
                'hit_addr': hex(hit_addr)
            })
            offset += record_size

        return hits

# ============== 主流程 ==============
def main():
    log('=== 硬件断点链路验证 ===')
    log(f'目标 ItemCode: {SRC_IC}')
    log('')

    # 1. 检查 Apollo 状态
    log('步骤1: 检查 Apollo 状态')
    r = subprocess.run(['sc', 'query', 'ApolloProtect'], capture_output=True, text=True)
    if 'RUNNING' in r.stdout:
        log('警告: ApolloProtect 正在运行，需要先停止')
        log('执行: sc.exe stop ApolloProtect')
        subprocess.run(['sc.exe', 'stop', 'ApolloProtect'], capture_output=True)
        time.sleep(2)

    # 2. 找进程
    log('')
    log('步骤2: 查找 FreeStyle.exe 进程')
    pid = find_pid()
    if not pid:
        log('错误: FreeStyle.exe 未运行，请先启动游戏并进入房间')
        return 1
    log(f'PID = {pid}')

    # 3. 扫描地址
    log('')
    log('步骤3: 扫描 ItemCode 地址')
    try:
        addrs = scan_itemcode_with_frida(pid, SRC_IC)
    except Exception as e:
        log(f'扫描失败: {e}')
        log('提示: Frida 可能触发 Apollo 检测，游戏可能被杀')
        save_log()
        return 1

    if not addrs:
        log('未找到 ItemCode 地址')
        save_log()
        return 1

    log(f'找到 {len(addrs)} 个地址:')
    for i, a in enumerate(addrs[:10]):
        log(f'  [{i+1}] {a}')
    if len(addrs) > 10:
        log(f'  ... 还有 {len(addrs)-10} 个')

    # 选第一个地址测试
    test_addr = int(addrs[0], 16)
    log(f'')
    log(f'选择地址测试: 0x{test_addr:x}')

    # 4. 注入 VEH DLL
    log('')
    log('步骤4: 注入 VEH DLL')
    if not os.path.exists(VEH_DLL_PATH):
        log(f'错误: VEH DLL 不存在: {VEH_DLL_PATH}')
        save_log()
        return 1

    if not inject_dll(pid, VEH_DLL_PATH):
        log('DLL 注入失败')
        save_log()
        return 1

    time.sleep(1)  # 等 DLL 初始化

    # 5. 连接驱动
    log('')
    log('步骤5: 连接硬件断点驱动')
    driver = HwBpDriver()
    try:
        driver.open()
    except OSError as e:
        log(f'错误: {e}')
        log('提示: 驱动可能未加载，尝试 sc.exe start hwbp_driver')
        save_log()
        return 1

    # 6. 设置断点
    log('')
    log('步骤6: 设置硬件断点 (读类型)')
    try:
        driver.set_breakpoint(pid, test_addr, dr_index=0, bp_type=2, length=4)
    except OSError as e:
        log(f'设置断点失败: {e}')
        driver.close()
        save_log()
        return 1

    # 7. 连接共享内存
    log('')
    log('步骤7: 连接共享内存')
    shm = SharedMemReader()
    try:
        shm.open()
    except OSError as e:
        log(f'警告: {e}')
        log('VEH 可能未正确初始化，继续监控...')

    # 8. 监控命中
    log('')
    log('步骤8: 监控断点命中')
    log('在游戏中操作角色，触发 ItemCode 被读取...')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                state = driver.get_state()
                log(f'驱动状态: active_bps={state["active_bps"]} hit_count={state["hit_count"]}')

                try:
                    hit_count = shm.read_hit_count()
                    log(f'共享内存命中数: {hit_count}')
                    if hit_count > 0:
                        hits = shm.read_hits()
                        for h in hits:
                            log(f'  命中 #{h["n"]}: trigger={h["trigger"]} hit_addr={h["hit_addr"]}')
                except Exception as e:
                    log(f'读共享内存失败: {e}')

    except (KeyboardInterrupt, EOFError):
        pass

    # 清理
    driver.close()
    shm.close()
    save_log()
    log('验证结束')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log(f'异常: {e}')
        save_log()
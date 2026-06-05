"""
injector.py — 注入 apollo_hook.dll 到 FreeStyle.exe (32位进程)
64位Python注入32位进程: 需要从SysWOW64 kernel32获取LoadLibraryA地址
用法: python injector.py [dll_path]
默认DLL: C:\\tmp\\apollo_hook.dll
"""
import sys, os, time, struct, ctypes, ctypes.wintypes

kernel32 = ctypes.windll.kernel32

# 64位Python: 必须设restype/argtypes，否则HMODULE/PTR被截断为32位
kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.wintypes.LPVOID
kernel32.VirtualAllocEx.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_size_t, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]
kernel32.WriteProcessMemory.restype = ctypes.wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.GetModuleHandleA.restype = ctypes.wintypes.HMODULE
kernel32.GetModuleHandleA.argtypes = [ctypes.wintypes.LPCSTR]
kernel32.GetProcAddress.restype = ctypes.wintypes.LPVOID
kernel32.GetProcAddress.argtypes = [ctypes.wintypes.HMODULE, ctypes.wintypes.LPCSTR]
kernel32.CreateRemoteThread.restype = ctypes.wintypes.HANDLE
kernel32.CreateRemoteThread.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.wintypes.LPVOID, ctypes.wintypes.LPVOID, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD)]
kernel32.WaitForSingleObject.restype = ctypes.wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
kernel32.GetExitCodeThread.restype = ctypes.wintypes.BOOL
kernel32.GetExitCodeThread.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.wintypes.DWORD)]
kernel32.VirtualFreeEx.restype = ctypes.wintypes.BOOL
kernel32.VirtualFreeEx.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_size_t, ctypes.wintypes.DWORD]
kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT_RESERVE = 0x3000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
WAIT_OBJECT_0 = 0
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes.DWORD),
        ('th32ModuleID', ctypes.wintypes.DWORD),
        ('th32ProcessID', ctypes.wintypes.DWORD),
        ('GlbcntUsage', ctypes.wintypes.DWORD),
        ('ProccntUsage', ctypes.wintypes.DWORD),
        ('modBaseAddr', ctypes.c_void_p),
        ('modBaseSize', ctypes.wintypes.DWORD),
        ('hModule', ctypes.wintypes.HMODULE),
        ('szModule', ctypes.c_char * 256),
        ('szExePath', ctypes.c_char * 260),
    ]

def find_pid():
    """找FreeStyle.exe PID"""
    import subprocess
    try:
        r = subprocess.run(
            ['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except Exception as e:
        print(f'查找进程失败: {e}')
    return None

def get_remote_module_base(pid, module_name):
    """枚举目标进程模块，找到指定模块的基址"""
    hSnap = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if hSnap == ctypes.wintypes.HANDLE(-1).value:
        print(f'  CreateToolhelp32Snapshot失败 (err={ctypes.GetLastError()})')
        return None

    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)

    result = None
    if kernel32.Module32First(hSnap, ctypes.byref(me)):
        while True:
            if me.szModule.decode('ascii', errors='replace').lower() == module_name.lower():
                result = me.modBaseAddr
                print(f'  Found {module_name} base=0x{result:X} in PID {pid}')
                break
            me.dwSize = ctypes.sizeof(MODULEENTRY32)
            if not kernel32.Module32Next(hSnap, ctypes.byref(me)):
                break
    kernel32.CloseHandle(hSnap)
    return result

def pe_get_export_rva(pe_path, func_name):
    """解析PE文件导出表，获取函数RVA"""
    with open(pe_path, 'rb') as f:
        # DOS header
        dos = f.read(64)
        if dos[:2] != b'MZ':
            return None
        pe_off = struct.unpack_from('<I', dos, 0x3C)[0]

        # PE header
        f.seek(pe_off)
        sig = f.read(4)
        if sig != b'PE\x00\x00':
            return None

        # COFF header (20 bytes)
        coff = f.read(20)
        machine = struct.unpack_from('<H', coff, 0)[0]
        num_sections = struct.unpack_from('<H', coff, 2)[0]
        opt_hdr_size = struct.unpack_from('<H', coff, 16)[0]

        # Optional header
        opt = f.read(opt_hdr_size)
        magic = struct.unpack_from('<H', opt, 0)[0]
        # PE32: magic=0x10b, PE32+: magic=0x20b
        if magic == 0x10b:  # PE32 (32-bit)
            export_dir_rva = struct.unpack_from('<I', opt, 96)[0]
            export_dir_size = struct.unpack_from('<I', opt, 100)[0]
        elif magic == 0x20b:  # PE32+ (64-bit)
            export_dir_rva = struct.unpack_from('<I', opt, 112)[0]
            export_dir_size = struct.unpack_from('<I', opt, 116)[0]
        else:
            return None

        if not export_dir_rva:
            return None

        # Section headers
        sections = []
        sec_start = pe_off + 4 + 20 + opt_hdr_size
        for i in range(num_sections):
            f.seek(sec_start + i * 40)
            sec = f.read(40)
            name = sec[:8].rstrip(b'\x00').decode('ascii', errors='replace')
            vsize = struct.unpack_from('<I', sec, 8)[0]
            vrva = struct.unpack_from('<I', sec, 12)[0]
            rawsize = struct.unpack_from('<I', sec, 16)[0]
            rawptr = struct.unpack_from('<I', sec, 20)[0]
            sections.append((name, vrva, vsize, rawptr, rawsize))

    def rva_to_file(rva):
        for name, vrva, vsize, rawptr, rawsize in sections:
            if vrva <= rva < vrva + max(vsize, rawsize):
                return rawptr + (rva - vrva)
        return None

    with open(pe_path, 'rb') as f:
        # Export directory
        exp_off = rva_to_file(export_dir_rva)
        if exp_off is None:
            return None

        f.seek(exp_off)
        exp_dir = f.read(40)
        num_funcs = struct.unpack_from('<I', exp_dir, 20)[0]
        num_names = struct.unpack_from('<I', exp_dir, 24)[0]
        addr_rva = struct.unpack_from('<I', exp_dir, 28)[0]
        names_rva = struct.unpack_from('<I', exp_dir, 32)[0]
        ords_rva = struct.unpack_from('<I', exp_dir, 36)[0]

        # Read name pointers
        f.seek(rva_to_file(names_rva))
        name_ptrs = struct.unpack(f'<{num_names}I', f.read(num_names * 4))

        # Read ordinals
        f.seek(rva_to_file(ords_rva))
        ords = struct.unpack(f'<{num_names}H', f.read(num_names * 2))

        # Find function
        for i in range(num_names):
            f.seek(rva_to_file(name_ptrs[i]))
            name = b''
            while True:
                c = f.read(1)
                if c == b'\x00' or not c:
                    break
                name += c
            if name.decode('ascii') == func_name:
                # Get address by ordinal
                func_rva_off = rva_to_file(addr_rva)
                f.seek(func_rva_off + ords[i] * 4)
                func_rva = struct.unpack('<I', f.read(4))[0]
                return func_rva

    return None

def get_loadlib_addr(pid):
    """获取目标32位进程中LoadLibraryA的地址
    方法: 枚举目标进程kernel32.dll基址 + 解析PE导出表RVA
    """
    # 1. 找目标进程中kernel32.dll基址
    base = get_remote_module_base(pid, 'kernel32.dll')
    if not base:
        print('  kernel32.dll not found in target')
        return None
    # 截断到32位（WOW64进程地址空间）
    base32 = base & 0xFFFFFFFF

    # 2. 解析SysWOW64 kernel32.dll获取LoadLibraryA RVA
    syswow64_kern = r'C:\Windows\SysWOW64\kernel32.dll'
    rva = pe_get_export_rva(syswow64_kern, 'LoadLibraryA')
    if not rva:
        print(f'  解析{syswow64_kern}导出表失败')
        return None
    print(f'  LoadLibraryA RVA=0x{rva:X}')

    addr = base32 + rva
    print(f'  LoadLibraryA in target = 0x{base32:X} + 0x{rva:X} = 0x{addr:X}')
    return addr

def inject(pid, dll_path):
    """注入DLL到目标进程"""
    if not os.path.isfile(dll_path):
        print(f'DLL不存在: {dll_path}')
        return False

    dll_path_bytes = dll_path.encode('ascii') + b'\x00'

    # 打开目标进程
    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        print(f'OpenProcess失败 (err={ctypes.GetLastError()})')
        return False
    print(f'OpenProcess OK handle=0x{hProcess:X}')

    # 在目标进程分配内存
    remote_mem = kernel32.VirtualAllocEx(hProcess, 0, len(dll_path_bytes),
                                         MEM_COMMIT_RESERVE, PAGE_READWRITE)
    if not remote_mem:
        print(f'VirtualAllocEx失败 (err={ctypes.GetLastError()})')
        kernel32.CloseHandle(hProcess)
        return False
    print(f'VirtualAllocEx OK addr=0x{remote_mem:X}')

    # 写入DLL路径
    written = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(hProcess, remote_mem,
                                      dll_path_bytes, len(dll_path_bytes),
                                      ctypes.byref(written))
    if not ok:
        print(f'WriteProcessMemory失败 (err={ctypes.GetLastError()})')
        kernel32.VirtualFreeEx(hProcess, remote_mem, 0, MEM_RELEASE)
        kernel32.CloseHandle(hProcess)
        return False
    print(f'WriteProcessMemory OK {written.value} bytes')

    # 获取32位LoadLibraryA地址 (目标进程上下文)
    print('Resolving LoadLibraryA in 32-bit target...')
    pLoadLib = get_loadlib_addr(pid)
    if not pLoadLib:
        print('获取LoadLibraryA地址失败')
        kernel32.VirtualFreeEx(hProcess, remote_mem, 0, MEM_RELEASE)
        kernel32.CloseHandle(hProcess)
        return False

    # 创建远程线程
    tid = ctypes.c_ulong(0)
    hThread = kernel32.CreateRemoteThread(hProcess, None, 0,
                                          pLoadLib, remote_mem, 0,
                                          ctypes.byref(tid))
    if not hThread:
        print(f'CreateRemoteThread失败 (err={ctypes.GetLastError()})')
        kernel32.VirtualFreeEx(hProcess, remote_mem, 0, MEM_RELEASE)
        kernel32.CloseHandle(hProcess)
        return False
    print(f'CreateRemoteThread OK tid={tid.value}')

    # 等待线程完成
    result = kernel32.WaitForSingleObject(hThread, 10000)
    if result == WAIT_OBJECT_0:
        print('DLL加载完成!')
    else:
        print(f'等待超时 (result={result})')

    # 获取线程退出码 (LoadLibraryA返回的DLL模块句柄)
    exit_code = ctypes.c_ulong(0)
    kernel32.GetExitCodeThread(hThread, ctypes.byref(exit_code))
    print(f'DLL handle=0x{exit_code.value:X}')

    # 清理
    kernel32.VirtualFreeEx(hProcess, remote_mem, 0, MEM_RELEASE)
    kernel32.CloseHandle(hThread)
    kernel32.CloseHandle(hProcess)
    return True

def check_log():
    """检查注入后日志"""
    log_path = r'C:\tmp\apollo_hook.log'
    if os.path.isfile(log_path):
        print(f'\n--- {log_path} (最后20行) ---')
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                print(line.rstrip())
    else:
        print(f'\n日志文件不存在: {log_path}')

def main():
    dll_path = sys.argv[1] if len(sys.argv) > 1 else r'C:\tmp\apollo_hook.dll'

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return 1

    print(f'FreeStyle.exe PID={pid}')
    print(f'DLL: {dll_path}')
    print()

    if inject(pid, dll_path):
        print('\n注入成功!')
        time.sleep(1)
        check_log()
    else:
        print('\n注入失败!')
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())

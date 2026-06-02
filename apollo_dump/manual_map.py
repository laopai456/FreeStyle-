"""
manual_map.py v2 — Manual map DLL injection
- 本地PE解析获取函数RVA (解析SysWOW64 DLL)
- 远程读取模块base → base + RVA = 目标地址
- 输出写入日志文件 C:\tmp\manual_map.log

用法: python manual_map.py [dll_path]
"""
import sys, os, struct, ctypes, ctypes.wintypes, time

kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.wintypes.LPVOID
kernel32.VirtualAllocEx.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_size_t, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]
kernel32.VirtualFreeEx.restype = ctypes.wintypes.BOOL
kernel32.VirtualFreeEx.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_size_t, ctypes.wintypes.DWORD]
kernel32.ReadProcessMemory.restype = ctypes.wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = ctypes.wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.CreateRemoteThread.restype = ctypes.wintypes.HANDLE
kernel32.CreateRemoteThread.argtypes = [ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.wintypes.LPVOID, ctypes.wintypes.LPVOID, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD)]
kernel32.WaitForSingleObject.restype = ctypes.wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT_RESERVE = 0x3000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40

LOG_FILE = r'C:\tmp\manual_map.log'
LOG_F = None

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()

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
    import subprocess
    r = subprocess.run(['tasklist', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
                       capture_output=True, text=True, timeout=10)
    for line in r.stdout.strip().split('\n'):
        if 'FreeStyle.exe' in line:
            return int(line.split(',')[1].strip('"'))
    return None

def get_target_modules(pid):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == ctypes.wintypes.HANDLE(-1).value:
        return {}
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    mods = {}
    if kernel32.Module32First(snap, ctypes.byref(me)):
        while True:
            name = me.szModule.decode('ascii', errors='replace').lower()
            mods[name] = me.modBaseAddr & 0xFFFFFFFF
            me.dwSize = ctypes.sizeof(MODULEENTRY32)
            if not kernel32.Module32Next(snap, ctypes.byref(me)):
                break
    kernel32.CloseHandle(snap)
    return mods

def rpm(hProcess, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(hProcess, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
    return buf.raw[:read.value] if ok else None

def wpm(hProcess, addr, data):
    written = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hProcess, ctypes.c_void_p(addr),
                                       data, len(data), ctypes.byref(written))

def parse_local_exports(dll_path):
    """解析本地32位DLL的导出表, 返回 {func_name: RVA}"""
    with open(dll_path, 'rb') as f:
        data = f.read()

    assert data[:2] == b'MZ'
    pe_off = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[pe_off:pe_off+4] == b'PE\x00\x00'
    coff = pe_off + 4
    num_sec = struct.unpack_from('<H', data, coff + 2)[0]
    opt_size = struct.unpack_from('<H', data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from('<H', data, opt)[0]

    if magic == 0x10B:  # PE32
        export_rva = struct.unpack_from('<I', data, opt + 96)[0]
        export_size = struct.unpack_from('<I', data, opt + 100)[0]
    else:
        return {}

    if not export_rva:
        return {}

    # Sections
    sec_off = opt + opt_size
    sections = []
    for i in range(num_sec):
        o = sec_off + i * 40
        sections.append({
            'vrva': struct.unpack_from('<I', data, o + 12)[0],
            'vsize': struct.unpack_from('<I', data, o + 8)[0],
            'rawptr': struct.unpack_from('<I', data, o + 20)[0],
            'rawsize': struct.unpack_from('<I', data, o + 16)[0],
        })

    def rva2off(rva):
        for s in sections:
            if s['vrva'] <= rva < s['vrva'] + max(s['vsize'], s['rawsize']):
                return s['rawptr'] + (rva - s['vrva'])
        return None

    exp_off = rva2off(export_rva)
    if exp_off is None:
        return {}

    num_funcs = struct.unpack_from('<I', data, exp_off + 20)[0]
    num_names = struct.unpack_from('<I', data, exp_off + 24)[0]
    addr_rva = struct.unpack_from('<I', data, exp_off + 28)[0]
    names_rva = struct.unpack_from('<I', data, exp_off + 32)[0]
    ords_rva = struct.unpack_from('<I', data, exp_off + 36)[0]

    names_off = rva2off(names_rva)
    ords_off = rva2off(ords_rva)
    addr_off = rva2off(addr_rva)
    if not names_off or not ords_off or not addr_off:
        return {}

    result = {}
    for i in range(num_names):
        name_ptr = struct.unpack_from('<I', data, names_off + i * 4)[0]
        name_off = rva2off(name_ptr)
        if name_off is None:
            continue
        fn = b''
        p = name_off
        while data[p]:
            fn += bytes([data[p]])
            p += 1
        fn = fn.decode('ascii')

        ordinal = struct.unpack_from('<H', data, ords_off + i * 2)[0]
        func_rva = struct.unpack_from('<I', data, addr_off + ordinal * 4)[0]
        result[fn] = func_rva

    return result

class PEFile:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = f.read()
        self._parse()

    def _parse(self):
        d = self.data
        assert d[:2] == b'MZ'
        self.pe_off = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[self.pe_off:self.pe_off+4] == b'PE\x00\x00'
        coff = self.pe_off + 4
        self.num_sec = struct.unpack_from('<H', d, coff + 2)[0]
        opt_size = struct.unpack_from('<H', d, coff + 16)[0]
        opt = coff + 20
        assert struct.unpack_from('<H', d, opt)[0] == 0x10B
        self.entry_rva = struct.unpack_from('<I', d, opt + 16)[0]
        self.image_base = struct.unpack_from('<I', d, opt + 28)[0]
        self.size_of_image = struct.unpack_from('<I', d, opt + 56)[0]
        self.size_of_headers = struct.unpack_from('<I', d, opt + 60)[0]
        dd = opt + 96
        self.import_rva = struct.unpack_from('<I', d, dd + 8)[0]
        self.import_size = struct.unpack_from('<I', d, dd + 12)[0]
        self.reloc_rva = struct.unpack_from('<I', d, dd + 40)[0]
        self.reloc_size = struct.unpack_from('<I', d, dd + 44)[0]
        sec = opt + opt_size
        self.sections = []
        for i in range(self.num_sec):
            o = sec + i * 40
            self.sections.append({
                'vrva': struct.unpack_from('<I', d, o + 12)[0],
                'vsize': struct.unpack_from('<I', d, o + 8)[0],
                'rawptr': struct.unpack_from('<I', d, o + 20)[0],
                'rawsize': struct.unpack_from('<I', d, o + 16)[0],
            })

    def rva_to_off(self, rva):
        for s in self.sections:
            if s['vrva'] <= rva < s['vrva'] + max(s['vsize'], s['rawsize']):
                return s['rawptr'] + (rva - s['vrva'])
        return None

    def get_imports(self):
        if not self.import_rva:
            return []
        imports = []
        off = self.rva_to_off(self.import_rva)
        while off is not None:
            ilt_rva = struct.unpack_from('<I', self.data, off)[0]
            name_rva = struct.unpack_from('<I', self.data, off + 12)[0]
            iat_rva = struct.unpack_from('<I', self.data, off + 16)[0]
            if name_rva == 0:
                break
            noff = self.rva_to_off(name_rva)
            dll_name = b''
            while self.data[noff]:
                dll_name += bytes([self.data[noff]])
                noff += 1
            funcs = []
            use_rva = ilt_rva if ilt_rva else iat_rva
            ilt_off = self.rva_to_off(use_rva)
            idx = 0
            while True:
                entry = struct.unpack_from('<I', self.data, ilt_off + idx * 4)[0]
                if entry == 0:
                    break
                if entry & 0x80000000:
                    funcs.append(('ord', entry & 0xFFFF))
                else:
                    ho = self.rva_to_off(entry)
                    fn = b''
                    p = ho + 2
                    while self.data[p]:
                        fn += bytes([self.data[p]])
                        p += 1
                    funcs.append(('name', fn.decode('ascii')))
                idx += 1
            imports.append({'dll': dll_name.decode('ascii'), 'funcs': funcs, 'iat_rva': iat_rva})
            off += 20
        return imports

    def get_relocs(self):
        if not self.reloc_rva:
            return []
        relocs = []
        off = self.rva_to_off(self.reloc_rva)
        end = off + self.reloc_size
        while off and off < end:
            block_rva = struct.unpack_from('<I', self.data, off)[0]
            block_sz = struct.unpack_from('<I', self.data, off + 4)[0]
            if block_sz == 0:
                break
            n = (block_sz - 8) // 2
            for i in range(n):
                e = struct.unpack_from('<H', self.data, off + 8 + i * 2)[0]
                if (e >> 12) == 3:
                    relocs.append(block_rva + (e & 0xFFF))
            off += block_sz
        return relocs

# SysWOW64 DLL缓存
_syswow_exports = {}

def resolve_import(hProcess, dll_name, func_name, target_mods):
    """解析导入函数: 本地PE获取RVA, 远程模块base+RVA=地址"""
    dll_lower = dll_name.lower()

    # 获取目标进程中的模块base
    mod_base = target_mods.get(dll_lower)
    if mod_base is None:
        return None

    # 获取本地导出RVA (缓存)
    if dll_lower not in _syswow_exports:
        syswow_path = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'SysWOW64', dll_name)
        if os.path.isfile(syswow_path):
            _syswow_exports[dll_lower] = parse_local_exports(syswow_path)
            log(f'  Parsed {dll_name}: {len(_syswow_exports[dll_lower])} exports')
        else:
            _syswow_exports[dll_lower] = {}
            log(f'  SysWOW64/{dll_name} not found')

    exports = _syswow_exports[dll_lower]
    rva = exports.get(func_name)
    if rva is None:
        return None

    return mod_base + rva

def manual_map(pid, dll_path):
    pe = PEFile(dll_path)
    log(f'DLL: {os.path.basename(dll_path)}')
    log(f'  Base=0x{pe.image_base:X} Size=0x{pe.size_of_image:X} Entry=0x{pe.entry_rva:X}')
    log(f'  Sections: {pe.num_sec}, Relocs: {"yes" if pe.reloc_rva else "no"}, Imports: {"yes" if pe.import_rva else "no"}')

    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        log(f'OpenProcess failed err={ctypes.GetLastError()}')
        return False

    # 1. Allocate
    size = pe.size_of_image
    remote_base = kernel32.VirtualAllocEx(hProcess, 0, size, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    if not remote_base:
        log(f'VirtualAllocEx failed err={ctypes.GetLastError()}')
        kernel32.CloseHandle(hProcess)
        return False
    remote_base = remote_base & 0xFFFFFFFF
    delta = remote_base - pe.image_base
    log(f'Allocated: 0x{remote_base:X} (delta=0x{delta:X})')

    # 2. Write headers + sections
    wpm(hProcess, remote_base, pe.data[:pe.size_of_headers])
    for s in pe.sections:
        if s['rawsize'] > 0:
            wpm(hProcess, remote_base + s['vrva'], pe.data[s['rawptr']:s['rawptr'] + s['rawsize']])
    log(f'Wrote {pe.num_sec} sections')

    # 3. Fix relocations
    relocs = pe.get_relocs()
    fixed = 0
    for rva in relocs:
        raw = rpm(hProcess, remote_base + rva, 4)
        if raw:
            val = struct.unpack('<I', raw)[0] + delta
            wpm(hProcess, remote_base + rva, struct.pack('<I', val))
            fixed += 1
    log(f'Relocations: {fixed}/{len(relocs)} fixed')

    # 4. Resolve imports — 本地PE解析 + 远程模块base
    target_mods = get_target_modules(pid)
    imports = pe.get_imports()
    log(f'Imports: {len(imports)} DLLs')
    total_funcs = 0
    failed_funcs = 0

    for imp in imports:
        for i, (ftype, fname) in enumerate(imp['funcs']):
            if ftype == 'name':
                addr = resolve_import(hProcess, imp['dll'], fname, target_mods)
            else:
                addr = None

            iat_addr = remote_base + imp['iat_rva'] + i * 4

            if addr is None:
                failed_funcs += 1
                log(f'  FAIL: {imp["dll"]}!{fname or ftype}')
            else:
                wpm(hProcess, iat_addr, struct.pack('<I', addr))
                total_funcs += 1

        log(f'  {imp["dll"]}: {total_funcs} resolved, {failed_funcs} failed')

    if failed_funcs > 0:
        log(f'WARNING: {failed_funcs} imports unresolved!')

    # 5. Verify: 回读IAT确认
    log('Verifying IAT...')
    for imp in imports:
        for i, (ftype, fname) in enumerate(imp['funcs']):
            iat_addr = remote_base + imp['iat_rva'] + i * 4
            raw = rpm(hProcess, iat_addr, 4)
            val = struct.unpack('<I', raw)[0] if raw else 0
            status = 'OK' if val > 0x10000 else 'BAD'
            if status == 'BAD':
                log(f'  VERIFY FAIL: {imp["dll"]}!{fname or ftype} = 0x{val:X}')

    # 6. Shellcode → DllMain(base, DLL_PROCESS_ATTACH, NULL)
    entry_addr = remote_base + pe.entry_rva
    sc = (
        b'\x6A\x00'                                # push 0
        b'\x6A\x01'                                # push 1
        b'\xFF\x74\x24\x0C'                        # push [esp+12]
        b'\xB8' + struct.pack('<I', entry_addr) +  # mov eax, entry
        b'\xFF\xD0'                                # call eax
        b'\xC2\x04\x00'                            # ret 4
    )
    sc_addr = kernel32.VirtualAllocEx(hProcess, 0, len(sc), MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    sc_addr = sc_addr & 0xFFFFFFFF
    wpm(hProcess, sc_addr, sc)
    log(f'Shellcode: 0x{sc_addr:X} → DllMain 0x{entry_addr:X}')

    # 7. CreateRemoteThread
    tid = ctypes.c_ulong(0)
    hThread = kernel32.CreateRemoteThread(hProcess, None, 0,
                                          ctypes.c_void_p(sc_addr),
                                          ctypes.c_void_p(remote_base),
                                          0, ctypes.byref(tid))
    if not hThread:
        log(f'CreateRemoteThread failed err={ctypes.GetLastError()}')
        kernel32.CloseHandle(hProcess)
        return False

    log(f'Thread tid={tid.value}, waiting...')
    kernel32.WaitForSingleObject(hThread, 10000)
    kernel32.VirtualFreeEx(hProcess, ctypes.c_void_p(sc_addr), 0, MEM_RELEASE)
    kernel32.CloseHandle(hThread)
    kernel32.CloseHandle(hProcess)
    log(f'Done! DLL @ 0x{remote_base:X}')
    return True

def main():
    global LOG_F
    dll_path = sys.argv[1] if len(sys.argv) > 1 else r'C:\tmp\apollo_hook.dll'
    if not os.path.isfile(dll_path):
        print(f'DLL not found: {dll_path}')
        return 1

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe not running')
        return 1

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== Manual Map v2 === PID={pid}')
    ok = manual_map(pid, dll_path)
    if LOG_F:
        LOG_F.close()
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())

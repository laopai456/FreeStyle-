# patch_itemcode_brutal.py — 暴力 patch: 搜索内存中所有 ItemCode 出现位置并替换
#
# 不依赖描述符 vtable, 直接搜 int32 值
#
# 用法: py patch_itemcode_brutal.py <src_ic> <dst_ic>
# 例:   py patch_itemcode_brutal.py 50122931 50125711

import pymem, struct, sys, subprocess, time
import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
MEM_COMMIT = 0x1000
RW_PROTECT = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}
TEXT_CEILING = 0x02B00000

class MBI(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wintypes.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wintypes.DWORD),
        ('Protect', wintypes.DWORD),
        ('Type', wintypes.DWORD),
    ]

def find_pid():
    r = subprocess.run(['tasklist','/FI','IMAGENAME eq FreeStyle.exe','/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts)>=2 and parts[1].isdigit():
            return int(parts[1])
    return None

def scan_and_patch(pm, src_ic, dst_ic, dry_run=False):
    src_bytes = struct.pack('<i', src_ic)
    dst_bytes = struct.pack('<i', dst_ic)
    h = pm.process_handle
    hits = []
    patched = []

    addr = 0
    mbi = MBI()
    mbi_size = ctypes.sizeof(mbi)
    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0: break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING and size <= 0x1000000:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(src_bytes, off)
                        if idx < 0: break
                        hit_addr = base + idx
                        hits.append(hit_addr)

                        if not dry_run:
                            # Check if this is a writable location
                            try:
                                pm.write_bytes(hit_addr, dst_bytes, 4)
                                patched.append(hit_addr)
                            except:
                                pass
                        off = idx + 4
            except: pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000: break
        addr = next_addr

    return hits, patched

def main():
    if len(sys.argv) < 3:
        print("Usage: py patch_itemcode_brutal.py <src_ic> <dst_ic>")
        return

    src = int(sys.argv[1])
    dst = int(sys.argv[2])
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found'); return

    pm = pymem.Pymem(pid)
    print(f'PID={pid}  src={src} (0x{src:X}) -> dst={dst} (0x{dst:X})')

    # Dry run first
    print('\n[*] Scanning (dry run)...')
    hits, _ = scan_and_patch(pm, src, dst, dry_run=True)
    print(f'    Found {len(hits)} occurrences:')
    for h in sorted(hits):
        # Read context
        try:
            ctx = pm.read_bytes(max(h - 8, TEXT_CEILING), 0x20)
            dwords = [struct.unpack_from('<I', ctx, i)[0] for i in range(0, len(ctx), 4)]
            ctx_str = ' '.join(f'{v:08X}' for v in dwords)
        except:
            ctx_str = '?'
        print(f'    0x{h:08X}  [{ctx_str}]')

    # Patch
    print(f'\n[*] Patching all {len(hits)} locations...')
    _, patched = scan_and_patch(pm, src, dst, dry_run=False)
    print(f'    Patched {len(patched)}/{len(hits)} locations')

    # Verify
    print('\n[*] Verifying...')
    hits2, _ = scan_and_patch(pm, src, dst, dry_run=True)
    hits3, _ = scan_and_patch(pm, dst, dst, dry_run=True)
    print(f'    Remaining src ({src}): {len(hits2)}')
    print(f'    New dst ({dst}): {len(hits3)}')

    print(f'\n[*] Done. Check in-game.')
    print(f'[*] To revert: py patch_itemcode_brutal.py {dst} {src}')
    pm.close_process()

if __name__ == '__main__':
    main()

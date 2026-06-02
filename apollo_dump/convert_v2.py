# convert_v2.py — 从已有 DD 对象复制物理参数到 DS 对象
#
# 策略:
#   1. 扫描当前 DD 对象, 读其物理区域字段 (作为参考)
#   2. 扫描 DS 对象
#   3. 将 DS 对象转为 DD (复制 DD 对象的物理参数)
#   4. 或者: 直接从 DD 对象读 vtable+type8+phys, 写到 DS 对象
#
# 用法:
#   py convert_v2.py              # 列出 DD/DS, 选择转换
#   py convert_v2.py --revert     # 恢复

import pymem
import struct
import sys
import os
import json
import time
import ctypes
from ctypes import wintypes

DD_VTABLE = 0x0284A9EC
DS_VTABLE = 0x0284E00C
TEXT_CEILING = 0x02B00000

BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convert_v2_backup.json')

kernel32 = ctypes.windll.kernel32
MEM_COMMIT = 0x1000
RW_PROTECT = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
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
    import subprocess
    try:
        r = subprocess.run(
            ['tasklist.exe', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().split('\n'):
            if 'FreeStyle' in line:
                return int(line.split(',')[1].strip('"'))
    except:
        pass
    return None

def scan_actors(pm, vtable_val, expected_type8):
    target = struct.pack('<I', vtable_val)
    h = pm.process_handle
    found = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)
    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0: break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0 and base >= TEXT_CEILING:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(target, off)
                        if idx < 0: break
                        obj_addr = base + idx
                        if idx + 12 <= len(data):
                            type8 = struct.unpack_from('<I', data, idx + 8)[0]
                            if type8 == expected_type8:
                                found.append(obj_addr)
                        off = idx + 4
            except: pass
        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000: break
        addr = next_addr
    return found

def read_phys_fields(pm, addr):
    """读物理相关字段"""
    data = pm.read_bytes(addr, 0x4A0)
    if not data:
        return None
    fields = {}
    for off in [0x000, 0x004, 0x008, 0x00C, 0x014, 0x018,
                0x060, 0x064, 0x070, 0x074, 0x080, 0x0C0,
                0x460, 0x464, 0x468, 0x46C, 0x470, 0x474, 0x478, 0x47C,
                0x480, 0x484, 0x488, 0x48C, 0x490, 0x494, 0x498, 0x49C]:
        if off + 4 <= len(data):
            fields[off] = struct.unpack_from('<I', data, off)[0]
    # 也读 float 版本
    for off in [0x470, 0x474, 0x478, 0x47C, 0x480, 0x484, 0x488, 0x48C, 0x490, 0x494]:
        if off + 4 <= len(data):
            fields[f'{off:#x}_f'] = struct.unpack_from('<f', data, off)[0]
    return fields

def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # Scan DD
    print('[*] Scanning DDynamicActor...')
    dd_objects = scan_actors(pm, DD_VTABLE, 1)
    print(f'    Found {len(dd_objects)}: {[hex(a) for a in sorted(dd_objects)]}')

    # Scan DS
    print('[*] Scanning DStaticActor...')
    ds_objects = scan_actors(pm, DS_VTABLE, 3)
    print(f'    Found {len(ds_objects)}: {[hex(a) for a in sorted(ds_objects)]}')

    # Show DD reference object
    dd_ref = None
    if dd_objects:
        dd_ref = dd_objects[0]
        dd_fields = read_phys_fields(pm, dd_ref)
        print(f'\n[+] DD reference @ 0x{dd_ref:08X}:')
        print(f'    vtable=0x{dd_fields[0]:08X}  type8={dd_fields[8]}')
        print(f'    +0x460=0x{dd_fields.get(0x460,0):08X}')
        print(f'    +0x464=0x{dd_fields.get(0x464,0):08X}')
        print(f'    +0x468=0x{dd_fields.get(0x468,0):08X}')
        print(f'    +0x46C=0x{dd_fields.get(0x46C,0):08X}')
        print(f'    +0x470=0x{dd_fields.get(0x470,0):08X} (f={dd_fields.get("0x470_f",0):.4f})')
        print(f'    +0x474=0x{dd_fields.get(0x474,0):08X}')
        print(f'    +0x478=0x{dd_fields.get(0x478,0):08X}')
        print(f'    +0x47C=0x{dd_fields.get(0x47C,0):08X}')
        print(f'    +0x48C=0x{dd_fields.get(0x48C,0):08X}')

    # Revert mode
    if '--revert' in sys.argv:
        if not os.path.exists(BACKUP_FILE):
            print('[!] No backup')
            pm.close_process()
            return
        with open(BACKUP_FILE) as f:
            backup = json.load(f)
        for entry in backup['objects']:
            addr = entry['addr']
            orig = bytes.fromhex(entry['data'])
            pm.write_bytes(addr, orig, len(orig))
            print(f'  Reverted 0x{addr:08X}')
        print('[*] Done')
        pm.close_process()
        return

    # List DS objects
    print(f'\n  #  Address         idx   f460')
    print('  ' + '-' * 50)
    for i, addr in enumerate(ds_objects):
        fields = read_phys_fields(pm, addr)
        f46c = fields.get(0x46C, 0)
        f460 = fields.get(0x460, 0)
        print(f'  {i}  0x{addr:08X}  {f46c:>4}  0x{f460:08X}')

    if not dd_ref:
        print('\n[!] No DD object found - equip a dynamic hair first!')
        pm.close_process()
        return

    # Convert
    if '--all' in sys.argv:
        targets = list(range(len(ds_objects)))
    else:
        print(f'\n  Enter # to convert: ', end='', flush=True)
        choice = input().strip()
        if choice.lower() == 'all':
            targets = list(range(len(ds_objects)))
        else:
            targets = [int(x.strip()) for x in choice.split(',')]

    # Backup
    backup = {'time': time.strftime('%H:%M:%S'), 'objects': []}

    print(f'\n[*] Converting {len(targets)} objects using DD @ 0x{dd_ref:08X} as reference...')
    for idx in targets:
        ds_addr = ds_objects[idx]
        # Backup
        orig_data = pm.read_bytes(ds_addr, 0x4A0)
        backup['objects'].append({'addr': ds_addr, 'data': orig_data.hex()})

        # Read DD reference fields
        dd_f = read_phys_fields(pm, dd_ref)

        # Convert: write DD fields to DS object
        # +0x000: vtable
        pm.write_int(ds_addr, DD_VTABLE)
        # +0x008: type
        pm.write_int(ds_addr + 8, 1)
        # +0x460: phys block ptr (from DD ref)
        pm.write_int(ds_addr + 0x460, dd_f.get(0x460, 0))
        # +0x464: sub vtable
        pm.write_int(ds_addr + 0x464, dd_f.get(0x464, 0))
        # +0x468
        pm.write_int(ds_addr + 0x468, dd_f.get(0x468, 0))
        # +0x46C
        pm.write_int(ds_addr + 0x46C, dd_f.get(0x46C, 0))
        # +0x470: phys float
        pm.write_int(ds_addr + 0x470, dd_f.get(0x470, 0))
        # +0x474~0x49C: copy from DD ref
        for off in [0x474, 0x478, 0x47C, 0x480, 0x484, 0x488, 0x48C, 0x490, 0x494, 0x498, 0x49C]:
            pm.write_int(ds_addr + off, dd_f.get(off, 0))

        print(f'  [{idx}] 0x{ds_addr:08X} -> DD (phys_block=0x{dd_f.get(0x460,0):08X})')

    with open(BACKUP_FILE, 'w') as f:
        json.dump(backup, f)
    print(f'\n[*] Backup saved. Revert: py convert_v2.py --revert')

    pm.close_process()

if __name__ == '__main__':
    main()

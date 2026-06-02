# convert_static_to_dynamic.py — 将 DStaticActor 堆对象转换为 DDynamicActor
#
# 基于 IDA 工厂函数分析 (§86-§87):
#   +0x000: vtable    0x0284E00C -> 0x0284A9EC
#   +0x008: type      3 -> 1
#   +0x460: phys_ptr  current -> [0x02A43CA4]  (全局物理参数块)
#   +0x46C: phys_st   current -> 0
#   +0x470: phys_f    current -> [0x026A1B04]  (float)
#   +0x47C: pos       current -> 0,0,0  (vec3)
#   +0x48C: vel       current -> 0,0,0  (vec3)
#
# 用法:
#   py convert_static_to_dynamic.py              # 列出所有 DS 对象，选择转换
#   py convert_static_to_dynamic.py --all        # 转换全部
#   py convert_static_to_dynamic.py --addr 0x... # 转换指定地址
#   py convert_static_to_dynamic.py --revert     # 恢复原始值（从备份）

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

BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convert_backup.json')

# 全局物理参数地址 (来自 IDA 工厂函数分析)
PHYS_GLOBALS_PTR  = 0x02A43CA4   # mov eax, [2A43CA4] -> phys params block
PHYS_FLOAT_PTR    = 0x026A1B04   # float param

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


def scan_ds_objects(pm):
    """扫描所有真正的 DStaticActor 堆对象"""
    target = struct.pack('<I', DS_VTABLE)
    h = pm.process_handle
    found = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    mbi_size = ctypes.sizeof(mbi)

    while True:
        ret = kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size)
        if ret == 0:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0

        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in RW_PROTECT and size > 0:
            try:
                data = pm.read_bytes(base, size)
                if data:
                    off = 0
                    while True:
                        idx = data.find(target, off)
                        if idx < 0:
                            break
                        obj_addr = base + idx
                        if obj_addr >= TEXT_CEILING and idx + 12 <= len(data):
                            type8 = struct.unpack_from('<I', data, idx + 8)[0]
                            if type8 == 3:
                                found.append(obj_addr)
                        off = idx + 4
            except:
                pass

        next_addr = base + size
        if next_addr <= addr or next_addr > 0x7FFF0000:
            break
        addr = next_addr

    return found


def read_globals(pm):
    """读取全局物理参数"""
    try:
        phys_block_ptr = struct.unpack_from('<I', pm.read_bytes(PHYS_GLOBALS_PTR, 4), 0)[0]
    except:
        phys_block_ptr = 0

    try:
        phys_float = struct.unpack_from('<f', pm.read_bytes(PHYS_FLOAT_PTR, 4), 0)[0]
    except:
        phys_float = 0.0

    return phys_block_ptr, phys_float


def backup_obj(pm, addr):
    """备份对象原始数据"""
    data = pm.read_bytes(addr, 0x490)
    return data


def convert_obj(pm, addr, phys_block_ptr, phys_float):
    """执行 Static -> Dynamic 转换"""
    # 读取原始值
    orig = pm.read_bytes(addr, 0x490)
    orig_fields = {}
    for off in [0, 8, 0x460, 0x464, 0x468, 0x46C, 0x470, 0x474, 0x478, 0x47C, 0x480, 0x484, 0x488, 0x48C]:
        orig_fields[off] = struct.unpack_from('<I', orig, off)[0]

    # 写入 Dynamic 值
    # +0x000: vtable -> DD_VTABLE
    pm.write_int(addr, DD_VTABLE)

    # +0x008: type -> 1
    pm.write_int(addr + 8, 1)

    # +0x460: phys_ptr -> globals block
    pm.write_int(addr + 0x460, phys_block_ptr)

    # +0x46C: phys state -> 0
    pm.write_int(addr + 0x46C, 0)

    # +0x470: phys float
    pm.write_float(addr + 0x470, phys_float)

    # +0x47C: position -> 0,0,0 (3 floats)
    pm.write_float(addr + 0x47C, 0.0)
    pm.write_float(addr + 0x480, 0.0)
    pm.write_float(addr + 0x484, 0.0)

    # +0x48C: velocity -> 0,0,0 (3 floats)
    pm.write_float(addr + 0x48C, 0.0)
    pm.write_float(addr + 0x490, 0.0)
    pm.write_float(addr + 0x494, 0.0)

    return orig_fields


def revert_obj(pm, addr, orig_data):
    """恢复原始数据"""
    pm.write_bytes(addr, orig_data, len(orig_data))


def main():
    pid = find_pid()
    if not pid:
        print('[!] FreeStyle.exe not found')
        sys.exit(1)
    print(f'[+] PID: {pid}')

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 读取全局物理参数
    phys_block_ptr, phys_float = read_globals(pm)
    print(f'[+] Phys globals: block_ptr=0x{phys_block_ptr:08X}, float={phys_float:.6f}')

    if phys_block_ptr == 0:
        print('[!] WARNING: phys_block_ptr is NULL, conversion may not work!')

    # 扫描 DS 对象
    print('[*] Scanning DStaticActor objects...')
    ds_objects = scan_ds_objects(pm)
    print(f'[*] Found {len(ds_objects)} objects')

    if not ds_objects:
        print('[!] No DS objects found')
        pm.close_process()
        return

    # 列出对象
    print(f'\n{"#":>3}  {"Address":>12}  {"f004":>12}  {"f074":>6}  {"f460":>12}  {"f468":>12}  {"idx(f46C)":>10}')
    print('-' * 80)
    obj_data = []
    for i, addr in enumerate(ds_objects):
        data = backup_obj(pm, addr)
        if not data:
            continue
        f004 = struct.unpack_from('<I', data, 0x04)[0]
        f074 = struct.unpack_from('<I', data, 0x74)[0]
        f460 = struct.unpack_from('<I', data, 0x460)[0]
        f468 = struct.unpack_from('<I', data, 0x468)[0]
        f46c = struct.unpack_from('<I', data, 0x46C)[0]
        obj_data.append((addr, data))
        print(f'{i:>3}  0x{addr:08X}  0x{f004:08X}  0x{f074:04X}  0x{f460:08X}  0x{f468:08X}  {f46c:>10}')

    # Revert mode
    if '--revert' in sys.argv:
        if not os.path.exists(BACKUP_FILE):
            print('[!] No backup file found')
            pm.close_process()
            return
        with open(BACKUP_FILE, 'rb') as f:
            # backup is json with base64 encoded data
            pass
        # Revert from saved backup
        with open(BACKUP_FILE, 'r') as f:
            backup = json.load(f)
        for entry in backup['objects']:
            addr = entry['addr']
            orig = bytes.fromhex(entry['data'])
            revert_obj(pm, addr, orig)
            print(f'  Reverted 0x{addr:08X}')
        print('[*] All objects reverted')
        pm.close_process()
        return

    # 选择转换目标
    if '--all' in sys.argv:
        targets = list(range(len(obj_data)))
    elif '--addr' in sys.argv:
        target_addr = int(sys.argv[sys.argv.index('--addr') + 1], 16)
        targets = [i for i, (a, _) in enumerate(obj_data) if a == target_addr]
        if not targets:
            print(f'[!] Address 0x{target_addr:08X} not found')
            pm.close_process()
            return
    else:
        print(f'\n  Enter # to convert (comma-separated), or "all": ', end='', flush=True)
        # Read from stdin
        choice = input().strip()
        if choice.lower() == 'all':
            targets = list(range(len(obj_data)))
        else:
            targets = [int(x.strip()) for x in choice.split(',')]

    # 备份
    backup = {
        'time': time.strftime('%H:%M:%S'),
        'phys_block_ptr': phys_block_ptr,
        'phys_float': phys_float,
        'objects': []
    }

    print(f'\n[*] Converting {len(targets)} objects...')
    for idx in targets:
        addr, data = obj_data[idx]
        backup['objects'].append({
            'addr': addr,
            'data': data[:0x490].hex()
        })

        orig_fields = convert_obj(pm, addr, phys_block_ptr, phys_float)
        print(f'  [{idx}] 0x{addr:08X} converted')
        print(f'       vtable: 0x{orig_fields[0]:08X} -> 0x{DD_VTABLE:08X}')
        print(f'       type8:  {orig_fields[8]} -> 1')
        print(f'       f460:   0x{orig_fields[0x460]:08X} -> 0x{phys_block_ptr:08X}')

    # Save backup
    with open(BACKUP_FILE, 'w') as f:
        json.dump(backup, f)
    print(f'\n[*] Backup saved to {BACKUP_FILE}')
    print(f'[*] To revert: py convert_static_to_dynamic.py --revert')
    print(f'[*] Check in-game: hair should start moving if this is the right object')
    print(f'[*] If game crashes, the object was wrong or fields incomplete')

    pm.close_process()


if __name__ == '__main__':
    main()

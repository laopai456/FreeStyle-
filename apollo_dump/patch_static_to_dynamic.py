# patch_actor.py - 交互式DStaticActor->DDynamicActor转换
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem
import psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

VTABLE_STATIC  = 0x0284E00C
VTABLE_DYNAMIC = 0x0284A9EC

def check_vtable(pm, addr, name):
    try:
        val = pm.read_bytes(addr, 4)
        v = struct.unpack('<I', val)[0]
        print(f'  {name} @ 0x{addr:08X} -> 0x{v:08X} (OK)')
        return True
    except:
        print(f'  {name} @ 0x{addr:08X} -> 不可读!')
        return False

def find_statics(pm, no_filter=False):
    vt_bytes = struct.pack('<I', VTABLE_STATIC)
    results = []
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if not data: continue
            off = 0
            while True:
                idx = data.find(vt_bytes, off)
                if idx == -1: break
                obj_addr = addr + idx
                raw = pm.read_bytes(obj_addr, 64)
                f = struct.unpack('<16I', raw)
                if no_filter or f[2] == 3:  # +8 == 3
                    results.append((obj_addr, f))
                off = idx + 4
        except:
            continue
    return results

def patch_to_dynamic(pm, addr):
    # 改vtable
    pm.write_bytes(addr, struct.pack('<I', VTABLE_DYNAMIC), 4)
    # 改+8: 3->1
    pm.write_bytes(addr + 8, struct.pack('<I', 1), 4)
    print(f'  已patch 0x{addr:08X}: vtable->Dynamic, type->1')

def restore_to_static(pm, addr):
    pm.write_bytes(addr, struct.pack('<I', VTABLE_STATIC), 4)
    pm.write_bytes(addr + 8, struct.pack('<I', 3), 4)
    print(f'  已恢复 0x{addr:08X}: vtable->Static, type->3')

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 验证vtable地址
    print('验证vtable:')
    vt_ok = True
    vt_ok = check_vtable(pm, VTABLE_STATIC, 'DStaticActor') and vt_ok
    vt_ok = check_vtable(pm, VTABLE_DYNAMIC, 'DDynamicActor') and vt_ok

    if not vt_ok:
        print('  vtable地址不可读，可能游戏版本变化')
        # 尝试搜模块基址
        mod = pymem.process.module_from_name(pm.process_handle, 'FreeStyle.exe')
        print(f'  FreeStyle.exe base: 0x{mod.lpBaseOfDll:08X}')

    # 验证扫描能力：搜itemcode
    test_target = b'50125461'
    test_count = 0
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if data and test_target in data:
                test_count += data.count(test_target)
        except:
            continue
    print(f'  "50125461" 在内存中出现 {test_count} 次')

    statics = find_statics(pm)
    print(f'找到 {len(statics)} 个 DStaticActor\n')

    for i, (addr, f) in enumerate(statics):
        print(f'[{i}] 0x{addr:08X}: +4=0x{f[1]:08X} +8={f[2]} +C=0x{f[3]:08X} +10=0x{f[4]:08X} scale=({f[9]:.2f},{f[10]:.2f},{f[11]:.2f})')

    print()
    print('命令:')
    print('  p <编号>   - patch该对象为Dynamic')
    print('  r <编号>   - 恢复为Static')
    print('  r all      - 恢复所有')
    print('  scan       - 重新扫描(+8=3过滤)')
    print('  scanall    - 扫描所有vtable匹配(不过滤)')
    print('  q          - 退出')

    patched = set()
    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd == 'scan':
                statics = find_statics(pm)
                print(f'重新扫描: {len(statics)} 个')
                for i, (addr, f) in enumerate(statics):
                    print(f'[{i}] 0x{addr:08X}: +8={f[2]}')
            elif cmd == 'scanall':
                all_hits = find_statics(pm, no_filter=True)
                print(f'所有vtable匹配: {len(all_hits)} 个')
                for i, (addr, f) in enumerate(all_hits[:30]):
                    print(f'[{i}] 0x{addr:08X}: +4=0x{f[1]:08X} +8={f[2]} +C=0x{f[3]:08X}')
            elif cmd.startswith('p '):
                idx = int(cmd.split()[1])
                if 0 <= idx < len(statics):
                    patch_to_dynamic(pm, statics[idx][0])
                    patched.add(idx)
                else:
                    print('索引越界')
            elif cmd.startswith('r '):
                arg = cmd.split()[1]
                if arg == 'all':
                    for idx in patched:
                        restore_to_static(pm, statics[idx][0])
                    patched.clear()
                else:
                    idx = int(arg)
                    if 0 <= idx < len(statics):
                        restore_to_static(pm, statics[idx][0])
                        patched.discard(idx)
    except (KeyboardInterrupt, EOFError):
        pass

    # 退出前恢复
    if patched:
        print('恢复所有patch...')
        for idx in patched:
            restore_to_static(pm, statics[idx][0])

    pm.close_process()

if __name__ == '__main__':
    main()

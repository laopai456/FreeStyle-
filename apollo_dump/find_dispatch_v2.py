# find_dispatch_v2.py - 找Static/Dynamic工厂调用者的调用者（真正的分发点）
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def search_callers(pm, target, label, range_start=0x00401000, range_end=0x02A00000):
    """搜索E8调用到target的所有位置"""
    results = []
    target_bytes = struct.pack('<I', target)
    for page in range(range_start, range_end, 0x10000):
        try:
            data = pm.read_bytes(page, 0x10000)
            for i in range(len(data) - 5):
                if data[i] == 0xE8:
                    rel = struct.unpack_from('<i', data, i+1)[0]
                    if page + i + 5 + rel == target:
                        results.append(page + i)
        except:
            continue
    return results

def search_pointer(pm, target, range_start=0x00401000, range_end=0x7FFF0000):
    """搜索函数指针存储"""
    target_bytes = struct.pack('<I', target)
    results = []
    for page in range(range_start, range_end, 0x10000):
        try:
            data = pm.read_bytes(page, 0x10000)
            off = 0
            while True:
                idx = data.find(target_bytes, off)
                if idx == -1:
                    break
                results.append(page + idx)
                off = idx + 1
                if len(results) >= 10:
                    return results
        except:
            continue
    return results

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 工厂调用者函数
    callers = {
        0x0231B930: 'Static#1_CreateActor',
        0x0231BDB0: 'Static#2_CreateActor',
        0x02299730: 'Dynamic#1_CreateActor',
        0x022F27B0: 'Dynamic#2_CreateActor',
    }

    for addr, name in callers.items():
        print(f'\n=== {name} (0x{addr:08X}) ===')
        
        # 搜索E8调用者
        e8_callers = search_callers(pm, addr, name)
        if e8_callers:
            print(f'  E8调用者:')
            for c in e8_callers:
                ctx = pm.read_bytes(max(0x00401000, c-8), 24)
                hex_str = ' '.join(f'{b:02x}' for b in ctx)
                print(f'    0x{c:08X}: {hex_str}')
        else:
            print(f'  无E8调用者')
        
        # 搜索函数指针
        ptrs = search_pointer(pm, addr)
        if ptrs:
            print(f'  函数指针存储:')
            for p in ptrs:
                # 读取前后上下文
                ctx = pm.read_bytes(max(0x00401000, p-16), 48)
                hex_str = ' '.join(f'{b:02x}' for b in ctx)
                print(f'    0x{p:08X}: {hex_str}')
        else:
            print(f'  无函数指针存储')

    # 特殊：检查这些调用者是否在某个vtable中
    # 如果在vtable中，它们就是虚函数
    print(f'\n=== Vtable分析 ===')
    # 已知vtable: Static=0x0284E00C, Dynamic=0x0284A9EC
    # 但还有其他vtable可能包含这些函数
    for addr, name in callers.items():
        # 搜索是否紧跟在某个vtable首地址之后
        ptrs = search_pointer(pm, addr, 0x0284E000, 0x0284F000)
        if ptrs:
            for p in ptrs:
                offset = p - 0x0284E00C
                print(f'  {name}: 在Static vtable+0x{offset:X} (0x{p:08X})')
        ptrs2 = search_pointer(pm, addr, 0x0284A900, 0x0284B000)
        if ptrs2:
            for p in ptrs2:
                offset = p - 0x0284A9EC
                print(f'  {name}: 在Dynamic vtable+0x{offset:X} (0x{p:08X})')

    # 读完整vtable看看有没有这些函数
    print(f'\n=== Static vtable 详细 ===')
    vt = pm.read_bytes(0x0284E00C, 0x80)
    for i in range(0, 0x80, 4):
        val = struct.unpack_from('<I', vt, i)[0]
        match = ''
        for addr, name in callers.items():
            if val == addr:
                match = f' <<< {name}'
        print(f'  +0x{i:02X}: 0x{val:08X}{match}')

    print(f'\n=== Dynamic vtable 详细 ===')
    vt2 = pm.read_bytes(0x0284A9EC, 0x80)
    for i in range(0, 0x80, 4):
        val = struct.unpack_from('<I', vt2, i)[0]
        match = ''
        for addr, name in callers.items():
            if val == addr:
                match = f' <<< {name}'
        print(f'  +0x{i:02X}: 0x{val:08X}{match}')

    pm.close_process()

if __name__ == '__main__':
    main()

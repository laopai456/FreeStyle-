# trace_dispatch.py - 追踪分发点到更高层
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def find_func_start(pm, addr, max_back=0x400):
    start = max(0x00401000, addr - max_back)
    data = pm.read_bytes(start, addr - start + 16)
    base = start
    for i in range(len(data) - 4, 4, -1):
        if data[i] == 0x55 and data[i+1] == 0x8B and data[i+2] == 0xEC:
            if i > 0 and data[i-1] == 0xCC:
                return base + i
    return None

def search_e8_callers(pm, target, start=0x00401000, end=0x02A00000):
    results = []
    for page in range(start, end, 0x10000):
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

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # Level 2 callers (call the functions that call factories)
    level2_targets = [
        (0x0231942C, 'calls Static#1'),
        (0x0231952B, 'calls Static#2'),
        (0x022FA39B, 'calls Dynamic#1'),
    ]

    for addr, desc in level2_targets:
        func = find_func_start(pm, addr)
        print(f'\n=== {desc}: caller @ 0x{addr:08X} ===')
        if func:
            print(f'  函数入口: 0x{func:08X}')
            # 检查这个函数内是否调用了Dynamic工厂相关函数
            func_size = min(0x800, addr - func + 0x100)
            data = pm.read_bytes(func, func_size)
            
            # 搜索这个函数内所有E8 call的目标
            dynamic_targets = {
                0x02299730: 'Dynamic#1_Create',
                0x022F27B0: 'Dynamic#2_Create',
                0x0229AF00: 'DynamicFactory',
            }
            static_targets = {
                0x0231B930: 'Static#1_Create',
                0x0231BDB0: 'Static#2_Create',
                0x0236B340: 'StaticFactory',
            }
            
            calls_found = []
            for i in range(len(data) - 5):
                if data[i] == 0xE8:
                    rel = struct.unpack_from('<i', data, i+1)[0]
                    target = func + i + 5 + rel
                    if target in dynamic_targets:
                        calls_found.append((func+i, dynamic_targets[target]))
                    elif target in static_targets:
                        calls_found.append((func+i, static_targets[target]))
            
            if calls_found:
                for ca, cn in calls_found:
                    print(f'  内部调用: 0x{ca:08X} -> {cn}')
            else:
                print(f'  无工厂相关调用（只有其他E8）')
            
            # 找这个函数的调用者
            callers = search_e8_callers(pm, func)
            print(f'  函数调用者 ({len(callers)}):')
            for c in callers[:5]:
                ctx = pm.read_bytes(max(0x00401000, c-8), 24)
                hex_str = ' '.join(f'{b:02x}' for b in ctx)
                print(f'    0x{c:08X}: {hex_str}')
        else:
            print(f'  未找到函数入口')

    # 特别分析：Static#1的调用者(0x0231942C)附近是否有Dynamic调用
    print(f'\n=== 0x023194xx区域详细分析 ===')
    func_addr = find_func_start(pm, 0x0231942C)
    if func_addr:
        print(f'函数: 0x{func_addr:08X}')
        data = pm.read_bytes(func_addr, 0x400)
        for i in range(0, min(len(data), 0x400), 16):
            addr = func_addr + i
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            marker = ''
            if addr <= 0x0231942C < addr + 16:
                marker = ' <<< calls Static#1'
            if addr <= 0x0231952B < addr + 16:
                marker = ' <<< calls Static#2'
            print(f'  {addr:08X}: {hex_str}{marker}')

    pm.close_process()

if __name__ == '__main__':
    main()

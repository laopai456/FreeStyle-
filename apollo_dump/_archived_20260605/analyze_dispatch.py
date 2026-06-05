# analyze_dispatch.py - 分析Static/Dynamic工厂调用点的分发逻辑
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def find_func_start(pm, addr, max_back=512):
    data = pm.read_bytes(max(0x00401000, addr - max_back), max_back + 16)
    base = max(0x00401000, addr - max_back)
    for i in range(max_back, 4, -1):
        # CC padding + 55 8B EC = INT3... push ebp; mov ebp, esp
        if data[i] == 0x55 and data[i+1] == 0x8B and data[i+2] == 0xEC:
            # 检查前面是否有CC（padding）
            if data[i-1] == 0xCC or data[i-2] == 0xCC:
                return base + i
    return None

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 分析每个调用点的上下文
    callers = [
        (0x0231BB0C, 'Static#1', 0x0236B340),
        (0x0231BECD, 'Static#2', 0x0236B340),
        (0x0229973C, 'Dynamic#1', 0x0229AF00),
        (0x022F27D9, 'Dynamic#2', 0x0229AF00),
    ]

    for call_addr, name, target in callers:
        print(f'\n{"="*60}')
        print(f'调用点: {name} @ 0x{call_addr:08X} -> 0x{target:08X}')
        print(f'{"="*60}')

        # 找函数入口
        func_start = find_func_start(pm, call_addr)
        if func_start:
            print(f'函数入口: 0x{func_start:08X}')
            dump_start = func_start
        else:
            dump_start = call_addr - 0x80
            print(f'未找到入口，从 0x{dump_start:08X} 开始')

        # dump调用点周围大量代码
        size = 0x200 if func_start else 0x180
        data = pm.read_bytes(dump_start, size)
        for i in range(0, len(data), 16):
            addr = dump_start + i
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            marker = ''
            if addr <= call_addr < addr + 16:
                marker = ' <<< CALL'
            print(f'  {addr:08X}: {hex_str}{marker}')

    # 特别分析：找到Static和Dynamic调用点是否在同一个函数中
    # 0x0231BB0C 和 0x0231BECD 相距很近，可能在同一函数
    # 检查 0x0229973C 附近是否也有对Static的调用
    print(f'\n{"="*60}')
    print(f'交叉分析：搜索0x022997xx附近的其他工厂调用')
    print(f'{"="*60}')
    
    # 在0x0229973C周围大范围搜索所有E8 call
    data = pm.read_bytes(0x02299000, 0x1000)
    for i in range(len(data) - 5):
        if data[i] == 0xE8:
            rel = struct.unpack_from('<i', data, i+1)[0]
            call_target = 0x02299000 + i + 5 + rel
            if call_target in (0x0236B340, 0x0229AF00):
                addr = 0x02299000 + i
                name = 'STATIC' if call_target == 0x0236B340 else 'DYNAMIC'
                print(f'  0x{addr:08X}: call {name} (0x{call_target:08X})')

    # 在0x0231Bxxx附近搜索所有工厂调用
    print(f'\n0x0231Bxxx附近的工厂调用:')
    data2 = pm.read_bytes(0x0231B000, 0x1000)
    for i in range(len(data2) - 5):
        if data2[i] == 0xE8:
            rel = struct.unpack_from('<i', data2, i+1)[0]
            call_target = 0x0231B000 + i + 5 + rel
            if call_target in (0x0236B340, 0x0229AF00):
                addr = 0x0231B000 + i
                name = 'STATIC' if call_target == 0x0236B340 else 'DYNAMIC'
                print(f'  0x{addr:08X}: call {name} (0x{call_target:08X})')

    pm.close_process()

if __name__ == '__main__':
    main()

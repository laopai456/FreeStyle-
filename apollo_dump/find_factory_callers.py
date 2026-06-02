# find_factory_callers.py - 搜索工厂函数地址在内存中的存储位置
# 同时分析新发现的3个Dynamic vtable引用点的上下文
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# 工厂函数地址
STATIC_FACTORY  = struct.pack('<I', 0x0236B36B)
DYNAMIC_FACTORY = struct.pack('<I', 0x0229AF00)

def scan_for_pattern(pm, pattern, label, start=0x00401000, end=0x7FFF0000, page_size=0x10000):
    """全内存搜索4字节模式"""
    results = []
    for addr in range(start, end, page_size):
        try:
            data = pm.read_bytes(addr, page_size)
            if not data:
                continue
            off = 0
            while True:
                idx = data.find(pattern, off)
                if idx == -1:
                    break
                hit_addr = addr + idx
                results.append(hit_addr)
                off = idx + 1
        except:
            continue
    return results

def read_context(pm, addr, before=16, after=32):
    """读取地址周围上下文"""
    try:
        start = addr - before
        data = pm.read_bytes(start, before + after)
        return data
    except:
        return None

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 1. 搜索Static工厂地址 0x0236B36B
    print(f'\n=== 搜索 Static工厂 0x0236B36B ===')
    hits = scan_for_pattern(pm, STATIC_FACTORY, 'StaticFactory')
    for addr in hits:
        ctx = read_context(pm, addr, 16, 32)
        if ctx:
            hex_pre = ' '.join(f'{b:02x}' for b in ctx[:16])
            hex_val = ' '.join(f'{b:02x}' for b in ctx[16:20])
            hex_post = ' '.join(f'{b:02x}' for b in ctx[20:48])
            print(f'  0x{addr:08X}: ...{hex_pre} [{hex_val}] {hex_post}')
        else:
            print(f'  0x{addr:08X}: (无法读取上下文)')
    print(f'  共 {len(hits)} 处')

    # 2. 搜索Dynamic工厂地址 0x0229AF00
    print(f'\n=== 搜索 Dynamic工厂 0x0229AF00 ===')
    hits2 = scan_for_pattern(pm, DYNAMIC_FACTORY, 'DynamicFactory')
    for addr in hits2:
        ctx = read_context(pm, addr, 16, 32)
        if ctx:
            hex_pre = ' '.join(f'{b:02x}' for b in ctx[:16])
            hex_val = ' '.join(f'{b:02x}' for b in ctx[16:20])
            hex_post = ' '.join(f'{b:02x}' for b in ctx[20:48])
            print(f'  0x{addr:08X}: ...{hex_pre} [{hex_val}] {hex_post}')
        else:
            print(f'  0x{addr:08X}: (无法读取上下文)')
    print(f'  共 {len(hits2)} 处')

    # 3. 分析3个新的Dynamic vtable引用点
    new_refs = [
        (0x022F28CB, 'DynRef1'),
        (0x022FA6A9, 'DynRef2'),
        (0x0230436C, 'DynRef3'),
    ]
    print(f'\n=== 新Dynamic引用点分析 ===')
    for ref_addr, name in new_refs:
        # 向前搜索函数起始点（找55 8B EC或83 EC等常见prologue）
        ctx = read_context(pm, ref_addr, 128, 32)
        if ctx:
            print(f'\n  {name} @ 0x{ref_addr:08X}:')
            # 找函数入口 - 向前找prologue
            func_start = None
            for i in range(128, 0, -1):
                # 55 8B EC = push ebp; mov ebp, esp
                if i >= 2 and ctx[i-2] == 0x55 and ctx[i-1] == 0x8B and ctx[i] == 0xEC:
                    func_start = ref_addr - 128 + i - 2
                    break
                # 83 EC xx = sub esp, xx
                if i >= 1 and ctx[i-1] == 0x83 and ctx[i] == 0xEC:
                    func_start = ref_addr - 128 + i - 1
                    break
            if func_start:
                print(f'    函数入口: 0x{func_start:08X}')
            else:
                print(f'    未找到函数入口（可能由其他方式进入）')

            # 显示vtable赋值附近的代码
            vtable_offset = 128  # 在ctx中的偏移
            print(f'    上下文(vtable赋值附近):')
            for i in range(max(0, vtable_offset-16), min(len(ctx), vtable_offset+20)):
                marker = " <<< vtable" if i == vtable_offset else ""
                print(f'      {ref_addr - 128 + i:08X}: {ctx[i]:02x}{marker}')

    # 4. 读vtable内容
    print(f'\n=== Vtable内容 ===')
    for vt_addr, vt_name in [(0x0284E00C, 'Static'), (0x0284A9EC, 'Dynamic')]:
        try:
            vt_data = pm.read_bytes(vt_addr, 64)
            print(f'\n  {vt_name} vtable @ 0x{vt_addr:08X}:')
            for i in range(0, 64, 4):
                val = struct.unpack_from('<I', vt_data, i)[0]
                print(f'    +{i:02X}: 0x{val:08X}')
        except Exception as e:
            print(f'  {vt_name} vtable: 读取失败 ({e})')

    pm.close_process()

if __name__ == '__main__':
    main()

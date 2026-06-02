# find_callers_v2.py - 用正确的工厂入口地址搜索调用者
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 正确的工厂入口地址
    targets = {
        0x0236B340: 'StaticFactory (DStaticActor)',
        0x0229AF00: 'DynamicFactory (DDynamicActor)',
        0x0229AD50: 'DynamicCtor_short (0x0229AD50)',
        0x0229ADF0: 'DynamicCtor_medium (0x0229ADF0)',
        0x0229AE80: 'DynamicDtor (vtable[0])',
        0x0236B4C0: 'StaticDtor (vtable[0])',
    }

    # 搜索E8直接调用
    for target, name in targets.items():
        print(f'\n=== 搜索 call {name} (0x{target:08X}) ===')
        found = 0
        for page in range(0x00401000, 0x02A00000, 0x10000):
            try:
                data = pm.read_bytes(page, 0x10000)
                for i in range(len(data) - 5):
                    if data[i] == 0xE8:
                        rel = struct.unpack_from('<i', data, i+1)[0]
                        call_target = page + i + 5 + rel
                        if call_target == target:
                            addr = page + i
                            found += 1
                            # 读上下文
                            ctx_start = max(0, i - 12)
                            ctx_end = min(len(data), i + 20)
                            ctx = data[ctx_start:ctx_end]
                            hex_str = ' '.join(f'{b:02x}' for b in ctx)
                            print(f'  0x{addr:08X}: {hex_str}')
            except:
                continue
        if found == 0:
            # 搜索函数指针存储
            ptr_bytes = struct.pack('<I', target)
            ptr_found = 0
            for page in range(0x00401000, 0x7FFF0000, 0x10000):
                try:
                    data = pm.read_bytes(page, 0x10000)
                    idx = data.find(ptr_bytes)
                    if idx != -1:
                        hit = page + idx
                        ctx = pm.read_bytes(max(0x00401000, hit-8), 32)
                        hex_str = ' '.join(f'{b:02x}' for b in ctx)
                        print(f'  函数指针 @ 0x{hit:08X}: {hex_str}')
                        ptr_found += 1
                        if ptr_found >= 5:
                            break
                except:
                    continue
            if ptr_found == 0:
                print(f'  未找到直接调用或函数指针')

    pm.close_process()

if __name__ == '__main__':
    main()

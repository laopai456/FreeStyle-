# find_crc_callers.py - 找CRC校验的调用者和校验失败处理
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

    # 1. 读间接调用目标: 0x02F899C (CRC函数中的 ff 15 9c f9 68 02)
    print('=== 间接调用目标 ===')
    for iat_addr in [0x02F899C, 0x02F8EC, 0x02F9C8]:
        try:
            val = struct.unpack('<I', pm.read_bytes(iat_addr, 4))[0]
            # 尝试读函数名
            name_bytes = pm.read_bytes(val, 16)
            hex_str = ' '.join(f'{b:02x}' for b in name_bytes)
            print(f'  [0x{iat_addr:08X}] = 0x{val:08X}: {hex_str}')
        except:
            print(f'  [0x{iat_addr:08X}]: 读取失败')

    # 2. 搜索E8调用到0x0243DAB0 (CRC计算函数)
    target = 0x0243DAB0
    print(f'\n=== 搜索 call 0x{target:08X} ===')
    for page in range(0x00401000, 0x02A00000, 0x10000):
        try:
            data = pm.read_bytes(page, 0x10000)
            for i in range(len(data) - 5):
                if data[i] == 0xE8:
                    rel = struct.unpack_from('<i', data, i+1)[0]
                    call_target = page + i + 5 + rel
                    if call_target == target:
                        addr = page + i
                        # 读上下文
                        ctx_start = max(0, i - 16)
                        ctx_end = min(len(data), i + 16)
                        ctx = data[ctx_start:ctx_end]
                        hex_str = ' '.join(f'{b:02x}' for b in ctx)
                        print(f'  0x{addr:08X}: call -> 0x{target:08X}')
                        print(f'    {hex_str}')
        except:
            continue

    # 3. 搜索0x0243DAB0作为存储的函数指针
    target_bytes = struct.pack('<I', 0x0243DAB0)
    print(f'\n=== 搜索函数指针 0x0243DAB0 ===')
    found_ptrs = []
    for page in range(0x00401000, 0x7FFF0000, 0x10000):
        try:
            data = pm.read_bytes(page, 0x10000)
            off = 0
            while True:
                idx = data.find(target_bytes, off)
                if idx == -1:
                    break
                hit = page + idx
                found_ptrs.append(hit)
                off = idx + 1
        except:
            continue
    print(f'  找到 {len(found_ptrs)} 处')
    for addr in found_ptrs[:10]:
        ctx = pm.read_bytes(addr - 8, 32)
        hex_str = ' '.join(f'{b:02x}' for b in ctx)
        print(f'  0x{addr:08X}: {hex_str}')

    # 4. 检查CRC函数后的代码 - 可能在调用者中做比较
    # 读0x0243DB10函数更完整的代码
    print(f'\n=== CRC后续函数 0x0243DB10 详细 ===')
    data = pm.read_bytes(0x0243DB10, 0x100)
    for i in range(0, len(data), 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        print(f'  {0x0243DB10+i:08X}: {hex_str}')

    pm.close_process()

if __name__ == '__main__':
    main()

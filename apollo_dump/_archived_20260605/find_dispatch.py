# find_dispatch.py - 分析工厂函数上下文，找Static/Dynamic分发点
# 关键：0x0236B36B不是标准函数入口(以call开头)，可能是更大函数内的label
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

    # 1. 读Static工厂(0x0236B36B)之前的代码，找函数边界
    print('=== Static工厂 0x0236B36B 之前代码 ===')
    # 读0x236B000到0x236B400 (包括工厂前后)
    data = pm.read_bytes(0x0236B200, 0x400)
    for i in range(0, len(data), 16):
        addr = 0x0236B200 + i
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        marker = ''
        if addr == 0x0236B36B:
            marker = ' <<< factory start'
        elif addr == 0x0236B38E:
            marker = ' <<< vtable=Static'
        elif addr == 0x0236B4C0:
            marker = ' <<< vtable[0]'
        elif addr == 0x0236B51D:
            marker = ' <<< vtable=Static #2'
        print(f'  {addr:08X}: {hex_str}{marker}')

    # 2. 读Dynamic工厂(0x0229AF00)之前的代码
    print('\n=== Dynamic工厂 0x0229AF00 之前代码 ===')
    data2 = pm.read_bytes(0x0229AD00, 0x300)
    for i in range(0, len(data2), 16):
        addr = 0x0229AD00 + i
        chunk = data2[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        marker = ''
        if addr == 0x0229AF00:
            marker = ' <<< factory start'
        elif 0x0229AD9C <= addr <= 0x0229AD9F:
            marker = ' <<< vtable=Dynamic'
        print(f'  {addr:08X}: {hex_str}{marker}')

    # 3. 关键搜索：找跳转到0x0236B36B的指令
    # jmp rel32 = E9 xx xx xx xx
    # 或者 jmp reg = FF xx
    target_s = 0x0236B36B
    target_d = 0x0229AF00
    print(f'\n=== 搜索跳转到工厂的指令 ===')
    for page in range(0x00401000, 0x02A00000, 0x10000):
        try:
            data = pm.read_bytes(page, 0x10000)
            for i in range(len(data) - 5):
                # E9 = jmp rel32
                if data[i] == 0xE9:
                    rel = struct.unpack_from('<i', data, i+1)[0]
                    jmp_target = page + i + 5 + rel
                    if jmp_target in (target_s, target_d):
                        addr = page + i
                        name = 'Static' if jmp_target == target_s else 'Dynamic'
                        print(f'  jmp {name}: 0x{addr:08X} -> 0x{jmp_target:08X}')
                # 0F 84 = jz rel32
                if data[i] == 0x0F and i+5 < len(data) and data[i+1] == 0x84:
                    rel = struct.unpack_from('<i', data, i+2)[0]
                    jmp_target = page + i + 6 + rel
                    if jmp_target in (target_s, target_d):
                        addr = page + i
                        name = 'Static' if jmp_target == target_s else 'Dynamic'
                        print(f'  jz {name}: 0x{addr:08X} -> 0x{jmp_target:08X}')
                # 0F 85 = jnz rel32
                if data[i] == 0x0F and i+5 < len(data) and data[i+1] == 0x85:
                    rel = struct.unpack_from('<i', data, i+2)[0]
                    jmp_target = page + i + 6 + rel
                    if jmp_target in (target_s, target_d):
                        addr = page + i
                        name = 'Static' if jmp_target == target_s else 'Dynamic'
                        print(f'  jnz {name}: 0x{addr:08X} -> 0x{jmp_target:08X}')
        except:
            continue

    pm.close_process()

if __name__ == '__main__':
    main()

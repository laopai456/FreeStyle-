# find_vtable_refs.py - 扫描.text段中vtable常量的所有引用点
# 找到游戏在哪里决定创建Static vs Dynamic Actor
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

STATIC_VT  = struct.pack('<I', 0x0284E00C)   # 0C E0 84 02
DYNAMIC_VT = struct.pack('<I', 0x0284A9EC)   # EC A9 84 02

def scan_for_bytes(pm, pattern, label, start=0x00401000, end=0x03000000):
    """扫描范围内所有pattern出现位置"""
    results = []
    page_size = 0x10000  # 64KB chunks
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
                # 读前后各16字节上下文
                ctx_start = max(0, idx - 8)
                ctx_end = min(len(data), idx + 4 + 12)
                ctx = data[ctx_start:ctx_end]
                results.append((hit_addr, ctx, idx - ctx_start))
                off = idx + 1
        except:
            continue
    return results

def disasm_context(ctx, pattern_offset):
    """简单分析上下文字节"""
    lines = []
    for i in range(0, len(ctx), 1):
        marker = " <<<" if i == pattern_offset else ""
        lines.append(f'{ctx[i]:02x}{marker}')
    return ' '.join(lines[:24])

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 扫描Static vtable引用
    print(f'\n=== Static vtable 0x0284E00C 引用 ===')
    hits = scan_for_bytes(pm, STATIC_VT, 'Static')
    for addr, ctx, poff in hits:
        # 判断是否在代码段（通常0x00401000-0x02A00000）
        if 0x00401000 <= addr <= 0x02A00000:
            section = '.text'
        else:
            section = 'data?'
        # 检查前一个字节是否是mov立即数指令操作码
        pre_byte = ctx[poff - 1] if poff > 0 else 0
        # C7 = mov [reg], imm32 (常见vtable赋值)
        if pre_byte in (0xC7,):
            instr = 'mov [reg], imm32'
        elif (poff >= 2 and ctx[poff-2] == 0xC7):
            instr = 'mov [reg+disp], imm32'
        elif (poff >= 3 and ctx[poff-3] == 0xC7):
            instr = 'mov [reg+disp8], imm32'
        else:
            instr = f'pre={pre_byte:02x}'
        print(f'  0x{addr:08X} [{section}] {instr}')
        # 显示完整上下文
        hex_str = ' '.join(f'{b:02x}' for b in ctx)
        print(f'    {hex_str}')

    print(f'\n  共 {len([h for h in hits if 0x00401000 <= h[0] <= 0x02A00000])} 个代码段引用')

    # 扫描Dynamic vtable引用
    print(f'\n=== Dynamic vtable 0x0284A9EC 引用 ===')
    hits2 = scan_for_bytes(pm, DYNAMIC_VT, 'Dynamic')
    for addr, ctx, poff in hits2:
        if 0x00401000 <= addr <= 0x02A00000:
            section = '.text'
        else:
            section = 'data?'
        pre_byte = ctx[poff - 1] if poff > 0 else 0
        if pre_byte in (0xC7,):
            instr = 'mov [reg], imm32'
        elif (poff >= 2 and ctx[poff-2] == 0xC7):
            instr = 'mov [reg+disp], imm32'
        elif (poff >= 3 and ctx[poff-3] == 0xC7):
            instr = 'mov [reg+disp8], imm32'
        else:
            instr = f'pre={pre_byte:02x}'
        print(f'  0x{addr:08X} [{section}] {instr}')
        hex_str = ' '.join(f'{b:02x}' for b in ctx)
        print(f'    {hex_str}')

    print(f'\n  共 {len([h for h in hits2 if 0x00401000 <= h[0] <= 0x02A00000])} 个代码段引用')

    pm.close_process()

if __name__ == '__main__':
    main()

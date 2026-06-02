# find_crc.py - 搜索CRC校验相关代码
# 1. CRC32多项式 0xEDB88320
# 2. .text段范围引用
# 3. 常见校验循环模式
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# 搜索模式
patterns = {
    'CRC32_poly': struct.pack('<I', 0xEDB88320),
    'CRC32_poly_rev': struct.pack('<I', 0x04C11DB7),
    'text_start_00401000': struct.pack('<I', 0x00401000),
    'text_end_approx': struct.pack('<I', 0x02A00000),
}

def scan_text(pm, pattern, label, start=0x00401000, end=0x02A00000):
    """在.text段搜索"""
    results = []
    chunk = 0x10000
    for addr in range(start, end, chunk):
        try:
            data = pm.read_bytes(addr, chunk)
            if not data:
                continue
            off = 0
            while True:
                idx = data.find(pattern, off)
                if idx == -1:
                    break
                hit = addr + idx
                # 读上下文
                ctx_before = max(0, idx - 8)
                ctx_after = min(len(data), idx + len(pattern) + 16)
                ctx = data[ctx_before:ctx_after]
                hex_str = ' '.join(f'{b:02x}' for b in ctx)
                results.append((hit, hex_str))
                off = idx + 1
        except:
            continue
    return results

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    for name, pat in patterns.items():
        print(f'\n=== {name} ===')
        hits = scan_text(pm, pat, name)
        print(f'  找到 {len(hits)} 处')
        for addr, ctx in hits[:10]:
            print(f'  0x{addr:08X}: {ctx}')

    # 也搜索 mov reg, imm32 模式中引用 .text 边界的
    # push 0x00401000 = 68 00 10 40 00
    print(f'\n=== push 0x00401000 ===')
    hits = scan_text(pm, b'\x68\x00\x10\x40\x00', 'push_text_start')
    print(f'  找到 {len(hits)} 处')
    for addr, ctx in hits[:10]:
        print(f'  0x{addr:08X}: {ctx}')

    # 搜索 jmp 旁路模式: 之前CRC patch尝试的地址附近
    # 0x1A3C54 应该是 jz/jnz 跳过CRC失败处理
    print(f'\n=== 0x001A3C54 附近代码 ===')
    try:
        data = pm.read_bytes(0x001A3C00, 0x100)
        for i in range(0, 0x100, 16):
            hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f'  {0x001A3C00+i:08X}: {hex_str}  {ascii_str}')
    except Exception as e:
        print(f'  读取失败: {e}')

    pm.close_process()

if __name__ == '__main__':
    main()

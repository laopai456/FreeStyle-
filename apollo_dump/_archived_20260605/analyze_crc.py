# analyze_crc.py - 分析CRC校验函数，找到可patch的分支
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

def dump_region(pm, addr, size=512, highlight=None):
    """hex dump一个区域"""
    try:
        data = pm.read_bytes(addr, size)
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            marker = ''
            if highlight and addr + i <= highlight < addr + i + 16:
                marker = ' <<<'
            lines.append(f'  {addr+i:08X}: {hex_str}{marker}')
        return '\n'.join(lines)
    except:
        return '  (读取失败)'

def find_func_start(pm, addr, max_back=256):
    """向前搜索函数prologue"""
    try:
        data = pm.read_bytes(addr - max_back, max_back + 16)
        for i in range(max_back, 0, -1):
            # 55 8B EC = push ebp; mov ebp, esp
            if data[i-2] == 0x55 and data[i-1] == 0x8B and data[i] == 0xEC:
                return addr - max_back + i - 2
            # 83 EC xx = sub esp, xx (after push ebp)
            if i >= 3 and data[i-3] == 0x55 and data[i-2] == 0x8B and data[i-1] == 0xEC:
                return addr - max_back + i - 3
        return None
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

    # 1. 分析 0x021D86FF 附近的CRC32函数
    print('\n=== CRC32函数 @ 0x021D86FF ===')
    func_start = find_func_start(pm, 0x021D86FF)
    if func_start:
        print(f'  函数入口: 0x{func_start:08X}')
        print(dump_region(pm, func_start, 0x120, 0x021D86FF))
    else:
        print('  未找到函数入口，直接dump')
        print(dump_region(pm, 0x021D8600, 0x200, 0x021D86FF))

    # 2. 分析 0x0243DA1E 附近的CRC循环
    print('\n=== CRC展开循环 @ 0x0243DA1E ===')
    func_start2 = find_func_start(pm, 0x0243DA1E)
    if func_start2:
        print(f'  函数入口: 0x{func_start2:08X}')
        print(dump_region(pm, func_start2, 0x200, 0x0243DA1E))
    else:
        print('  未找到函数入口，直接dump')
        print(dump_region(pm, 0x0243D900, 0x300, 0x0243DA1E))

    # 3. 读取 0x01FC6EEA 附近 (存储.text起始地址的代码)
    print('\n=== .text引用 @ 0x01FC6EEA ===')
    print(dump_region(pm, 0x01FC6E00, 0x200, 0x01FC6EEA))

    # 4. 搜索常见的CRC校验失败处理模式
    # CRC失败通常会: call exit/TerminateProcess/断言
    # 搜索 "call [TerminateProcess]" 的间接调用
    kernel32_term = pm.read_bytes(0x01FC6E00, 0x200)

    # 5. 搜索条件跳转后跟 exit/abort 的模式
    # 在0x021D8xxx附近找jz/jnz后跟着call exit
    print('\n=== 搜索0x021D区域的jz/jnz模式 ===')
    try:
        data = pm.read_bytes(0x021D8000, 0x1000)
        for i in range(0, len(data) - 10):
            # 0F 84 xx xx xx xx = jz rel32 (6 bytes)
            # 0F 85 xx xx xx xx = jnz rel32 (6 bytes)
            if data[i] == 0x0F and data[i+1] in (0x84, 0x85):
                addr = 0x021D8000 + i
                rel = struct.unpack_from('<i', data, i+2)[0]
                target = addr + 6 + rel
                # 检查目标是否在合理范围内
                if 0x00401000 <= target <= 0x02A00000:
                    ctx = data[i:i+12]
                    hex_str = ' '.join(f'{b:02x}' for b in ctx)
                    jtype = 'jz' if data[i+1] == 0x84 else 'jnz'
                    print(f'  {addr:08X}: {hex_str}  {jtype} 0x{target:08X}')
    except Exception as e:
        print(f'  错误: {e}')

    pm.close_process()

if __name__ == '__main__':
    main()

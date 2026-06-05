# compare_item_records.py - 对比静态/动态物品的内存记录结构
# 找出哪个字段控制Actor类型
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

STATIC_IC = b'50125461'  # 美丽梦想发型(静态) pak767
DYNAMIC_IC = b'50125711' # 紫色超赛发型(动态) pak768

def find_item_records(pm, itemcode, dump_size=256):
    """搜索物品记录，返回完整dump"""
    results = []
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if not data:
                continue
            off = 0
            while True:
                idx = data.find(itemcode, off)
                if idx == -1:
                    break
                rec_addr = addr + idx
                # 验证是记录（+0x10应该有08 00 00 00）
                try:
                    check = pm.read_bytes(rec_addr + 0x10, 4)
                    if check == b'\x08\x00\x00\x00':
                        # dump大块区域
                        raw = pm.read_bytes(rec_addr, dump_size)
                        results.append((rec_addr, raw))
                except:
                    pass
                off = idx + 1
        except:
            continue
    return results

def print_hexdump(data, base_addr, width=16):
    """格式化hex dump"""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  +0x{i:03X} (0x{base_addr+i:08X}): {hex_part:<48s} {ascii_part}')
    return '\n'.join(lines)

def compare_records(static_recs, dynamic_recs):
    """比较静态和动态记录的差异"""
    if not static_recs or not dynamic_recs:
        print('  记录不足，无法比较')
        return

    s_addr, s_data = static_recs[0]
    d_addr, d_data = dynamic_recs[0]
    size = min(len(s_data), len(d_data))

    print(f'\n=== 差异对比 (前{size}字节) ===')
    print(f'  静态: 50125461(美丽梦想) @ 0x{s_addr:08X}')
    print(f'  动态: 50125711(紫色超赛) @ 0x{d_addr:08X}')
    print()

    diffs = []
    for i in range(0, size, 4):
        s_val = struct.unpack_from('<I', s_data, i)[0] if i+4 <= size else None
        d_val = struct.unpack_from('<I', d_data, i)[0] if i+4 <= size else None
        if s_val != d_val and s_val is not None and d_val is not None:
            # 尝试作为字符串
            s_str = s_data[i:i+16].split(b'\x00')[0].decode('ascii', errors='replace')
            d_str = d_data[i:i+16].split(b'\x00')[0].decode('ascii', errors='replace')
            is_str_s = all(32 <= b < 127 or b == 0 for b in s_data[i:i+16])
            is_str_d = all(32 <= b < 127 or b == 0 for b in d_data[i:i+16])
            is_str = is_str_s and is_str_d
            if is_str:
                diffs.append(f'  +0x{i:03X}: "{s_str}" vs "{d_str}"')
            else:
                diffs.append(f'  +0x{i:03X}: 0x{s_val:08X} ({s_val}) vs 0x{d_val:08X} ({d_val})')

    if diffs:
        print('差异字段:')
        for d in diffs:
            print(d)
    else:
        print('前{}字节完全相同！'.format(size))

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 搜索静态物品记录
    print('\n搜索 50125461 (美丽梦想, 静态, pak767)...')
    static_recs = find_item_records(pm, STATIC_IC)
    print(f'  找到 {len(static_recs)} 个记录')

    # 搜索动态物品记录
    print('搜索 50125711 (紫色超赛, 动态, pak768)...')
    dynamic_recs = find_item_records(pm, DYNAMIC_IC)
    print(f'  找到 {len(dynamic_recs)} 个记录')

    # 显示静态物品记录
    for i, (addr, data) in enumerate(static_recs[:3]):
        print(f'\n--- 静态记录 #{i} @ 0x{addr:08X} ---')
        print(print_hexdump(data, addr))

    # 显示动态物品记录
    for i, (addr, data) in enumerate(dynamic_recs[:3]):
        print(f'\n--- 动态记录 #{i} @ 0x{addr:08X} ---')
        print(print_hexdump(data, addr))

    # 对比
    compare_records(static_recs, dynamic_recs)

    pm.close_process()

if __name__ == '__main__':
    main()

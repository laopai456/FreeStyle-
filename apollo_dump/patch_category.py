# patch_category.py - 修改内存中50125461的category字段为2147
# 验证category是否控制动态/静态
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem, psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# 记录结构:
# +0x00: ItemCode (16B)  "50125461\0..."
# +0x1C: PakNum (16B)    "767\0..."
# +0x3C: Category (16B)  "\0..." -> "2147\0..."

TARGET_IC = b'50125461'
CATEGORY_OFFSET = 0x3C  # category字段偏移
NEW_CATEGORY = b'2147\x00'  # "2147" + null

def find_records(pm):
    """找所有包含50125461的记录"""
    results = []
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if not data: continue
            off = 0
            while True:
                idx = data.find(TARGET_IC, off)
                if idx == -1: break
                # 验证这是记录开头（+0x10处应该有 08 00 00 00）
                rec_addr = addr + idx
                try:
                    check = pm.read_bytes(rec_addr + 0x10, 4)
                    if check == b'\x08\x00\x00\x00':
                        # 读pak字段确认
                        pak = pm.read_bytes(rec_addr + 0x1C, 16)
                        cat = pm.read_bytes(rec_addr + 0x3C, 16)
                        results.append(rec_addr)
                        print(f'  记录 @ 0x{rec_addr:08X}: pak={pak[:3].decode()} cat={cat[:4].decode(errors="replace").strip(chr(0)) or "(空)"}')
                except:
                    pass
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

    print('搜索 50125461 记录...')
    records = find_records(pm)

    if not records:
        print('未找到记录')
        pm.close_process()
        return

    print(f'\n找到 {len(records)} 个记录')
    cmd = input('修改category为2147? (y/n): ').strip().lower()
    if cmd != 'y':
        pm.close_process()
        return

    for rec_addr in records:
        # 写 "2147\0" 到 +0x3C
        patch = NEW_CATEGORY + b'\x00' * (16 - len(NEW_CATEGORY))
        pm.write_bytes(rec_addr + CATEGORY_OFFSET, patch, 16)
        # 验证
        verify = pm.read_bytes(rec_addr + CATEGORY_OFFSET, 16)
        cat_str = verify[:4].decode(errors='replace')
        print(f'  0x{rec_addr:08X}: category -> "{cat_str}"')

    print('\n已修改! 进房间看效果')
    pm.close_process()

if __name__ == '__main__':
    main()

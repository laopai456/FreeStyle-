# patch_crc.py - 先patch CRC校验，才能安全hook内部函数
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem
import psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

# 已知的CRC校验点
CRC_PATCHES = [
    (0x1A3C54, b'\xEB\x1E'),   # jmp 跳过CRC检查
    (0x1BE222, b'\xEB\x1E'),   # jmp 跳过CRC检查
]

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 读原始字节
    print('当前CRC点:')
    for addr, patch in CRC_PATCHES:
        try:
            orig = pm.read_bytes(addr, 2)
            print(f'  0x{addr:08X}: {orig.hex()} -> {patch.hex()}')
        except Exception as e:
            print(f'  0x{addr:08X}: 不可读 ({e})')

    cmd = input('确认patch CRC? (y/n): ').strip().lower()
    if cmd != 'y':
        print('取消')
        pm.close_process()
        return

    for addr, patch in CRC_PATCHES:
        try:
            pm.write_bytes(addr, patch, len(patch))
            print(f'  0x{addr:08X}: patched')
        except Exception as e:
            print(f'  0x{addr:08X}: 写入失败 ({e})')

    print('CRC已patch，现在可以安全hook内部函数')

    # 验证函数地址
    print('\n验证函数地址:')
    func_addrs = [
        ('SetMotionType', 0x02297810),
        ('DStaticActor::ctor', 0x0236B36B),
        ('DDynamicActor::ctor', 0x0229AF00),
    ]
    for name, addr in func_addrs:
        try:
            raw = pm.read_bytes(addr, 8)
            print(f'  {name} @ 0x{addr:08X}: {raw.hex()}')
        except:
            print(f'  {name} @ 0x{addr:08X}: 不可读')

    pm.close_process()

if __name__ == '__main__':
    main()

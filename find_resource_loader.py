"""
find_resource_loader.py — 搜索 "item_2404" 字符串在内存中的位置
找到游戏根据 ItemCode 构造 .ppi 路径的函数

用法: py find_resource_loader.py
"""
import struct, sys
sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem, pymem.memory, pymem.process

HEAP_MIN = 0x01000000
HEAP_MAX = 0x7FFF0000

def scan_bytes(pm, needle_bytes, max_hits=200):
    hits = []
    addr = HEAP_MIN
    while addr < HEAP_MAX:
        try:
            mbi = pymem.memory.virtual_query(pm.process_handle, addr)
        except Exception:
            addr += 0x10000; continue
        next_addr = int(mbi.BaseAddress) + int(mbi.RegionSize)
        if int(mbi.State) != 0x1000:
            addr = next_addr; continue
        protect = int(mbi.Protect) & 0xFF
        if protect not in (0x04, 0x40, 0x02, 0x20):
            addr = next_addr; continue
        r_base = max(int(mbi.BaseAddress), HEAP_MIN)
        r_end = min(int(mbi.BaseAddress) + int(mbi.RegionSize), HEAP_MAX)
        r_size = r_end - r_base
        if r_size <= 0 or r_size > 0x1000000:
            addr = next_addr; continue
        try:
            data = pm.read_bytes(r_base, r_size)
        except Exception:
            addr = next_addr; continue
        pos = 0
        while len(hits) < max_hits:
            idx = data.find(needle_bytes, pos)
            if idx < 0: break
            hits.append(r_base + idx)
            pos = idx + 1
        addr = next_addr
    return hits

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("FreeStyle.exe not found or no admin"); return

    outpath = r"D:\py\反编译\FreeStyle\find_resource_result.txt"
    outf = open(outpath, 'w', encoding='utf-8')
    def log(s):
        print(s)
        outf.write(s + '\n')

    log(f"PID={pm.process_id}")

    # 搜索关键字符串
    targets = [b"item_2404", b"item_2405", b".ppi", b"fleece_hair"]

    for needle in targets:
        hits = scan_bytes(pm, needle)
        sep = "=" * 60
        log(f"\n{sep}")
        log(f"  '{needle.decode()}' — {len(hits)} hits")
        log(f"{sep}")

        # 按地址范围分组
        for addr in hits[:30]:
            try:
                # 读取周围上下文
                start = max(addr - 0x20, HEAP_MIN)
                context = pm.read_bytes(start, 0x60)
                # 找 null terminator
                raw = b''
                for i in range(0x60):
                    b = context[i]
                    if b == 0:
                        break
                    raw += bytes([b])

                # 尝试显示为 ASCII
                try:
                    s = raw.decode('ascii', errors='replace')
                    log(f"  0x{addr:08X}: ...{s}...")
                except:
                    log(f"  0x{addr:08X}: (binary)")
            except:
                log(f"  0x{addr:08X}: (read error)")

        if len(hits) > 30:
            log(f"  ... and {len(hits)-30} more")

    outf.close()
    print(f"\nWritten to {outpath}")
    pm.close_process()

if __name__ == "__main__":
    main()

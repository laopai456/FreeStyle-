# scan_actor.py - 深入分析DStaticActor堆对象
import sys, struct
sys.stdout.reconfigure(encoding='utf-8')
import pymem
import psutil

def find_pid():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

VTABLE_STATIC  = 0x0284E00C
VTABLE_DYNAMIC = 0x0284A9EC

def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        sys.exit(1)

    print(f'PID: {pid}')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    # 上次发现的两个DStatic对象
    targets = [0x46527030, 0x46EA1020]

    # 也重新扫一遍确认
    print('重新扫描 DStaticActor (+8=3 过滤)...')
    vt_bytes = struct.pack('<I', VTABLE_STATIC)
    statics = []
    for addr in range(0x10000, 0x7FFF0000, 0x1000):
        try:
            data = pm.read_bytes(addr, 0x1000)
            if not data: continue
            off = 0
            while True:
                idx = data.find(vt_bytes, off)
                if idx == -1: break
                obj_addr = addr + idx
                # 读+8字段确认是3
                raw = pm.read_bytes(obj_addr, 16)
                f = struct.unpack('<4I', raw)
                if f[2] == 3:  # +8 == 3
                    statics.append(obj_addr)
                off = idx + 4
        except:
            continue
    print(f'  确认 {len(statics)} 个 DStaticActor')

    # 对每个对象做深度分析
    for obj_addr in statics:
        print(f'\n{"="*60}')
        print(f'DStaticActor @ 0x{obj_addr:08X}')

        # dump前256字节
        try:
            raw = pm.read_bytes(obj_addr, 0x200)
            # 按4字节字段打印前64字节
            print('  前64字节:')
            for i in range(0, 64, 4):
                val = struct.unpack_from('<I', raw, i)[0]
                fval = struct.unpack_from('<f', raw, i)[0]
                tag = ''
                if i == 0: tag = ' <- vtable'
                elif i == 8: tag = ' <- type (3=static,1=dynamic)'
                print(f'    +0x{i:03X}: 0x{val:08X}  ({fval:>12.2f}){tag}')

            # 搜附近内存找itemcode
            for code in [b'50125461', b'50125331', b'50914671', b'50125711']:
                idx = raw.find(code)
                if idx != -1:
                    print(f'  !! 对象内 +0x{idx:X} 发现 {code.decode()}')

            # 读+4指向的数据（可能是关联对象）
            ptr_plus4 = struct.unpack_from('<I', raw, 4)[0]
            if 0x10000 < ptr_plus4 < 0x7FFF0000:
                try:
                    sub = pm.read_bytes(ptr_plus4, 0x100)
                    print(f'  +4 -> 0x{ptr_plus4:08X}: {sub[:64].hex()}')
                    # 在子对象里搜itemcode
                    for code in [b'50125461', b'50125331']:
                        idx = sub.find(code)
                        if idx != -1:
                            print(f'    !! 子对象 +0x{idx:X} 发现 {code.decode()}')
                except:
                    print(f'  +4 -> 0x{ptr_plus4:08X}: 不可读')

            # 沿指针链多跳几层
            print('  指针链探索:')
            chain_addr = obj_addr
            for step in range(3):
                try:
                    # 读+0x10, +0x14, +0x18等常见指针位置
                    for offset in [0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C]:
                        ptr = struct.unpack_from('<I', raw, offset)[0] if offset < len(raw) else 0
                        if 0x400000 < ptr < 0x7FFF0000:
                            try:
                                sub2 = pm.read_bytes(ptr, 0x40)
                                for code in [b'50125461', b'50125331']:
                                    if code in sub2:
                                        idx = sub2.index(code)
                                        print(f'    +0x{offset:02X} -> 0x{ptr:08X} +0x{idx:X} 发现 {code.decode()}')
                            except:
                                pass
                except:
                    pass
                break  # 只探索一层

        except Exception as e:
            print(f'  读失败: {e}')

    # 额外：从itemcode地址反向搜vtable
    print(f'\n{"="*60}')
    print('从 itemcode 反向搜对象:')
    # 0x29B01B58 有 "50125461"+"767"
    item_addr = 0x29B01B58
    try:
        ctx = pm.read_bytes(item_addr - 0x100, 0x200)
        # 在这个区域搜vtable指针
        for vt_name, vt_val in [('DStatic', VTABLE_STATIC), ('DDynamic', VTABLE_DYNAMIC)]:
            vt_b = struct.pack('<I', vt_val)
            idx = ctx.find(vt_b)
            if idx != -1:
                print(f'  {vt_name} vtable 在 itemcode 前方 0x{0x100-idx:X} 处')
    except:
        pass

    pm.close_process()

if __name__ == '__main__':
    main()

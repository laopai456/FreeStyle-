"""
test_candidate.py — 测试单个候选是否为 AcquireSMD

用法:
  py test_candidate.py <CAND_A|CAND_B|CAND_C|REF_SSKF_1|REF_SSKF_2>

在游戏运行时:
  1. 脚本对候选地址写入 JMP $ (EB FE 死循环)
  2. 等待 60 秒观察:
     - 5 秒内崩 → 主循环函数, 不是 AcquireSMD
     - 60 秒不崩 → 冷函数, 进去商城点发型预览
     - 点预览时卡死 → 这就是 AcquireSMD!
  3. 自动恢复原始字节

例子:
  py test_candidate.py CAND_B
  py test_candidate.py REF_SSKF_1
"""

import sys, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000

CANDIDATES = {
    'CAND_A': 0x02366580,
    'CAND_B': 0x02367270,
    'CAND_C': 0x024C3DC0,
    'REF_SSKF_1': 0x022EC941,
    'REF_SSKF_2': 0x022ED7D5,
}

JMP_SELF = b'\xEB\xFE'

kernel32 = ctypes.windll.kernel32

def vp_rwx(handle, addr):
    old = ctypes.c_uint32()
    return kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), 0x1000, 0x40, ctypes.byref(old))

def vp_rx(handle, addr):
    old = ctypes.c_uint32()
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), 0x1000, 0x20, ctypes.byref(old))

def alive(pid):
    h = kernel32.OpenProcess(0x0400, False, pid)
    if not h:
        print("    [检查] OpenProcess 失败 → 进程可能已死")
        return False
    ec = ctypes.c_uint32()
    kernel32.GetExitCodeProcess(h, ctypes.byref(ec))
    kernel32.CloseHandle(h)
    return ec.value == 0x103

def main():
    if len(sys.argv) < 2 or sys.argv[1].upper() not in CANDIDATES:
        print(f"用法: py test_candidate.py <{'|'.join(CANDIDATES.keys())}>")
        return

    name = sys.argv[1].upper()
    addr = CANDIDATES[name]
    rva = addr - BASE

    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    pid = pm.process_id
    handle = pm.process_handle
    page_start = addr & ~0xFFF

    print(f"[+] 测试 {name} @ 0x{addr:08X} (RVA 0x{rva:06X})")
    print(f"[+] PID={pid}")
    print()

    # 1. 读原始字节
    try:
        orig = pm.read_bytes(addr, 2)
        print(f"[*] 原始 2 字节: {orig.hex()}")
    except Exception as e:
        print(f"[!] 读取失败: {e}")
        pm.close_process()
        return

    if orig == JMP_SELF:
        print("[!] 地址已有 JMP $, 可能上次未恢复")
        pm.close_process()
        return

    # 2. 写入 JMP $
    ok = vp_rwx(handle, page_start)
    if not ok:
        print("[!] VirtualProtectEx 失败")
        pm.close_process()
        return

    try:
        pm.write_bytes(addr, JMP_SELF, 2)
        print(f"[+] 已写入 JMP $")
    except Exception as e:
        print(f"[!] 写入失败: {e}")
        vp_rx(handle, page_start)
        pm.close_process()
        return

    vp_rx(handle, page_start)

    # 3. 观察 60 秒
    print()
    print(f"[*] 观察中... 如果在 60 秒内游戏卡死 → {name} 是主循环函数")
    print(f"[*] 60 秒不卡死 → 进商城点发型预览, 卡死则 {name} = AcquireSMD")
    print()

    crash_time = None
    for i in range(60):
        time.sleep(1)
        if not alive(pid):
            crash_time = i + 1
            break

    # 4. 恢复 (即使进程已死也尝试)
    ok = vp_rwx(handle, page_start)
    if ok:
        try:
            pm.write_bytes(addr, orig, 2)
            vp_rx(handle, page_start)
            print(f"[*] 原始字节已恢复")
        except:
            pass

    pm.close_process()

    # 5. 结论
    print()
    if crash_time:
        print(f"=== 游戏在 t={crash_time}s 时卡死 ===")
        if crash_time <= 5:
            print(f"→ {name} 是主循环/高频函数, 不是 AcquireSMD")
        else:
            print(f"→ {name} 是周期调用函数 (~{crash_time}s), 不是 AcquireSMD")
    else:
        print(f"=== 60 秒内无卡死 ===")
        print(f"→ {name} 是冷函数")
        print(f"→ 现在进商城点发型预览 → 如果卡死 = {name} 就是 AcquireSMD!")

if __name__ == "__main__":
    main()
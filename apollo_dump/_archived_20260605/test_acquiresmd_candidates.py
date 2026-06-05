"""
test_acquiresmd_candidates.py — 对候选函数写 JMP，逐个验证哪个是 AcquireSMD

原理:
  对每个候选函数入口写 JMP $ (EB FE = 死循环)
  进商城点发型预览 → 如果该函数是 AcquireSMD，游戏会卡死
  从卡死就知道哪个候选对了
"""

import sys, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000

# 候选函数入口 (从 find_acquiresmd_v2.py 结果)
CANDIDATES = {
    'CAND_A': 0x02366580,  # RVA 0x1F66580
    'CAND_B': 0x02367270,  # RVA 0x1F67270
    'CAND_C': 0x024C3DC0,  # RVA 0x20C3DC0
}

# 在两个 SSKF 引用点也写上 (虽然没找到序言, 但可以写 NOP 试试)
# 这些引用点本身可能在函数体内, 直接写 JMP 到安全位置
INTERNAL_POINTS = {
    'REF_SSKF_1': 0x022EC941,  # 在已知 SSKF 比较函数内
    'REF_SSKF_2': 0x022ED7D5,
}

JMP_SELF = b'\xEB\xFE'  # JMP $ (infinite loop, 2 bytes)

kernel32 = ctypes.windll.kernel32

def vp_rwx(handle, addr, size):
    old = ctypes.c_uint32()
    ok = kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, 0x40, ctypes.byref(old))
    return ok

def vp_rx(handle, addr, size):
    old = ctypes.c_uint32()
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, 0x20, ctypes.byref(old))

def process_alive(pid):
    handle = kernel32.OpenProcess(0x0400, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_uint32()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return exit_code.value == 0x103

def patch_and_watch(pm, handle, pid, name, addr, watch_seconds=15):
    """写 JMP 到函数入口, 观察游戏是否卡死"""
    page_start = addr & ~0xFFF

    # 读原始字节
    try:
        orig = pm.read_bytes(addr, 2)
    except:
        return f"读取失败"

    if orig == JMP_SELF:
        return f"已有 JMP"

    # 写 JMP
    ok = vp_rwx(handle, page_start, 0x1000)
    if not ok:
        return f"VirtualProtect 失败"

    try:
        pm.write_bytes(addr, JMP_SELF, 2)
    except:
        vp_rx(handle, page_start, 0x1000)
        return f"写入失败"

    vp_rx(handle, page_start, 0x1000)

    # 等待观察 — 游戏卡死 = 命中了
    for i in range(watch_seconds):
        time.sleep(1)
        alive = process_alive(pid)
        if not alive:
            return f"进程崩溃 (t={i+1}s)"

    # 恢复
    ok = vp_rwx(handle, page_start, 0x1000)
    if ok:
        pm.write_bytes(addr, orig, 2)
        vp_rx(handle, page_start, 0x1000)

    return f"无命中 (观察{watch_seconds}s)"

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    handle = pm.process_handle
    pid = pm.process_id
    print(f"[+] PID = {pid}")
    print()
    print("方案 A: 逐个对候选函数写 JMP $ (EB FE = 死循环)")
    print("如果在商城点发型预览时游戏卡死 → 该候选就是 AcquireSMD")
    print()

    for name, addr in CANDIDATES.items():
        rva = addr - BASE
        result = patch_and_watch(pm, handle, pid, name, addr, 15)
        print(f"  {name} @ 0x{addr:08X} (RVA 0x{rva:06X}): {result}")

        # 如果进程崩溃了, 不用继续测了
        if not process_alive(pid):
            print(f"\n[!] 进程已崩, {name} 导致了崩溃")
            break

    print()

    if process_alive(pid):
        print("方案 B: 内部引用点写 NOP (原地不跳), 直到游戏加载模型时崩溃")
        print("进入加载场景后脚本会自动检测...")
        for name, addr in INTERNAL_POINTS.items():
            rva = addr - BASE
            result = patch_and_watch(pm, handle, pid, name, addr, 10)
            print(f"  {name} @ 0x{addr:08X} (RVA 0x{rva:06X}): {result}")
            if not process_alive(pid):
                break

    # 不在循环内就恢复 (上面的循环已经恢复了)
    pm.close_process()
    print("[*] 完成")

if __name__ == "__main__":
    main()
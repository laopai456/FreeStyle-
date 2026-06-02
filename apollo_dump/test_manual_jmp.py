"""
test_manual_jmp.py — v2: VirtualProtectEx + 写 JMP 到已确认的代码地址
"""

import sys, struct, time, ctypes

sys.path.insert(0, r"d:\py\反编译\FreeStyle\lib\Pymem")
import pymem

BASE = 0x400000
# 选两个没有重叠的明确代码地址
# 用 SSKF 地址 +0x20 (在 SSKF 字符串附近，但不覆盖可能的数据)
WRITE_TARGET = 0x284B9C4 + 0x20
# 用完全不同的地址做跳转目标，确保 JMP 字节不同
DUMMY_JMP_TARGET = 0x40001000

PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_READ = 0x20

kernel32 = ctypes.windll.kernel32

def make_jmp_rel32(from_addr, to_addr):
    rel = (to_addr - (from_addr + 5)) & 0xFFFFFFFF
    return struct.pack("<Bi", 0xE9, rel)

def vp_rwx(handle, addr, size):
    old = ctypes.c_uint32()
    ok = kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, PAGE_EXECUTE_READWRITE, ctypes.byref(old))
    return ok, old.value

def vp_rx(handle, addr, size):
    old = ctypes.c_uint32()
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, PAGE_EXECUTE_READ, ctypes.byref(old))

def process_alive(pid):
    """检查进程是否存活"""
    handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
    if not handle:
        return False
    exit_code = ctypes.c_uint32()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return exit_code.value == 0x103  # STILL_ACTIVE

def main():
    try:
        pm = pymem.Pymem("FreeStyle.exe")
    except:
        print("[!] FreeStyle.exe 未运行")
        return

    handle = pm.process_handle
    pid = pm.process_id
    if not handle:
        print("[!] 无效进程句柄")
        return

    print(f"[+] PID = {pid} | 句柄 = {handle}")
    print(f"[+] 写入目标 = 0x{WRITE_TARGET:08X} | 跳转目标 = 0x{DUMMY_JMP_TARGET:08X}")

    PAGE_SIZE = 0x1000
    page_start = WRITE_TARGET & ~0xFFF

    # 1. 读原始字节
    try:
        orig = pm.read_bytes(WRITE_TARGET, 5)
        print(f"[*] 原始 5 字节: {orig.hex()}")
    except Exception as e:
        print(f"[!] 读取失败: {e}")
        pm.close_process()
        return

    # 2. 构造 JMP
    jmp_bytes = make_jmp_rel32(WRITE_TARGET, DUMMY_JMP_TARGET)
    print(f"[*] JMP 字节: {jmp_bytes.hex()}")

    # 如果 JMP 和原始一样那就改目标直到不一样
    if jmp_bytes == orig:
        DUMMY_JMP_TARGET_ALT = 0x40002000
        jmp_bytes = make_jmp_rel32(WRITE_TARGET, DUMMY_JMP_TARGET_ALT)
        print(f"[*] 和原字节重合，改用 0x40002000: {jmp_bytes.hex()}")

    # 3. VirtualProtectEx → RWX
    ok, old_prot = vp_rwx(handle, page_start, PAGE_SIZE)
    print(f"[*] VirtualProtectEx({page_start:#x}, rwx): {'成功' if ok else '失败'} (原属性: {old_prot:#x})")
    if not ok:
        print("[!] 无法改页属性，退出")
        pm.close_process()
        return

    # 4. 写入 JMP
    try:
        pm.write_bytes(WRITE_TARGET, jmp_bytes, 5)
        print(f"[+] JMP 写入成功!")
    except Exception as e:
        print(f"[!] 写入失败: {e}")
        vp_rx(handle, page_start, PAGE_SIZE)
        pm.close_process()
        return

    # 5. 恢复页属性为 RX
    vp_rx(handle, page_start, PAGE_SIZE)
    print(f"[*] 页属性已恢复为 RX")

    # 6. 观察进程 5 秒
    print("[*] 等待 5 秒观察游戏是否崩溃...")
    crashed = False
    for i in range(5):
        time.sleep(1)
        alive = process_alive(pid)
        status = '存活' if alive else '已崩溃!'
        print(f"    [t={i+1}s] {status}")
        if not alive:
            crashed = True
            break

    if not crashed:
        print(f"\n=== 存活 ✅ ===")
        print(f"    → 手动修改 .text 不触发检测")
        print(f"    → Frida Interceptor.attach 崩溃另有原因")
    else:
        print(f"\n=== 崩溃 ❌ ===")
        print(f"    → 写入 .text 本身被检测到")

    # 7. 恢复原始字节
    try:
        ok2, _ = vp_rwx(handle, page_start, PAGE_SIZE)
        if ok2:
            pm.write_bytes(WRITE_TARGET, orig, 5)
            vp_rx(handle, page_start, PAGE_SIZE)
            print(f"[*] 原始字节已恢复")
    except:
        print(f"[!] 恢复失败")

    pm.close_process()
    print("[*] 完成")

if __name__ == "__main__":
    main()
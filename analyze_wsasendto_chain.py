"""
analyze_wsasendto_chain.py — 用 capstone 反汇编 .text 段，定位 WSASendTo→加密函数调用链

策略:
  1. 用 pefile 解析 PE，定位 .text 段
  2. 用 capstone 反汇编整个 .text 段
  3. 找到所有 CALL [CryptEncrypt_IAT] 和 CALL [WSASendTo_IAT] 指令
  4. 对于每个 CALL，反汇编所在函数(向前到 func start, 向后到 ret)
  5. 分析哪些函数同时引用 crypto 和 WSASendTo
  6. 输出调用链和加密函数候选

锚点:
  IAT RVA (取决于 ImageBase=0x400000):
    WSASendTo:       0x0268F944  (absolute=0x0268F944, call [0x268F944])
    WSARecvFrom:     0x0268F948
    CryptEncrypt:    0x0268F04C
    CryptImportKey:  0x0268F008
    recvfrom:        0x0268F964
    WSASend:         0x0268F9EC
    WSARecv:         0x0268F9C4

  x86 call dword ptr [addr] = FF 15 <4 bytes addr>
  x86 jmp  dword ptr [addr] = FF 25 <4 bytes addr>
  x86 ret                    = C3 / C2 XX
  x86 call rel32              = E8 <4 bytes rel>
"""
import pefile
import struct
import os
import sys
from collections import defaultdict

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    print("[!] capstone not installed. Run: py -m pip install capstone")
    sys.exit(1)

PE_PATH = r"d:\py\反编译\FreeStyle\apollo_dump\FreeStyle.exe"
OUTPUT_PATH = r"d:\py\反编译\FreeStyle\apollo_dump\udp_crypto_chain_v2.txt"
IMAGE_BASE = 0x400000

# 目标 IAT RVAs
IAT_TARGETS = {
    0x0268F944: "WSASendTo",
    0x0268F948: "WSARecvFrom",
    0x0268F964: "recvfrom",
    0x0268F9C0: "sendto",
    0x0268F9C4: "WSARecv",
    0x0268F9EC: "WSASend",
    0x0268F04C: "CryptEncrypt",
    0x0268F008: "CryptImportKey",
    0x0268F014: "CryptHashData",
    0x0268F018: "CryptCreateHash",
    0x0268F02C: "CryptGenRandom",
    0x0268F030: "CryptAcquireContextA",
    0x0268F04C: "CryptEncrypt",
}

# AES S-box RVAs （这些在 .rdata 段，但在代码中寻找 mov eax, offset xxx 之类的引用）
AES_SBOX_RVAS = {0x2442ef8, 0x2617f18, 0x2442ff8, 0x2618018, 0x261a118}

# 包构造区
MAGIC_907F_RVA = 0x220141

def main():
    print("=" * 80)
    print("  analyze_wsasendto_chain — capstone 静态分析")
    print("=" * 80)

    if not os.path.exists(PE_PATH):
        print(f"[!] File not found: {PE_PATH}")
        return

    pe = pefile.PE(PE_PATH)
    
    # 加载原始文件
    with open(PE_PATH, "rb") as f:
        raw_data = f.read()

    # 找到 .text 段
    text_sec = None
    for sec in pe.sections:
        name = sec.Name.decode("utf-8", errors="replace").rstrip("\x00")
        if name == ".text":
            text_sec = sec
            break
    
    if not text_sec:
        print("[!] .text section not found")
        pe.close()
        return

    text_rva = text_sec.VirtualAddress
    text_size = min(text_sec.Misc_VirtualSize, text_sec.SizeOfRawData)
    text_raw = text_sec.PointerToRawData
    text_data = raw_data[text_raw:text_raw + text_size]

    print(f".text section: RVA=0x{text_rva:08X}, size=0x{text_size:08X} ({text_size/1024:.0f} KB)")
    print(f" Raw offset: 0x{text_raw:08X}")

    # ---- Step 1: 反汇编 .text 段，定位所有 CALL [IAT] ----
    print(f"\n[Step 1] Disassembling .text section ({text_size/1024:.0f} KB)...")
    
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    
    # {(rva_of_call_insn, iat_target_name): [...]}
    iat_calls = defaultdict(list)
    # {rva: [(target_rva, target_name)]}
    call_insns = defaultdict(list)
    
    insn_count = 0
    for insn in md.disasm(text_data, text_rva):
        insn_count += 1
        if insn_count % 500000 == 0:
            print(f"  ... {insn_count} instructions ({insn.address - text_rva}/{text_size} bytes)")
        
        # Check for CALL [imm] = FF 15 XX XX XX XX
        if insn.mnemonic == "call" and len(insn.operands) > 0:
            op = insn.operands[0]
            if op.type == 2:  # memory operand
                # capstone: op.mem.disp gives the displacement
                disp = op.mem.disp
                if disp in IAT_TARGETS:
                    name = IAT_TARGETS[disp]
                    iat_calls[name].append(insn.address)
                    call_insns[insn.address].append((disp, name))

    print(f"  Total instructions: {insn_count}")
    
    # ---- Step 2: 按 IAT 函数统计 ----
    print(f"\n[Step 2] IAT CALL 指令统计:\n")
    total_calls = 0
    for name, addrs in sorted(iat_calls.items()):
        print(f"  {name:25s}: {len(addrs):4d} calls")
        total_calls += len(addrs)
    print(f"\n  Total CALL [IAT]: {total_calls}")

    # ---- Step 3: 对每个 CALL 地址，界定所在函数，查找内部引用 ----
    print(f"\n[Step 3] 函数界定 & 内部引用分析...")
    
    # 先用 ret 指令建立函数边界
    ret_addrs = set()
    for insn in md.disasm(text_data, text_rva):
        if insn.mnemonic == "ret" or (insn.mnemonic == "ret" and len(insn.bytes) == 1):
            ret_addrs.add(insn.address)
        elif insn.mnemonic == "int3" and insn.address > 0:
            # int3 (0xCC) 也是函数边界
            ret_addrs.add(insn.address - 1)  # treat function as ending before int3
    
    def find_function_range(addr):
        """给定一个地址，向前找 func start，向后找 ret"""
        # 向前搜索 func prologue: push ebp; mov ebp, esp 或直接 jump target
        # 简化：向前最多搜索 2048 字节
        func_start = addr
        search_back = min(2048, addr - text_rva)
        search_bytes = text_data[addr - text_rva - search_back:addr - text_rva + 1]
        
        # 最简单的方法：往回找最近的 ret/int3
        best_start = text_rva
        for insn in md.disasm(search_bytes, addr - search_back):
            if insn.address > addr:
                break
            if insn.mnemonic == "ret":
                best_start = insn.address + insn.size
            elif insn.mnemonic in ("int3", "nop"):
                if insn.address > best_start:
                    best_start = insn.address + 1
        
        # 向前找 ret
        func_end = addr
        search_forward = min(8192, text_rva + text_size - addr)
        fwd_bytes = text_data[addr - text_rva:addr - text_rva + search_forward]
        for insn in md.disasm(fwd_bytes, addr):
            if insn.mnemonic == "ret":
                func_end = insn.address
                break
            if insn.address > addr and insn.mnemonic in ("int3",):
                func_end = insn.address
                break
        
        return best_start, func_end
    
    # ---- 核心分析：WSASendTo 调用者 ----
    print(f"\n" + "=" * 80)
    print("  WSASendTo CALL 调用者分析")
    print("=" * 80)
    
    wsasendto_addrs = iat_calls.get("WSASendTo", [])
    crypto_addrs = iat_calls.get("CryptEncrypt", [])
    
    print(f"\nWSASendTo 调用: {len(wsasendto_addrs)} 次")
    print(f"CryptEncrypt 调用: {len(crypto_addrs)} 次")
    
    # 对每个 WSASendTo 调用，获取所在函数区间
    wsasendto_funcs = {}
    for addr in wsasendto_addrs:
        start, end = find_function_range(addr)
        wsasendto_funcs[addr] = (start, end)
    
    # 对每个 CryptEncrypt 调用，获取所在函数区间
    crypto_funcs = {}
    for addr in crypto_addrs:
        start, end = find_function_range(addr)
        crypto_funcs[addr] = (start, end)
    
    # 检查哪些 WSASendTo 函数也包含 crypto 调用
    print(f"\n--- WSASendTo 调用者 详细 ---")
    
    enc_candidates = []  # 加密函数候选
    
    for ws_addr, (ws_start, ws_end) in sorted(wsasendto_funcs.items()):
        ws_start_rva = ws_start  # 这已在 RVA 空间
        ws_end_rva = ws_end
        
        # 检查此函数区间内是否有 crypto IAT 调用
        containing_crypto = []
        for cr_addr, (cr_start, cr_end) in crypto_funcs.items():
            if ws_start_rva <= cr_addr <= ws_end_rva:
                containing_crypto.append(cr_addr)
        
        # 检查此函数区间内 AES S-box 引用
        sbox_hits = find_sbox_refs_insn(md, text_data, text_rva, ws_start_rva, ws_end_rva)
        
        # 检查包构造 magic (907f) 
        magic_hits = find_magic_907f_refs(md, text_data, text_rva, ws_start_rva, ws_end_rva)
        
        # 检查是否有 CryptImportKey
        key_import_addrs = iat_calls.get("CryptImportKey", [])
        key_hits = []
        for ki_addr in key_import_addrs:
            if ws_start_rva <= ki_addr <= ws_end_rva:
                key_hits.append(ki_addr)
        
        # 检查调用栈上层的函数
        # (谁调用了这个WSASendTo函数?)
        
        marker = ""
        if containing_crypto:
            marker = " ★ CRYPT 加密函数候选!"
        elif sbox_hits:
            marker = " ★ AES S-box 引用 (内置AES)"
        elif key_hits:
            marker = " ★ CryptImportKey (密钥导入)"
        elif magic_hits:
            marker = " ← 907f 包构造"
        
        print(f"\n  WSASendTo CALL @ 0x{ws_addr:08X}")
        print(f"    函数区间: 0x{ws_start_rva:08X} - 0x{ws_end_rva:08X} ({ws_end_rva - ws_start_rva} bytes){marker}")
        
        if containing_crypto:
            print(f"    CryptEncrypt 调用: {[f'0x{x:08X}' for x in containing_crypto]}")
            enc_candidates.append((ws_start_rva, "WSASendTo+CryptEncrypt", ws_addr))
        
        if sbox_hits:
            print(f"    AES S-box refs: {len(sbox_hits)} 处")
            for s in sbox_hits[:5]:
                print(f"      0x{s:08X}")
            if not containing_crypto:
                enc_candidates.append((ws_start_rva, "WSASendTo+S-box", ws_addr))
        
        if key_hits:
            print(f"    CryptImportKey 调用: {[f'0x{x:08X}' for x in key_hits]}")
        
        if magic_hits:
            print(f"    907f magic refs: {len(magic_hits)} 处")
            for m in magic_hits[:5]:
                print(f"      0x{m:08X}")
    
    # ---- 独立 CryptEncrypt 调用者（不在 WSASendTo 函数内） ----
    print(f"\n--- 独立 CryptEncrypt 调用者（不在 WSASendTo 函数内） ---")
    ws_ranges = [(s, e) for s, e in wsasendto_funcs.values()]
    
    for cr_addr, (cr_start, cr_end) in crypto_funcs.items():
        in_ws = False
        for ws_s, ws_e in ws_ranges:
            if ws_s <= cr_addr <= ws_e:
                in_ws = True
                break
        if not in_ws:
            # 检查谁调用了这个函数
            callers = find_direct_callers(md, text_data, text_rva, cr_start)
            
            sbox_hits = find_sbox_refs_insn(md, text_data, text_rva, cr_start, cr_end)
            key_hits = []
            for ki_addr in iat_calls.get("CryptImportKey", []):
                if cr_start <= ki_addr <= cr_end:
                    key_hits.append(ki_addr)
            
            marker = ""
            if sbox_hits: marker = " +S-box"
            if key_hits: marker += " +KeyImport"
            
            print(f"\n  CryptEncrypt CALL @ 0x{cr_addr:08X}")
            print(f"    函数区间: 0x{cr_start:08X} - 0x{cr_end:08X} ({cr_end - cr_start} bytes){marker}")
            print(f"    调用者: {[f'0x{x:08X}' for x in callers[:5]]}")
            if sbox_hits:
                print(f"    AES S-box refs: {len(sbox_hits)} 处")
            if key_hits:
                print(f"    CryptImportKey: {len(key_hits)} 处")
            
            enc_candidates.append((cr_start, "独立 CryptEncrypt" + marker, cr_addr))
    
    # ---- Step 4: 全量 907f 包构造代码搜索 ----
    print(f"\n--- 907f magic 包构造区域 ---")
    # 搜索 push 0x907f 或 mov ..., 0x907f 的指令
    magic_refs = find_all_magic_907f(md, text_data, text_rva)
    print(f"  找到 {len(magic_refs)} 处 907f 引用")
    
    # 按函数分组
    magic_funcs = defaultdict(list)
    for ref_addr in magic_refs:
        start, end = find_function_range(ref_addr)
        magic_funcs[start].append(ref_addr)
    
    print(f"  分布在 {len(magic_funcs)} 个函数中")
    for func_start, refs in sorted(magic_funcs.items()):
        func_end = find_function_range(func_start)[1]
        # 检查是否包含 crypto
        has_crypto = False
        for cr_addr in crypto_addrs:
            if func_start <= cr_addr <= func_end:
                has_crypto = True
                break
        marker = " ★ 包构造+加密!" if has_crypto else ""
        
        # 只显示包含 crypto 或在 0x220141 附近的函数
        if has_crypto or abs(func_start - 0x220141) < 0x10000:
            print(f"\n  函数 0x{func_start:08X} - 0x{func_end:08X} ({len(refs)} refs){marker}")
            # 打印前几句指令帮助理解
            print(f"  (907f ref 数: {len(refs)})")
            dump_first_insns(md, text_data, text_rva, func_start, 8)
    
    # ---- 输出结果 ----
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("  UDP 加密 Key 破解 — capstone 静态分析结果")
    output_lines.append("=" * 80)
    output_lines.append("")
    output_lines.append(f"WSASendTo 调用数: {len(wsasendto_addrs)}")
    output_lines.append(f"CryptEncrypt 调用数: {len(crypto_addrs)}")
    output_lines.append(f"907f magic 引用: {len(magic_refs)} 处，{len(magic_funcs)} 个函数")
    output_lines.append("")
    
    if enc_candidates:
        output_lines.append("=" * 60)
        output_lines.append("  ★ 加密函数候选")
        output_lines.append("=" * 60)
        for func_start, desc, call_addr in enc_candidates:
            output_lines.append(f"  entry=0x{func_start:08X}  [{desc}]  (CALL @ 0x{call_addr:08X})")
    else:
        output_lines.append("  ⚠ 未找到同时包含 WSASendTo/CryptEncrypt/AES S-box 的函数")
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\n[+] Results written to {OUTPUT_PATH}")
    
    pe.close()


def find_sbox_refs_insn(md, text_data, text_rva, start_rva, end_rva):
    """在指定RVA范围内查找 AES S-box 的地址引用"""
    hits = []
    offset = start_rva - text_rva
    end_offset = end_rva - text_rva
    chunk = text_data[offset:end_offset]
    
    for insn in md.disasm(chunk, start_rva):
        if insn.address > end_rva:
            break
        # 查找指令中引用的绝对地址是否是 S-box
        for op in insn.operands:
            if op.type == 2:  # memory
                if op.mem.disp in AES_SBOX_RVAS:
                    hits.append(insn.address)
            elif op.type == 1:  # immediate
                if op.imm in AES_SBOX_RVAS:
                    hits.append(insn.address)
    
    return hits


def find_magic_907f_refs(md, text_data, text_rva, start_rva, end_rva):
    """在指定范围内找 907f 引用"""
    hits = []
    offset = start_rva - text_rva
    end_offset = min(end_rva - text_rva, len(text_data))
    chunk = text_data[offset:end_offset]
    
    for insn in md.disasm(chunk, start_rva):
        if insn.address > end_rva:
            break
        for op in insn.operands:
            if op.type == 1 and (op.imm == 0x907f or op.imm == 0x7f90):
                hits.append(insn.address)
    
    return hits


def find_all_magic_907f(md, text_data, text_rva):
    """全量搜索 907f immediate 引用"""
    hits = []
    for insn in md.disasm(text_data, text_rva):
        for op in insn.operands:
            if op.type == 1 and (op.imm == 0x907f or op.imm == 0x7f90):
                hits.append(insn.address)
                break
    return hits


def find_direct_callers(md, text_data, text_rva, func_entry_rva):
    """找到调用 func_entry_rva 的地址们"""
    callers = []
    for insn in md.disasm(text_data, text_rva):
        if insn.mnemonic == "call":
            for op in insn.operands:
                if op.type == 1 and op.imm == func_entry_rva:
                    callers.append(insn.address)
    return callers


def dump_first_insns(md, text_data, text_rva, start_rva, count):
    """打印函数开头几句指令"""
    offset = start_rva - text_rva
    chunk = text_data[offset:offset + min(256, len(text_data) - offset)]
    n = 0
    for insn in md.disasm(chunk, start_rva):
        if n >= count:
            break
        print(f"    0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        n += 1


if __name__ == "__main__":
    main()
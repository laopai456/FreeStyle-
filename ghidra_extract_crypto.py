"""
ghidra_extract_crypto.py — Ghidra headless post-analysis 脚本
提取 FreeStyle.exe 中加密相关的反编译代码

分析锚点:
  1. WSASendTo 调用者 → 找谁调用了 UDP 发送
  2. CryptEncrypt 调用者 → 找谁调用了加密 API
  3. AES S-box (0x2442ef8) 引用者 → 找内置 AES 函数
  4. 907f magic (0x220141) 引用者 → 找包构造函数

用法: analyzeHeadless <proj> FreeStyle -process FreeStyle.exe -postScript ghidra_extract_crypto.py
"""

import os

# Ghidra headless 提供的全局变量
# currentProgram, currentAddress, etc.

OUT_DIR = r"D:\py\反编译\FreeStyle\ghidra_output"
os.makedirs(OUT_DIR, exist_ok=True)

out = []

def log(msg):
    out.append(msg)
    print(msg)

def get_func_info(func):
    """获取函数的地址、大小、名称"""
    if func is None:
        return None
    return {
        'name': func.getName(),
        'addr': func.getEntryPoint().toString(),
        'size': func.getBody().getNumAddresses()
    }

# ================================================================
# 1. 获取导入表中的目标函数地址
# ================================================================
def find_external_symbol(name):
    """在导入表中查找外部符号"""
    syms = currentProgram.getSymbolTable().getExternalSymbols()
    for sym in syms:
        if sym.getName() == name:
            return sym
    return None

# ================================================================
# 2. 查找对某个地址的所有代码引用
# ================================================================
def find_xrefs_to(addr, limit=20):
    """返回引用该地址的指令地址列表"""
    refs = []
    ref_mgr = currentProgram.getReferenceManager()
    it = ref_mgr.getReferencesTo(addr)
    for ref in it:
        from_addr = ref.getFromAddress()
        if ref.getReferenceType().isCall():
            kind = "CALL"
        elif ref.getReferenceType().isData():
            kind = "DATA"
        elif ref.getReferenceType().isRead():
            kind = "READ"
        else:
            kind = "OTHER"
        func = getFunctionContaining(from_addr)
        func_name = func.getName() if func else "?"
        refs.append({
            'from': from_addr.toString(),
            'kind': kind,
            'func': func_name,
            'func_addr': func.getEntryPoint().toString() if func else "?"
        })
        if len(refs) >= limit:
            break
    return refs

# ================================================================
# 3. 反编译函数并输出
# ================================================================
def decompile_function(func):
    """反编译单个函数，返回 C 代码"""
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor

    monitor = ConsoleTaskMonitor()
    decomp = DecompInterface()
    decomp.openProgram(currentProgram)
    result = decomp.decompileFunction(func, 30, monitor)

    if result.decompileCompleted():
        return result.getDecompiledFunction().getC()
    else:
        return "// DECOMPILE ERROR: " + result.getErrorMessage()

# ================================================================
# Main
# ================================================================
log("=" * 60)
log("FreeStyle.exe Crypto Analysis — Ghidra Headless")
log("=" * 60)

# --- 目标1: WSASendTo 调用者 ---
log("\n>>> WSASendTo XREFs (UDP send)")
wsasym = find_external_symbol("WSASendTo")
if wsasym:
    wsaddr = wsasym.getAddress()
    log(f"  External symbol: {wsasym.getName()} @ {wsaddr}")
    xrefs = find_xrefs_to(wsaddr)
    log(f"  Found {len(xrefs)} xrefs:")
    for r in xrefs:
        log(f"    {r['from']} ({r['kind']}) → {r['func']} @ {r['func_addr']}")
else:
    log("  WSASendTo NOT FOUND in import table")

# --- 目标2: CryptEncrypt 调用者 ---
log("\n>>> CryptEncrypt XREFs")
cr_sym = find_external_symbol("CryptEncrypt")
if cr_sym:
    cr_addr = cr_sym.getAddress()
    log(f"  External symbol: {cr_sym.getName()} @ {cr_addr}")
    xrefs = find_xrefs_to(cr_addr)
    log(f"  Found {len(xrefs)} xrefs:")
    for r in xrefs:
        log(f"    {r['from']} ({r['kind']}) → {r['func']} @ {r['func_addr']}")
else:
    log("  CryptEncrypt NOT FOUND")

# --- 目标3: AES S-box 引用 ---
log("\n>>> AES S-box (0x2442ef8) XREFs")
base = currentProgram.getImageBase()
sbox_addr = base.add(0x2442ef8)
log(f"  Looking for xrefs to: {sbox_addr}")

# 扫描所有引用
ref_mgr = currentProgram.getReferenceManager()
it = ref_mgr.getReferencesTo(sbox_addr)
count = 0
for ref in it:
    from_addr = ref.getFromAddress()
    func = getFunctionContaining(from_addr)
    func_name = func.getName() if func else "?"
    kind = "DATA" if ref.getReferenceType().isData() else "READ" if ref.getReferenceType().isRead() else "CALL" if ref.getReferenceType().isCall() else "OTHER"
    log(f"    {from_addr} ({kind}) → {func_name} @ {func.getEntryPoint() if func else '?'}")
    count += 1
    if count >= 30:
        break
if count == 0:
    log("  No xrefs found (S-box may be accessed via calculated offset)")

# --- 反编译包含 WSASendTo 调用的函数 ---
log("\n>>> Decompiling WSASendTo caller functions")
wsasym2 = find_external_symbol("WSASendTo")
if wsasym2:
    ref_mgr2 = currentProgram.getReferenceManager()
    it2 = ref_mgr2.getReferencesTo(wsasym2.getAddress())
    done = set()
    for ref in it2:
        func = getFunctionContaining(ref.getFromAddress())
        if func and func.getEntryPoint().toString() not in done:
            done.add(func.getEntryPoint().toString())
            log(f"\n--- {func.getName()} @ {func.getEntryPoint()} ---")
            code = decompile_function(func)
            # 只输出前 200 行
            lines = code.split('\n')
            for line in lines[:200]:
                log(line)
            if len(lines) > 200:
                log(f"  ... ({len(lines) - 200} more lines)")

# --- 反编译包含 CryptEncrypt 调用的函数 ---
log("\n>>> Decompiling CryptEncrypt caller functions")
cr_sym2 = find_external_symbol("CryptEncrypt")
if cr_sym2:
    ref_mgr3 = currentProgram.getReferenceManager()
    it3 = ref_mgr3.getReferencesTo(cr_sym2.getAddress())
    done = set()
    for ref in it3:
        func = getFunctionContaining(ref.getFromAddress())
        if func and func.getEntryPoint().toString() not in done:
            done.add(func.getEntryPoint().toString())
            log(f"\n--- {func.getName()} @ {func.getEntryPoint()} ---")
            code = decompile_function(func)
            lines = code.split('\n')
            for line in lines[:200]:
                log(line)
            if len(lines) > 200:
                log(f"  ... ({len(lines) - 200} more lines)")

# Write output
with open(os.path.join(OUT_DIR, "crypto_analysis.txt"), "w", encoding="utf-8") as f:
    f.write('\n'.join(out))

log(f"\nOutput written to {OUT_DIR}/crypto_analysis.txt")
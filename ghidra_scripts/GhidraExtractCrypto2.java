/* GhidraExtractCrypto2.java — 改进版
 *
 * 策略修正:
 *   1. 对外部符号 → 找 thunk 函数 → 找 thunk 的调用者
 *   2. 扫描 .text 段中 "CALL [thunk_addr]" 指令
 *   3. 反编译所有找到的调用者函数
 *   4. 加 AES S-box 附近代码反编译 (0x220141 包构造)
 */

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.pcode.*;
import ghidra.program.model.lang.*;
import ghidra.util.task.ConsoleTaskMonitor;

import java.io.*;
import java.util.*;

public class GhidraExtractCrypto2 extends GhidraScript {

    private StringBuilder out = new StringBuilder();
    private String outDir = "D:\\py\\反编译\\FreeStyle\\ghidra_output";

    private void log(String msg) {
        out.append(msg).append('\n');
        println(msg);
    }

    /** 找外部符号的 thunk 函数（对应用层代码可见的包装器） */
    private Function findThunkFor(String symName) {
        SymbolTable st = currentProgram.getSymbolTable();

        // 方法1: 找名称为 symName 的 thunk 函数
        for (Symbol s : st.getSymbols(symName)) {
            if (s.isPrimary()) {
                Address addr = s.getAddress();
                if (!addr.isExternalAddress()) {
                    Function func = getFunctionAt(addr);
                    if (func != null) return func;
                }
            }
        }

        // 方法2: 找外部符号, 然后搜索指向它的 jmp 指令
        Symbol extSym = null;
        for (Symbol s : st.getExternalSymbols()) {
            if (s.getName().equals(symName)) {
                extSym = s;
                break;
            }
        }
        if (extSym == null) return null;

        // 在内存中搜索对该外部地址的引用
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(extSym.getAddress());
        while (it.hasNext()) {
            Reference ref = it.next();
            Address from = ref.getFromAddress();
            Function func = getFunctionContaining(from);
            if (func != null && func.isThunk()) return func;
        }

        return null;
    }

    /** 找 thunk 函数的所有调用者地址 */
    private List<Address> findThunkCallers(Function thunk) {
        List<Address> callers = new ArrayList<>();
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(thunk.getEntryPoint());
        while (it.hasNext()) {
            Reference ref = it.next();
            if (ref.getReferenceType().isCall()) {
                callers.add(ref.getFromAddress());
            }
        }
        return callers;
    }

    /** 反编译函数并输出 */
    private void decompileFunc(Function func, int maxLines) {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        ConsoleTaskMonitor monitor = new ConsoleTaskMonitor();

        DecompileResults result = decomp.decompileFunction(func, 30, monitor);
        if (result.decompileCompleted()) {
            String code = result.getDecompiledFunction().getC();
            String[] lines = code.split("\n");
            int limit = Math.min(lines.length, maxLines);
            for (int i = 0; i < limit; i++) {
                log(lines[i]);
            }
            if (lines.length > maxLines) {
                log("  ... (" + (lines.length - maxLines) + " more lines)");
            }
        } else {
            log("  DECOMPILE ERROR: " + result.getErrorMessage());
        }
    }

    /** 完整分析一个 API */
    private void analyzeImport(String symName, String label) {
        log("\n>>> " + label + " (" + symName + ")");

        Function thunk = findThunkFor(symName);
        if (thunk == null) {
            log("  No thunk found");
            return;
        }
        log("  Thunk: " + thunk.getName() + " @ " + thunk.getEntryPoint());

        List<Address> callers = findThunkCallers(thunk);
        log("  Callers: " + callers.size());

        Set<String> done = new HashSet<>();
        for (Address callAddr : callers) {
            Function caller = getFunctionContaining(callAddr);
            if (caller == null) {
                log("  Call @ " + callAddr + " → no function at this addr");
                continue;
            }
            String key = caller.getEntryPoint().toString();
            if (done.contains(key)) continue;
            done.add(key);

            log("\n--- " + caller.getName() + " @ " + key + " ---");
            decompileFunc(caller, 150);
        }
    }

    /** 反编译 0x220141 附近的包构造代码 */
    private void analyzePktCtr() {
        log("\n>>> Packet construction area (@ 0x220141)");
        Address addr = currentProgram.getImageBase().add(0x220141);
        log("  Address: " + addr);

        Function func = getFunctionContaining(addr);
        if (func != null) {
            log("\n--- " + func.getName() + " @ " + func.getEntryPoint() + " ---");
            decompileFunc(func, 200);
        } else {
            log("  No function found at " + addr);
            // 尝试反编译周围的函数
            Function before = getFunctionBefore(addr);
            Function after = getFunctionAfter(addr);
            if (before != null) {
                log("\n--- Closest before: " + before.getName() + " @ " + before.getEntryPoint() + " ---");
                decompileFunc(before, 200);
            }
            if (after != null) {
                log("\n--- Closest after: " + after.getName() + " @ " + after.getEntryPoint() + " ---");
                decompileFunc(after, 200);
            }
        }
    }

    @Override
    public void run() throws Exception {
        new File(outDir).mkdirs();

        log("============================================================");
        log("FreeStyle.exe Crypto Analysis v2 — Ghidra Headless (Java)");
        log("============================================================");

        // 目标 1: WSASendTo
        analyzeImport("WSASendTo", "UDP Send");

        // 目标 2: CryptEncrypt
        analyzeImport("CryptEncrypt", "Encrypt API");

        // 目标 3: CryptImportKey
        analyzeImport("CryptImportKey", "Key Import");

        // 目标 4: 包构造代码
        analyzePktCtr();

        // Save
        String outFile = outDir + File.separator + "crypto_analysis2.txt";
        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            pw.print(out.toString());
        }
        log("\nOutput saved to " + outFile);
    }
}
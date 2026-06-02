/* GhidraExtractCrypto.java — Ghidra headless post-analysis (Java)
 * 编译: javac -cp "D:\py\反编译\ghidra_12.0.1_PUBLIC\Ghidra\Framework\Generic\lib\Generic.jar;..." GhidraExtractCrypto.java
 */

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.pcode.*;
import ghidra.util.task.ConsoleTaskMonitor;

import java.io.*;
import java.util.*;

public class GhidraExtractCrypto extends GhidraScript {

    private StringBuilder out = new StringBuilder();
    private String outDir = "D:\\py\\反编译\\FreeStyle\\ghidra_output";

    private void log(String msg) {
        out.append(msg).append('\n');
        println(msg);
    }

    private void findAndLogExternalRefs(String symName, String label) {
        log("\n>>> " + label + " (" + symName + ") XREFs");
        SymbolTable st = currentProgram.getSymbolTable();
        Symbol sym = null;
        for (Symbol s : st.getExternalSymbols()) {
            if (s.getName().equals(symName)) {
                sym = s;
                break;
            }
        }
        if (sym == null) {
            log("  NOT FOUND in import table");
            return;
        }
        Address addr = sym.getAddress();
        log("  External symbol @ " + addr);

        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(addr);
        int count = 0;
        while (it.hasNext() && count < 20) {
            Reference ref = it.next();
            Address from = ref.getFromAddress();
            Function func = getFunctionContaining(from);
            String fname = (func != null) ? func.getName() : "?";
            String faddr = (func != null) ? func.getEntryPoint().toString() : "?";
            log("    " + from + " → " + fname + " @ " + faddr);
            count++;
        }
        log("  Total: " + count + " xrefs");
    }

    private void decompileAndLog(String symName) {
        log("\n>>> Decompiling " + symName + " caller functions");

        SymbolTable st = currentProgram.getSymbolTable();
        Symbol sym = null;
        for (Symbol s : st.getExternalSymbols()) {
            if (s.getName().equals(symName)) {
                sym = s;
                break;
            }
        }
        if (sym == null) {
            log("  NOT FOUND");
            return;
        }

        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(sym.getAddress());
        Set<String> done = new HashSet<>();

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        ConsoleTaskMonitor monitor = new ConsoleTaskMonitor();

        while (it.hasNext()) {
            Reference ref = it.next();
            Function func = getFunctionContaining(ref.getFromAddress());
            if (func == null) continue;
            String key = func.getEntryPoint().toString();
            if (done.contains(key)) continue;
            done.add(key);

            log("\n--- " + func.getName() + " @ " + key + " ---");
            DecompileResults result = decomp.decompileFunction(func, 30, monitor);
            if (result.decompileCompleted()) {
                String code = result.getDecompiledFunction().getC();
                String[] lines = code.split("\n");
                for (int i = 0; i < Math.min(lines.length, 200); i++) {
                    log(lines[i]);
                }
                if (lines.length > 200) {
                    log("  ... (" + (lines.length - 200) + " more lines)");
                }
            } else {
                log("  DECOMPILE ERROR: " + result.getErrorMessage());
            }
        }
    }

    private void scanAesSboxRefs() {
        log("\n>>> AES S-box (0x2442ef8) XREFs");

        Address base = currentProgram.getImageBase();
        Address sbox = base.add(0x2442ef8);
        log("  S-box address: " + sbox);

        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(sbox);
        int count = 0;
        while (it.hasNext() && count < 30) {
            Reference ref = it.next();
            Address from = ref.getFromAddress();
            Function func = getFunctionContaining(from);
            String fname = (func != null) ? func.getName() : "?";
            String faddr = (func != null) ? func.getEntryPoint().toString() : "?";
            log("    " + from + " → " + fname + " @ " + faddr);
            count++;
        }
        if (count == 0) log("  No xrefs (may be accessed via calculated offset)");
        else log("  Total xrefs found: " + count);
    }

    @Override
    public void run() throws Exception {
        new File(outDir).mkdirs();

        log("============================================================");
        log("FreeStyle.exe Crypto Analysis — Ghidra Headless (Java)");
        log("============================================================");

        // 1. WSASendTo
        findAndLogExternalRefs("WSASendTo", "UDP send");

        // 2. CryptEncrypt
        findAndLogExternalRefs("CryptEncrypt", "encrypt API");

        // 3. AES S-box
        scanAesSboxRefs();

        // 4. Decompile WSASendTo callers
        decompileAndLog("WSASendTo");

        // 5. Decompile CryptEncrypt callers
        decompileAndLog("CryptEncrypt");

        // Save
        String outFile = outDir + File.separator + "crypto_analysis.txt";
        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            pw.print(out.toString());
        }
        log("\nOutput saved to " + outFile);
    }
}
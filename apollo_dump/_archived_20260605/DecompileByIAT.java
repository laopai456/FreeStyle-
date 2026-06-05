// Apollo.sys: decompile all functions by scanning IAT call references
//@category Export
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;
import java.util.*;

public class DecompileByIAT extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    public void run() throws Exception {
        new File(OUT).mkdirs();

        // Step 1: Find IAT section range
        MemoryBlock iatBlock = currentProgram.getMemory().getBlock(".idata");
        if (iatBlock == null) {
            printf("No .idata block found!\n");
            return;
        }
        Address iatStart = iatBlock.getStart();
        Address iatEnd = iatBlock.getEnd();
        printf("IAT range: 0x%x - 0x%x\n", iatStart.getOffset(), iatEnd.getOffset());

        // Step 2: For each IAT entry, find xrefs (who reads/calls it)
        Map<Long,String> apiNames = new HashMap<>();
        Map<Long,List<Long>> apiCallers = new TreeMap<>(); // apiIatAddr -> list of caller func addrs

        // Get all external symbols with their IAT thunk addresses
        SymbolTable st = currentProgram.getSymbolTable();
        SymbolIterator es = st.getExternalSymbols();
        while (es.hasNext()) {
            Symbol s = es.next();
            // Each external symbol has references FROM it (the thunk in IAT)
            Reference[] refs = s.getReferences(null);
            for (Reference r : refs) {
                long iatAddr = r.getToAddress().getOffset();
                if (iatAddr >= iatStart.getOffset() && iatAddr <= iatEnd.getOffset()) {
                    apiNames.put(iatAddr, s.getName());
                    // Now look for references TO this IAT address
                    Address iatAddrObj = r.getToAddress();
                    ReferenceIterator xrefs = currentProgram.getReferenceManager().getReferencesTo(iatAddrObj);
                    while (xrefs.hasNext()) {
                        Reference xref = xrefs.next();
                        if (xref.getReferenceType().isRead()) {
                            long fromAddr = xref.getFromAddress().getOffset();
                            Function caller = currentProgram.getFunctionManager().getFunctionContaining(
                                xref.getFromAddress());
                            if (caller != null) {
                                long callerAddr = caller.getEntryPoint().getOffset();
                                if (!apiCallers.containsKey(iatAddr)) {
                                    apiCallers.put(iatAddr, new ArrayList<>());
                                }
                                if (!apiCallers.get(iatAddr).contains(callerAddr)) {
                                    apiCallers.get(iatAddr).add(callerAddr);
                                }
                            }
                        }
                    }
                }
            }
        }

        printf("IAT entries with API names: %d\n", apiNames.size());
        printf("IAT entries with callers: %d\n", apiCallers.size());

        // Step 3: Map function addresses to their API calls
        Map<Long,List<String>> funcAPIs = new TreeMap<>();
        for (Map.Entry<Long,List<Long>> e : apiCallers.entrySet()) {
            long iatAddr = e.getKey();
            String apiName = apiNames.get(iatAddr);
            if (apiName == null) apiName = "unk_" + Long.toHexString(iatAddr);
            for (Long funcAddr : e.getValue()) {
                if (!funcAPIs.containsKey(funcAddr)) {
                    funcAPIs.put(funcAddr, new ArrayList<>());
                }
                if (!funcAPIs.get(funcAddr).contains(apiName)) {
                    funcAPIs.get(funcAddr).add(apiName);
                }
            }
        }

        printf("Functions with API calls: %d\n", funcAPIs.size());

        // Step 4: Write report and decompile
        FileWriter fw = new FileWriter(OUT + "\\Apollo_sys_api_callers_v2.txt");
        fw.write("Apollo.sys API Callers (v2 - IAT xrefs)\n");
        fw.write("======================================\n\n");

        for (Map.Entry<Long,List<String>> e : funcAPIs.entrySet()) {
            Function f = currentProgram.getFunctionManager().getFunctionAt(toAddr(e.getKey()));
            int sz = f != null ? (int)f.getBody().getNumAddresses() : 0;
            fw.write(String.format("0x%016x (%4dB) => %s\n", e.getKey(), sz, String.join(", ", e.getValue())));
        }
        fw.close();

        // Step 5: Decompile all API-calling functions
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        int ok = 0, fail = 0;

        for (Map.Entry<Long,List<String>> e : funcAPIs.entrySet()) {
            Function f = currentProgram.getFunctionManager().getFunctionAt(toAddr(e.getKey()));
            if (f == null) continue;

            try {
                DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
                if (r != null && r.decompileCompleted()) {
                    String c = r.getDecompiledFunction().getC();
                    String apis = String.join("_", e.getValue().subList(0, Math.min(4, e.getValue().size())));
                    apis = apis.replaceAll("[^a-zA-Z0-9_]", "_").substring(0, Math.min(60, apis.length()));
                    String path = OUT + "\\Apollo_sys_API_" + apis + ".c";
                    FileWriter f2 = new FileWriter(path);
                    f2.write("/* " + f.getName() + " @ 0x" + Long.toHexString(e.getKey()) + " */\n");
                    f2.write("/* APIs: " + String.join(", ", e.getValue()) + " */\n");
                    f2.write(String.format("/* size: %dB */\n", f.getBody().getNumAddresses()));
                    f2.write(c);
                    f2.write("\n");
                    f2.close();
                    ok++;
                    printf("[OK] %s => %s (%d chars, %d lines)\n", f.getName(), apis, c.length(), c.split("\n").length);
                } else {
                    fail++;
                }
            } catch (Exception ex) { fail++; }
        }
        decomp.dispose();
        printf("Done: %d ok, %d fail (of %d total)\n", ok, fail, funcAPIs.size());
    }
}
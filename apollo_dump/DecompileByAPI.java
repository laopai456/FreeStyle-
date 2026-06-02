// Apollo.sys: identify functions by their API call patterns, then decompile
//@category Export
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;
import java.util.*;

public class DecompileByAPI extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    // Key API names to search for (case-insensitive)
    private static final String[] APIS = {
        "KdDisableDebugger", "KdDebuggerEnabled",
        "IoCreateDevice", "IoDeleteDevice", "IoCreateSymbolicLink", "IoDeleteSymbolicLink",
        "PsLookupProcessByProcessId", "PsGetCurrentProcessId",
        "PsSetCreateThreadNotifyRoutine", "PsSetLoadImageNotifyRoutine",
        "PsReferenceProcessFilePointer", "IoQueryFileDosDeviceName",
        "ObfDereferenceObject", "ExFreePoolWithTag",
        "RtlUnicodeToMultiByteN", "RtlInitUnicodeString",
        "IofCompleteRequest", "IoGetCurrentIrpStackLocation",
        "MmMapIoSpace", "MmUnmapIoSpace", "MmGetPhysicalAddress",
        "KeSetEvent", "KeWaitForSingleObject", "KeInitializeEvent",
        "ExAllocatePoolWithTag", "ExAllocatePool", "ExFreePool",
        "ProbeForRead", "ProbeForWrite", "MmIsAddressValid",
        "MmCopyVirtualMemory", "ZwOpenProcess", "ZwQueryInformationProcess",
        "ZwQuerySystemInformation", "ZwClose",
        "ObRegisterCallbacks", "ObUnRegisterCallbacks",
        "CmRegisterCallback", "CmUnRegisterCallback",
    };

    public void run() throws Exception {
        new File(OUT).mkdirs();

        // Step 1: Build map of import address -> API name
        Map<Long,String> importMap = new HashMap<>();
        SymbolTable st = currentProgram.getSymbolTable();
        for (Symbol s : st.getExternalSymbols()) {
            Reference[] refs = s.getReferences(null);
            for (Reference r : refs) {
                importMap.put(r.getFromAddress().getOffset(), s.getName());
            }
        }
        printf("Import references: %d\n", importMap.size());

        // Step 2: For each function, check which APIs it calls
        FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(true);
        // Map: apiName -> list of calling function addresses
        Map<String,List<Long>> apiCallers = new TreeMap<>();

        while (fit.hasNext()) {
            Function f = fit.next();
            long fAddr = f.getEntryPoint().getOffset();

            // Scan all instructions in this function for calls to imports
            InstructionIterator iit = currentProgram.getListing().getInstructions(f.getBody(), true);
            while (iit.hasNext()) {
                Instruction inst = iit.next();
                Reference[] memRefs = inst.getReferencesFrom();
                for (Reference r : memRefs) {
                    if (r.getReferenceType().isCall()) {
                        long target = r.getToAddress().getOffset();
                        String apiName = importMap.get(target);
                        if (apiName != null) {
                            if (!apiCallers.containsKey(apiName)) {
                                apiCallers.put(apiName, new ArrayList<>());
                            }
                            apiCallers.get(apiName).add(fAddr);
                        }
                    }
                }
            }
        }

        // Step 3: Find "interesting" functions (call 2+ different interesting APIs)
        Map<Long,List<String>> funcAPIs = new TreeMap<>();
        for (Map.Entry<String,List<Long>> e : apiCallers.entrySet()) {
            String api = e.getKey();
            for (Long addr : e.getValue()) {
                if (!funcAPIs.containsKey(addr)) {
                    funcAPIs.put(addr, new ArrayList<>());
                }
                funcAPIs.get(addr).add(api);
            }
        }

        FileWriter fw = new FileWriter(OUT + "\\Apollo_sys_api_callers.txt");
        fw.write("Functions with API calls:\n");
        fw.write("=========================\n\n");

        List<Long> toDecompile = new ArrayList<>();
        for (Map.Entry<Long,List<String>> e : funcAPIs.entrySet()) {
            if (e.getValue().size() >= 2) {
                fw.write(String.format("0x%016x: %s\n", e.getKey(), String.join(", ", e.getValue())));
                toDecompile.add(e.getKey());
            }
        }
        fw.write(String.format("\nTotal: %d functions call 2+ APIs\n", toDecompile.size()));

        // Also write functions calling single interesting API
        for (String api : APIS) {
            List<Long> callers = apiCallers.get(api.toLowerCase());
            if (callers != null) {
                fw.write(String.format("\n[%s] called by:\n", api));
                for (Long addr : callers) {
                    fw.write(String.format("  0x%016x\n", addr));
                    if (!toDecompile.contains(addr)) toDecompile.add(addr);
                }
            }
        }
        fw.close();

        printf("Functions calling 2+ interesting APIs: %d\n", toDecompile.size());
        printf("Single-API callers total: %d\n", toDecompile.size());

        // Step 4: Decompile all identified functions
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        int ok = 0, skip = 0;

        for (Long addr : toDecompile) {
            Function f = currentProgram.getFunctionManager().getFunctionAt(toAddr(addr));
            if (f == null) { skip++; continue; }

            try {
                DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
                if (r != null && r.decompileCompleted()) {
                    String c = r.getDecompiledFunction().getC();
                    String name = f.getName();
                    List<String> apis = funcAPIs.get(addr);
                    String tag = apis != null ? String.join("_", apis.subList(0, Math.min(3, apis.size()))) : "unknown";
                    tag = tag.replaceAll("[^a-zA-Z0-9_]", "_");
                    String path = OUT + "\\Apollo_sys_api_" + tag + "_" + Long.toHexString(addr) + ".c";
                    FileWriter f2 = new FileWriter(path);
                    f2.write("/* " + name + " @ 0x" + Long.toHexString(addr) + " */\n");
                    f2.write("/* API calls: " + (apis != null ? String.join(", ", apis) : "none") + " */\n");
                    f2.write(String.format("/* size: %d bytes */\n", f.getBody().getNumAddresses()));
                    f2.write(c);
                    f2.write("\n");
                    f2.close();
                    ok++;
                    printf("[OK] %s => %s (%d chars)\n", name, path, c.length());
                }
            } catch (Exception e) {}
        }
        decomp.dispose();
        printf("Done: %d decompiled, %d skipped\n", ok, skip);
    }
}
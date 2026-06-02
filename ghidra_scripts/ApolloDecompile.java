/* ApolloDecompile.java — Ghidra headless post-analysis script
 * Exports decompiled functions, strings, xrefs for Apollo binaries.
 * Usage: analyzeHeadless <project> <name> -import <file> -postScript ApolloDecompile.java
 */
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.util.task.ConsoleTaskMonitor;

import java.io.*;
import java.util.*;

public class ApolloDecompile extends GhidraScript {

    private String outDir;
    private int funcCount = 0;
    private int decompileCount = 0;
    private int decompileFail = 0;
    private List<String> interestingFuncs = new ArrayList<>();

    private void logp(PrintWriter pw, String msg) {
        pw.println(msg);
        pw.flush();
    }

    private boolean isInteresting(Function func) {
        String name = func.getName().toLowerCase();
        if (name.contains("crc") || name.contains("check") || name.contains("protect") ||
            name.contains("virtual") || name.contains("device") || name.contains("thread") ||
            name.contains("debug") || name.contains("detect") || name.contains("hook") ||
            name.contains("patch") || name.contains("scan") || name.contains("verify") ||
            name.contains("apollo") || name.contains("sleep") || name.contains("query")) {
            return true;
        }
        // Check if function references interesting strings
        AddressSetView body = func.getBody();
        Memory mem = currentProgram.getMemory();
        try {
            MemoryIterator it = mem.iterator(body, true);
            // Quick scan for string refs is too expensive, skip
        } catch (Exception e) {}
        return false;
    }

    @Override
    public void run() throws Exception {
        String binName = currentProgram.getExecutablePath();
        // Extract filename
        String baseName = new File(binName).getName();
        baseName = baseName.replaceAll("[^a-zA-Z0-9._-]", "_");

        outDir = System.getProperty("user.home") + File.separator + "apollo_decompile";
        new File(outDir).mkdirs();

        PrintWriter summary = new PrintWriter(new FileWriter(outDir + File.separator + baseName + "_summary.txt"));
        PrintWriter allFuncs = new PrintWriter(new FileWriter(outDir + File.separator + baseName + "_functions.txt"));
        PrintWriter decompOut = new PrintWriter(new FileWriter(outDir + File.separator + baseName + "_decompiled.c"));

        logp(summary, "=== Apollo Decompilation: " + baseName + " ===");
        logp(summary, "Image base: " + currentProgram.getImageBase());
        logp(summary, "Language: " + currentProgram.getLanguage());
        logp(summary, "");

        // 1. Enumerate all functions
        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        ConsoleTaskMonitor monitor = new ConsoleTaskMonitor();

        logp(summary, "--- Function Summary ---");
        Iterator<Function> fit = fm.getFunctions(true);
        List<Function> allFunctionList = new ArrayList<>();
        while (fit.hasNext()) {
            Function func = fit.next();
            allFunctionList.add(func);
            funcCount++;
        }

        logp(summary, "Total functions: " + funcCount);

        // 2. List all functions with size and signature
        logp(allFuncs, "addr,size,name,signature,is_thunk,namespace");
        for (Function func : allFunctionList) {
            String line = String.format("0x%s,%d,%s,%s,%b,%s",
                func.getEntryPoint(),
                func.getBody().getNumAddresses(),
                func.getName(),
                func.getSignature().replace(',', ';'),
                func.isThunk(),
                func.getParentNamespace().getName());
            logp(allFuncs, line);
        }

        // 3. Search for interesting strings
        logp(summary, "\n--- Interesting Strings ---");
        PrintWriter strOut = new PrintWriter(new FileWriter(outDir + File.separator + baseName + "_strings.txt"));
        Memory mem = currentProgram.getMemory();
        Address start = mem.getMinAddress();
        Address end = mem.getMaxAddress();
        DataIterator dit = currentProgram.getListing().getDefinedData(start, end);
        List<String> keyStrings = Arrays.asList(
            "virtual", "protect", "crc", "device", "thread", "sleep", "debug",
            "detect", "check", "apollo", "query", "memory", "process", "module",
            "hook", "inject", "hack", "cheat", "scan", "page", "ioctl",
            "ntquery", "virtualalloc", "readprocess", "writeprocess",
            "openprocess", "createthread", "loadlibrary", "getprocaddress",
            "suspend", "resume", "terminate", "crash", "kill", "guard",
            "integrity", "hash", "checksum", "verify", "validate"
        );

        int strCount = 0;
        while (dit.hasNext()) {
            Data d = dit.next();
            if (d.hasStringValue()) {
                String val = d.getDefaultValueRepresentation().toLowerCase();
                boolean interesting = false;
                for (String key : keyStrings) {
                    if (val.contains(key)) {
                        interesting = true;
                        break;
                    }
                }
                if (interesting) {
                    String addr = d.getAddress().toString();
                    // Get xrefs to this string
                    ReferenceManager rm = currentProgram.getReferenceManager();
                    ReferenceIterator refs = rm.getReferencesTo(d.getAddress());
                    List<String> refFrom = new ArrayList<>();
                    int rc = 0;
                    while (refs.hasNext() && rc < 10) {
                        Reference ref = refs.next();
                        Function caller = fm.getFunctionContaining(ref.getFromAddress());
                        String callerName = caller != null ? caller.getName() + "@" + caller.getEntryPoint() : "?";
                        refFrom.add(callerName);
                        rc++;
                    }
                    String line = String.format("%s: %s  refs=[%s]", addr, d.getDefaultValueRepresentation(), String.join(",", refFrom));
                    logp(summary, line);
                    logp(strOut, line);
                    strCount++;
                }
            }
        }
        logp(summary, "Interesting strings found: " + strCount);

        // 4. Decompile functions
        // Strategy: decompile all if < 500 functions, otherwise only interesting ones + largest 100
        List<Function> toDecompile = new ArrayList<>();

        if (allFunctionList.size() <= 500) {
            toDecompile.addAll(allFunctionList);
        } else {
            // Add interesting ones
            for (Function func : allFunctionList) {
                if (isInteresting(func)) {
                    toDecompile.add(func);
                }
            }
            // Add largest 200
            List<Function> sorted = new ArrayList<>(allFunctionList);
            sorted.sort((a, b) -> Long.compare(b.getBody().getNumAddresses(), a.getBody().getNumAddresses()));
            for (Function func : sorted) {
                if (toDecompile.size() >= 300) break;
                if (!toDecompile.contains(func)) {
                    toDecompile.add(func);
                }
            }
        }

        logp(summary, "\n--- Decompiling " + toDecompile.size() + " functions ---");

        for (Function func : toDecompile) {
            String addr = func.getEntryPoint().toString();
            logp(decompOut, "\n// ==============================");
            logp(decompOut, "// Function: " + func.getName() + " @ " + addr);
            logp(decompOut, "// Signature: " + func.getSignature());
            logp(decompOut, "// Size: " + func.getBody().getNumAddresses() + " bytes");
            logp(decompOut, "// ==============================");

            try {
                DecompileResults result = decomp.decompileFunction(func, 60, monitor);
                if (result.decompileCompleted()) {
                    String code = result.getDecompiledFunction().getC();
                    logp(decompOut, code);
                    decompileCount++;
                } else {
                    logp(decompOut, "// DECOMPILE FAILED: " + result.getErrorMessage());
                    decompileFail++;
                }
            } catch (Exception e) {
                logp(decompOut, "// DECOMPILE ERROR: " + e.getMessage());
                decompileFail++;
            }
        }

        logp(summary, "\nDecompile success: " + decompileCount);
        logp(summary, "Decompile failed: " + decompileFail);
        logp(summary, "\nOutput files:");
        logp(summary, "  " + outDir + File.separator + baseName + "_summary.txt");
        logp(summary, "  " + outDir + File.separator + baseName + "_functions.txt");
        logp(summary, "  " + outDir + File.separator + baseName + "_strings.txt");
        logp(summary, "  " + outDir + File.separator + baseName + "_decompiled.c");

        summary.close();
        allFuncs.close();
        strOut.close();
        decompOut.close();
        decomp.dispose();

        println("ApolloDecompile complete: " + funcCount + " functions, " + decompileCount + " decompiled");
    }
}

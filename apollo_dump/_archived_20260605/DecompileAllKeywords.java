// Dump ALL Apollo.sys function names, then decompile keyword matches
//@category Export
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;
import java.util.ArrayList;

public class DecompileAllKeywords extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    // Keywords to search in function names (case insensitive)
    private static final String[] KWS = {
        "device", "ioctl", "dispatch", "create", "delete", "debug",
        "process", "protect", "whitelist", "verify", "pslookup",
        "query", "thread", "notify", "image", "load", "write",
        "read", "mmcopymemory", "probeforwrite", "probe", "map",
        "section", "allocate", "free", "pool", "registry",
        "hide", "stealth", "rootkit", "hook", "detour",
        "ssdt", "idt", "gdt", "msr", "cr0", "cr4", "dr",
        "obregister", "obcallback", "filter", "minifilter",
        "file", "ntopen", "ntcreate", "createsection",
        "ntquery", "ntset", "ntread", "ntwrite",
        "zwopen", "zwcreate", "zwquery", "zwset",
    };

    public void run() throws Exception {
        new File(OUT).mkdirs();

        // Step 1: Dump ALL function names
        FileWriter fw = new FileWriter(OUT + "\\Apollo_sys_all_functions_ghidra.txt");
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        java.util.List<Function> matches = new ArrayList<>();
        int total = 0;

        while (it.hasNext()) {
            Function f = it.next();
            total++;
            String n = f.getName().toLowerCase();
            long addr = f.getEntryPoint().getOffset();

            // Write all functions
            if (total % 200 == 1) {
                fw.write(String.format("; %d functions so far...\n", total));
            }

            // Check each keyword
            for (String kw : KWS) {
                if (n.contains(kw)) {
                    matches.add(f);
                    fw.write(String.format("0x%016x  %s  [MATCH: %s]\n", addr, f.getName(), kw));
                    break;
                }
            }
        }
        fw.close();

        printf("Total functions: %d, Keyword matches: %d\n", total, matches.size());

        // Step 2: Decompile all matched functions
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        int ok = 0, fail = 0, skip = 0;

        for (Function f : matches) {
            if (f == null) { skip++; continue; }
            try {
                DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
                if (r != null && r.decompileCompleted()) {
                    String c = r.getDecompiledFunction().getC();
                    String name = f.getName();
                    long addr = f.getEntryPoint().getOffset();
                    String path = OUT + "\\Apollo_sys_" + sanitize(name) + ".c";
                    FileWriter f2 = new FileWriter(path);
                    f2.write("/* " + name + " @ 0x" + Long.toHexString(addr) + " */\n");
                    f2.write(String.format("/* size: %d bytes */\n", f.getBody().getNumAddresses()));
                    f2.write(c);
                    f2.write("\n");
                    f2.close();
                    ok++;
                    printf("[OK] %s (%d chars, %d lines)\n", name, c.length(),
                           c.split("\n").length);
                } else {
                    fail++;
                }
            } catch (Exception e) {
                fail++;
            }
        }
        decomp.dispose();
        printf("Done: %d ok, %d fail, %d skip (of %d total, %d matched)\n",
               ok, fail, skip, total, matches.size());
    }

    private String sanitize(String s) {
        return s.replaceAll("[^a-zA-Z0-9_.-]", "_");
    }
}
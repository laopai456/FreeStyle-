// Decompile ALL Apollo.sys functions to a single file
//@category Export
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;

public class DecompileAllFunctions extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    public void run() throws Exception {
        new File(OUT).mkdirs();
        FileWriter fw = new FileWriter(OUT + "\\Apollo_sys_ALL_DECOMPILED.c");
        fw.write("// ============================================\n");
        fw.write("// Apollo.sys - ALL FUNCTIONS DECOMPILED\n");
        fw.write("// Ghidra 12.0.1 headless decompilation\n");
        fw.write("// ============================================\n\n");

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int total = 0, ok = 0, fail = 0;
        int skippedSmall = 0;

        while (it.hasNext()) {
            Function f = it.next();
            total++;
            long addr = f.getEntryPoint().getOffset();
            int sz = (int)f.getBody().getNumAddresses();

            // Skip tiny 1-instruction stubs (likely thunks/jumps)
            if (sz <= 8) { skippedSmall++; continue; }

            try {
                DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
                if (r != null && r.decompileCompleted()) {
                    String c = r.getDecompiledFunction().getC();
                    fw.write(String.format("//── %s  @0x%016x  (%dB) ──\n",
                        f.getName(), addr, sz));
                    fw.write(c);
                    fw.write("\n\n");
                    ok++;
                } else {
                    fail++;
                }
            } catch (Exception e) {
                fail++;
            }
        }
        decomp.dispose();
        fw.write(String.format("\n// Total: %d functions, %d decompiled, %d failed, %d skipped (<=8B)\n",
            total, ok, fail, skippedSmall));
        fw.close();
        printf("ALL DONE: %d total, %d decompiled, %d failed, %d small skipped\n",
            total, ok, fail, skippedSmall);
    }
}
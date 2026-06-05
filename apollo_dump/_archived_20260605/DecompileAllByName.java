// Decompile ALL functions from any binary, output with correct binary name
//@category Export
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;

public class DecompileAllByName extends GhidraScript {

    public void run() throws Exception {
        String progName = currentProgram.getName().replaceAll("\\.(sys|dll|exe)$", "");
        String outDir = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";
        String outPath = outDir + "\\" + progName + "_ALL_DECOMPILED.c";
        new File(outDir).mkdirs();

        FileWriter fw = new FileWriter(outPath);
        fw.write("// " + progName + " - ALL DECOMPILED\n");
        fw.write("// Ghidra 12.0.1 headless\n");
        fw.write("// ====================\n\n");

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int total = 0, ok = 0, fail = 0, skipSmall = 0;

        while (it.hasNext()) {
            Function f = it.next();
            total++;
            long addr = f.getEntryPoint().getOffset();
            int sz = (int)f.getBody().getNumAddresses();

            if (sz <= 8) { skipSmall++; continue; }

            try {
                DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
                if (r != null && r.decompileCompleted()) {
                    String c = r.getDecompiledFunction().getC();
                    fw.write(String.format("//── %-30s @0x%016x (%dB) ──\n", f.getName(), addr, sz));
                    fw.write(c);
                    fw.write("\n\n");
                    ok++;
                } else { fail++; }
            } catch (Exception e) { fail++; }
        }
        decomp.dispose();
        fw.write(String.format("\n// %s: %d total, %d ok, %d fail, %d skipped(<=8B)\n",
            progName, total, ok, fail, skipSmall));
        fw.close();
        printf("%s: %d total, %d ok, %d fail, %d skipped\n", progName, total, ok, fail, skipSmall);
    }
}
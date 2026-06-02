// Decompile Apollo.sys dispatch functions + DR chain
//@category Export

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;

public class DecompileRound2Script extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    @Override
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        new File(OUT).mkdirs();
        
        // DeviceIoControl dispatch chain
        doFunc(decomp, 0x140239a21L, "DeviceIoControl_thunk");
        doFunc(decomp, 0x14023a0ddL, "Cleanup_thunk");
        
        // Functions called from Process_whitelist
        doFunc(decomp, 0x140001e54L, "Whitelist_precheck");
        
        // DR chain follow-up
        doFunc(decomp, 0x1400aa799L, "DR_chain_level2");
        
        // Additional functions from function list
        doFunc(decomp, 0x1400a1527L, "Large_9KB_func");
        doFunc(decomp, 0x1400a687aL, "Large_4KB_func");
        doFunc(decomp, 0x1400bc755L, "Large_4KB_func2");
        doFunc(decomp, 0x1400be80cL, "Large_3KB_func");
        doFunc(decomp, 0x1400a08e0L, "Large_2KB_func");
        doFunc(decomp, 0x140097badL, "Large_1KB_func");
        doFunc(decomp, 0x1400ac159L, "Mid_1KB_func");
        doFunc(decomp, 0x1400b686eL, "Mid_2KB_func");
        
        decomp.dispose();
        printf("Round 2 done.\n");
    }
    
    private void doFunc(DecompInterface decomp, long addr, String name) {
        try {
            Address a = toAddr(addr);
            Function f = currentProgram.getFunctionManager().getFunctionAt(a);
            if (f == null) {
                printf("[SKIP] %s @ 0x%x\n", name, addr);
                return;
            }
            DecompileResults r = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (r != null && r.decompileCompleted()) {
                String c = r.getDecompiledFunction().getC();
                String path = OUT + "\\Apollo_sys_" + name + ".c";
                FileWriter fw = new FileWriter(path);
                fw.write("/* " + name + " @ 0x" + Long.toHexString(addr) + " */\n");
                fw.write(c);
                fw.write("\n");
                fw.close();
                printf("[OK] %s (%d chars)\n", name, c.length());
                
                // Print first 30 lines for key functions
                String[] lines = c.split("\n");
                int max = Math.min(30, lines.length);
                for (int i = 0; i < max; i++) {
                    printf("  %s\n", lines[i]);
                }
                printf("  ... (%d total lines)\n\n", lines.length);
            } else {
                printf("[FAIL] %s: %s\n", name, r != null ? r.getErrorMessage() : "null");
            }
        } catch (Exception e) {
            printf("[ERR] %s: %s\n", name, e.toString());
        }
    }
}
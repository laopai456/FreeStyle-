// Decompile key Apollo.sys functions
//@category Export

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.FileWriter;
import java.io.File;

public class ExportDecompiledScript extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    @Override
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        
        printf("Program: %s, %d functions\n", 
            currentProgram.getName(), 
            currentProgram.getFunctionManager().getFunctionCount());
        
        new File(OUT).mkdirs();
        
        doFunc(decomp, 0x14008d00dL, "DeviceIoControl_dispatch");
        doFunc(decomp, 0x14013663aL, "Unknown_large_2");
        doFunc(decomp, 0x140001986L, "DR_clear_area");
        doFunc(decomp, 0x140001d48L, "Process_whitelist");
        doFunc(decomp, 0x1402399e8L, "KdDisableDebugger_loop");
        doFunc(decomp, 0x140239970L, "KdDebuggerEnabled_check");
        doFunc(decomp, 0x140239e6aL, "DriverEntry");
        doFunc(decomp, 0x1400016b0L, "Opaque_pred_1");
        doFunc(decomp, 0x1400016caL, "Opaque_pred_2");
        doFunc(decomp, 0x1400017e0L, "IRP_dispatch_stub");
        doFunc(decomp, 0x140063780L, "Control_flow_target");
        
        decomp.dispose();
        printf("Done.\n");
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
            } else {
                printf("[FAIL] %s: %s\n", name, r != null ? r.getErrorMessage() : "null");
            }
        } catch (Exception e) {
            printf("[ERR] %s: %s\n", name, e.toString());
        }
    }
}
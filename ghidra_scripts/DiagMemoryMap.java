// Quick diagnostic script: check segment layout and find function entry points
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import java.io.FileWriter;
import java.io.PrintWriter;

public class DiagMemoryMap extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String outputPath = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\ghidra_memory_map.txt";
        PrintWriter out = new PrintWriter(new FileWriter(outputPath));

        // Image base
        out.println("=== Image Base ===");
        out.println("Image Base: " + currentProgram.getImageBase());
        out.println("Default Address Space: " + currentProgram.getAddressFactory().getDefaultAddressSpace());

        // Memory segments
        out.println("\n=== Memory Segments ===");
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            out.println(String.format("%s: %s - %s (size=%d, read=%b, write=%b, exec=%b, initialized=%b)",
                block.getName(),
                block.getStart(),
                block.getEnd(),
                block.getSize(),
                block.isRead(), block.isWrite(), block.isExecute(), block.isInitialized()));
        }

        // Find function entries near known addresses
        out.println("\n=== Function Search Near Known Addresses ===");
        long[] knownAddrs = {0x22ECCD0L, 0x22EC130L, 0x229B0B0L, 0x2371B00L, 0x021C1F00L};
        String[] labels = {"AcquireSMD", "AcquireSMDEntry", "DDynActorCtor", "PPI_Handler", "FactoryFn"};

        for (int i = 0; i < knownAddrs.length; i++) {
            long addr = knownAddrs[i];
            out.println("\n" + labels[i] + " @ 0x" + Long.toHexString(addr));

            // Check if address exists in this program
            try {
                Address a = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addr);
                var mb = currentProgram.getMemory().getBlock(a);
                if (mb != null) {
                    out.println("  Block: " + mb.getName() + " exec=" + mb.isExecute());
                    var cu = currentProgram.getListing().getCodeUnitAt(a);
                    if (cu != null) {
                        out.println("  CodeUnit: " + cu.getClass().getSimpleName());
                        out.println("  Mnemonic: " + cu);
                    } else {
                        out.println("  No code unit at this address");
                    }
                } else {
                    out.println("  Address not in any memory block!");

                    // Try adding image base offset
                    long imageBase = currentProgram.getImageBase().getOffset();
                    out.println("  Image base: 0x" + Long.toHexString(imageBase));
                    long adjustedAddr = addr + imageBase;
                    out.println("  Adjusted: 0x" + Long.toHexString(adjustedAddr));

                    try {
                        Address aa = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(adjustedAddr);
                        var mb2 = currentProgram.getMemory().getBlock(aa);
                        if (mb2 != null) {
                            out.println("  Adjusted Block: " + mb2.getName() + " exec=" + mb2.isExecute());
                            var cu2 = currentProgram.getListing().getCodeUnitAt(aa);
                            if (cu2 != null) out.println("  Adjusted CodeUnit: " + cu2.getClass().getSimpleName());
                        } else {
                            out.println("  Adjusted address also not in any block");
                        }
                    } catch (Exception e) {
                        out.println("  Adjusted address error: " + e.getMessage());
                    }
                }
            } catch (Exception e) {
                out.println("  Error: " + e.getMessage());
            }
        }

        // Find functions containing AcquireSMD format string references
        out.println("\n=== Functions Near AcquireSMD String Refs ===");
        long[] strAddrs = {0x0284BA2CL, 0x0284BA6CL};
        for (long sa : strAddrs) {
            out.println("\nString @ 0x" + Long.toHexString(sa));
            Address strAddr = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(sa);
            // Check what block it's in
            var mb = currentProgram.getMemory().getBlock(strAddr);
            if (mb != null) out.println("  Block: " + mb.getName() + " exec=" + mb.isExecute());
        }

        // Search for functions in .text section
        out.println("\n=== Function Count & Coverage ===");
        int totalFns = 0;
        var fnIter = currentProgram.getFunctionManager().getFunctions(true);
        while (fnIter.hasNext()) { fnIter.next(); totalFns++; }
        out.println("Total functions: " + totalFns);

        // Check .text block function coverage
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (block.isExecute()) {
                out.println(block.getName() + " (" + block.getStart() + "-" + block.getEnd() + "): executable");
            }
        }

        out.close();
        println("Memory map diagnostic saved to: " + outputPath);
    }
}
// List all Apollo.sys memory blocks/sections
//@category Export
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.MemoryBlock;
import java.io.FileWriter;
import java.io.File;

public class ListSectionsScript extends GhidraScript {

    private static final String OUT = "D:\\py\\反编译\\FreeStyle\\apollo_dump\\r2_output";

    public void run() throws Exception {
        new File(OUT).mkdirs();
        FileWriter fw = new FileWriter(OUT + "\\Apollo_sys_sections_ghidra.txt");

        MemoryBlock[] blocks = currentProgram.getMemory().getBlocks();
        for (MemoryBlock b : blocks) {
            fw.write(String.format("%-20s  0x%016x - 0x%016x  %s  %s  %s  %dKB\n",
                b.getName(),
                b.getStart().getOffset(),
                b.getEnd().getOffset(),
                b.isExecute() ? "X" : " ",
                b.isWrite()   ? "W" : " ",
                b.isRead()    ? "R" : " ",
                b.getSize() / 1024));
        }
        fw.close();
        printf("Sections dumped: %s\n", OUT + "\\Apollo_sys_sections_ghidra.txt");
    }
}
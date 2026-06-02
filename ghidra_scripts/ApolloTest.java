// ApolloTest.java — minimal test script
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.io.*;

public class ApolloTest extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionManager fm = currentProgram.getFunctionManager();
        int count = 0;
        Iterator<Function> it = fm.getFunctions(true);
        while (it.hasNext()) { it.next(); count++; }
        String outDir = System.getProperty("user.home") + File.separator + "apollo_decompile";
        new File(outDir).mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(outDir + File.separator + "test_result.txt"));
        pw.println("Functions: " + count);
        pw.close();
        println("ApolloTest: " + count + " functions");
    }
}

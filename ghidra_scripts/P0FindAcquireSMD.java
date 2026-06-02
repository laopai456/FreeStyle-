// P0 Analysis Script: Find DGraphicAcquireSMD and related functions
// Outputs results to JSON file.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.Instruction;
import ghidra.util.task.ConsoleTaskMonitor;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;



public class P0FindAcquireSMD extends GhidraScript {

    private PrintWriter out;
    private DecompInterface decomp;
    private StringBuilder json = new StringBuilder();

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        String outputDir = args != null && args.length > 0 ? args[0] : "D:\\py\\反编译\\FreeStyle\\apollo_dump";
        String outputPath = outputDir + "\\ghidra_p0_output.json";
        out = new PrintWriter(new FileWriter(outputPath));

        json.append("{\n");
        json.append("  \"analysis_time\": \"").append(new Date()).append("\",\n");
        json.append("  \"program\": \"").append(currentProgram.getName()).append("\",\n");

        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        // P0 tasks
        task1_searchAcquireSMD();
        task2_searchResourceStrings();
        task3_verifyFunctions();
        task4_decompileKeyFunctions();
        task5_findWSASendTo();
        task6_searchCrypto();

        json.append("  \"status\": \"complete\"\n");
        json.append("}\n");

        out.print(json.toString());
        out.close();
        decomp.dispose();
        println("P0 analysis complete: " + outputPath);
    }

    // ===== Task 1: AcquireSMD string search =====
    private void task1_searchAcquireSMD() throws Exception {
        json.append("  \"acquire_smd_strings\": [\n");
        int count = 0;
        var it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            var d = it.next();
            if (d.hasStringValue()) {
                String v = d.getDefaultValueRepresentation();
                if (v.toLowerCase().contains("acquiresmd") || v.toLowerCase().contains("acquire_smd")) {
                    if (count > 0) json.append(",\n");
                    json.append("    {\"addr\":\"").append(d.getAddress()).append("\",\"val\":\"");
                    json.append(escapeJson(v)).append("\",\"xrefs\":[");
                    var refs = currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
                    boolean rfirst = true;
                    while (refs.hasNext()) {
                        var ref = refs.next();
                        if (!rfirst) json.append(",");
                        rfirst = false;
                        var fn = getFunctionContaining(ref.getFromAddress());
                        json.append("{\"from\":\"").append(ref.getFromAddress()).append("\",\"ref_type\":\"");
                        json.append(ref.getReferenceType()).append("\"");
                        if (fn != null) json.append(",\"fn\":\"").append(fn.getName()).append("\",\"fn_entry\":\"")
                            .append(fn.getEntryPoint()).append("\"");
                        json.append("}");
                    }
                    json.append("]}");
                    count++;
                }
            }
        }
        json.append("\n  ],\n");
        println("Task 1 AcquireSMD: " + count + " strings found");
    }

    // ===== Task 2: Resource strings =====
    private void task2_searchResourceStrings() throws Exception {
        json.append("  \"resource_strings\": {\n");
        String[] patterns = {".ppi", ".pak", ".smd", ".bml", "item_24", "item_26"};
        for (int pi = 0; pi < patterns.length; pi++) {
            String pat = patterns[pi];
            json.append("    \"").append(pat).append("\": [");
            int c = 0;
            var it = currentProgram.getListing().getDefinedData(true);
            while (it.hasNext() && c < 50 && !monitor.isCancelled()) {
                var d = it.next();
                if (d.hasStringValue()) {
                    String v = d.getDefaultValueRepresentation();
                    if (v.toLowerCase().contains(pat.toLowerCase())) {
                        if (c > 0) json.append(",");
                        var refs = currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
                        var rl = new ArrayList<Reference>();
                        while (refs.hasNext()) rl.add(refs.next());
                        json.append("{\"addr\":\"").append(d.getAddress()).append("\",\"val\":\"");
                        String sv = v.length() > 80 ? v.substring(0, 80) + "..." : v;
                        json.append(escapeJson(sv)).append("\",\"xrefs\":").append(rl.size()).append("}");
                        c++;
                    }
                }
            }
            json.append("]");
            if (pi < patterns.length - 1) json.append(",");
            json.append("\n");
            println("Task 2 '" + pat + "': " + c + " hits");
        }
        json.append("  },\n");
    }

    // ===== Task 3: Verify function addresses =====
    private void task3_verifyFunctions() throws Exception {
        json.append("  \"verified_functions\": {\n");
        long[] addrs = {0x22ECCD0L, 0x22EC130L, 0x229B0B0L, 0x236B8A0L, 0x229B4D0L,
                        0x02297810L, 0x021C1F00L, 0x21B46E0L, 0x2371B00L};
        String[] names = {"AcquireSMD_0x22ECCD0","AcquireSMD_0x22EC130","DDynamicActorCtor",
                          "DStaticActorCtor","DynamicInit","SetMotionType","FactoryFn",
                          "CharacterMotionParse","PPI_Handler"};

        for (int i = 0; i < addrs.length; i++) {
            Address a = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addrs[i]);
            Function fn = getFunctionAt(a);
            Listing listing = currentProgram.getListing();

            json.append("    \"").append(names[i]).append("\":");
            json.append("{\"addr\":\"0x").append(Long.toHexString(addrs[i])).append("\",\"is_fn\":");
            json.append(fn != null);

            if (fn != null) {
                json.append(",\"name\":\"").append(fn.getName()).append("\",\"entry\":\"")
                    .append(fn.getEntryPoint()).append("\",\"size\":").append(fn.getBody().getNumAddresses());
            } else {
                var cu = listing.getCodeUnitAt(a);
                json.append(",\"has_code\":").append(cu != null);
                if (cu instanceof Instruction) json.append(",\"is_instruction\":true");
            }

            // Callers
            var refs = currentProgram.getReferenceManager().getReferencesTo(a);
            int callers = 0;
            String fst = "none";
            while (refs.hasNext()) {
                var ref = refs.next();
                if (ref.getReferenceType().isCall()) {
                    var cfn = getFunctionContaining(ref.getFromAddress());
                    if (callers == 0 && cfn != null) fst = cfn.getName() + "@" + cfn.getEntryPoint();
                    callers++;
                }
            }
            json.append(",\"callers\":").append(callers);
            json.append(",\"first_caller\":\"").append(fst).append("\"}");
            if (i < addrs.length - 1) json.append(",");
            json.append("\n");
            println("Task 3 " + names[i] + ": fn=" + (fn != null) + " callers=" + callers);
        }
        json.append("  },\n");
    }

    // ===== Task 4: Decompile key functions =====
    private void task4_decompileKeyFunctions() throws Exception {
        json.append("  \"decompiled\": [\n");
        long[] addrs = {0x22EC130L, 0x2371B00L, 0x021C1F00L};
        String[] labels = {"AcquireSMDEntry","PPI_Handler","FactoryFn"};

        for (int i = 0; i < addrs.length; i++) {
            Address a = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addrs[i]);
            Function fn = getFunctionAt(a);

            json.append("    {\"label\":\"").append(labels[i]).append("\",\"addr\":\"0x")
                .append(Long.toHexString(addrs[i])).append("\",");

            if (fn != null) {
                DecompileResults r = decomp.decompileFunction(fn, 60, monitor);
                if (r != null && r.decompileCompleted()) {
                    String code = r.getDecompiledFunction().getC();
                    code = escapeJson(truncate(code, 5000));
                    json.append("\"status\":\"ok\",\"code\":\"").append(code).append("\"");
                } else {
                    json.append("\"status\":\"fail\",\"msg\":\"")
                        .append(r != null ? escapeJson(r.getErrorMessage()) : "null").append("\"");
                }
            } else {
                // Try to find and create function
                var ci = currentProgram.getListing().getInstructionAt(a);
                if (ci != null) {
                    try {
                        Function nfn = createFunction(a, null);
                        if (nfn != null) {
                            DecompileResults r = decomp.decompileFunction(nfn, 60, monitor);
                            if (r != null && r.decompileCompleted()) {
                                String code = r.getDecompiledFunction().getC();
                                code = escapeJson(truncate(code, 5000));
                                json.append("\"status\":\"created_ok\",\"code\":\"").append(code).append("\"");
                            } else {
                                json.append("\"status\":\"created_fail\"");
                            }
                        } else {
                            json.append("\"status\":\"no_create\"");
                        }
                    } catch (Exception ex) {
                        json.append("\"status\":\"error\",\"msg\":\"").append(escapeJson(ex.getMessage())).append("\"");
                    }
                } else {
                    json.append("\"status\":\"no_code\"");
                }
            }
            json.append("}");
            if (i < addrs.length - 1) json.append(",");
            json.append("\n");
            println("Task 4 " + labels[i] + ": decompiled");
        }
        json.append("  ],\n");
    }

    // ===== Task 5: WSASendTo callers =====
    private void task5_findWSASendTo() throws Exception {
        json.append("  \"wsasendto\": [\n");
        int si = 0;
        var syms = currentProgram.getSymbolTable().getExternalSymbols();
        while (syms.hasNext()) {
            var sym = syms.next();
            String nm = sym.getName().toLowerCase();
            if (nm.contains("wsasendto") || nm.contains("sendto") || nm.contains("wsasend")) {
                if (si > 0) json.append(",\n");
                json.append("    {\"sym\":\"").append(sym.getName()).append("\",\"addr\":\"")
                    .append(sym.getAddress()).append("\",\"callers\":[");
                var refs = currentProgram.getReferenceManager().getReferencesTo(sym.getAddress());
                int ci = 0;
                boolean ccfirst = true;
                while (refs.hasNext() && ci < 30) {
                    var ref = refs.next();
                    var cfn = getFunctionContaining(ref.getFromAddress());
                    if (ref.getReferenceType().isCall() && cfn != null) {
                        if (!ccfirst) json.append(",");
                        ccfirst = false;
                        json.append("{\"fn\":\"").append(cfn.getName()).append("\",\"entry\":\"")
                            .append(cfn.getEntryPoint()).append("\",\"at\":\"")
                            .append(ref.getFromAddress()).append("\"}");
                        ci++;
                    }
                }
                json.append("],\"count\":").append(ci).append("}");
                si++;
                println("Task 5 " + sym.getName() + ": " + ci + " callers");
            }
        }
        json.append("\n  ],\n");
    }

    // ===== Task 6: Crypto search =====
    private void task6_searchCrypto() throws Exception {
        json.append("  \"crypto\": {\n");
        long xorVal = 0x4db8a854L;
        byte[] pat = new byte[]{(byte)(xorVal & 0xFF), (byte)((xorVal>>8)&0xFF),
                                (byte)((xorVal>>16)&0xFF), (byte)((xorVal>>24)&0xFF)};
        json.append("    \"xor_4db8a854\": [");
        int found = 0;
        for (MemoryBlock blk : currentProgram.getMemory().getBlocks()) {
            if (blk.isExecute() && !monitor.isCancelled() && found < 20) {
                try {
                    byte[] buf = new byte[(int)Math.min(blk.getSize(), 0x100000)];
                    blk.getBytes(blk.getStart(), buf);
                    for (int j = 0; j < buf.length - 3 && found < 20; j++) {
                        if (buf[j]==pat[0] && buf[j+1]==pat[1] && buf[j+2]==pat[2] && buf[j+3]==pat[3]) {
                            if (found > 0) json.append(",");
                            long addr = blk.getStart().getOffset() + j;
                            json.append("\"0x").append(Long.toHexString(addr)).append("\"");
                            found++;
                        }
                    }
                } catch (Exception e) {}
            }
        }
        json.append("],\"count\":").append(found).append("\n  },\n");
        println("Task 6 XOR 0x4db8a854: " + found + " hits");
    }

    // ===== Utilities =====
    private static String escapeJson(String s) {
        if (s == null) return "";
        StringBuilder sb = new StringBuilder(s.length() + 20);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int)c));
                    else sb.append(c);
            }
        }
        return sb.toString();
    }

    private static String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() > max ? s.substring(0, max) + "..." : s;
    }
}
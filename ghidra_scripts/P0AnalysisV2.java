// P0 Analysis v2: Force disassembly at known addresses, create functions, decompile
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class P0AnalysisV2 extends GhidraScript {

    private PrintWriter out;
    private DecompInterface decomp;
    private StringBuilder json = new StringBuilder();

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        String outputDir = args != null && args.length > 0 ? args[0] : "D:\\py\\反编译\\FreeStyle\\apollo_dump";
        String outputPath = outputDir + "\\ghidra_p0_v2_output.json";
        out = new PrintWriter(new FileWriter(outputPath));

        json.append("{\n");
        json.append("  \"analysis_time\": \"").append(new Date()).append("\",\n");
        json.append("  \"program\": \"").append(currentProgram.getName()).append("\",\n");
        json.append("  \"image_base\": \"").append(currentProgram.getImageBase()).append("\",\n");

        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        // === Step 1: Force disassemble at known addresses ===
        forceDisassemble();

        // === Step 2: Search AcquireSMD strings ===
        searchAcquireSMD();

        // === Step 3: Search key resource strings ===
        searchResourceStrings();

        // === Step 4: Decompile found functions ===
        decompileFunctions();

        // === Step 5: WSASendTo analysis ===
        findWSASendTo();

        json.append("  \"status\": \"complete\"\n");
        json.append("}\n");

        out.print(json.toString());
        out.close();
        decomp.dispose();
        println("P0 v2 complete: " + outputPath);
    }

    private void forceDisassemble() throws Exception {
        json.append("  \"disassembly\": {\n");

        long[] addrs = {0x22ECCD0L, 0x22EC130L, 0x229B0B0L, 0x236B8A0L, 0x229B4D0L,
                        0x02297810L, 0x021C1F00L, 0x21B46E0L, 0x2371B00L};
        String[] names = {"AcquireSMD_0x22ECCD0","AcquireSMD_0x22EC130","DDynamicActorCtor",
                          "DStaticActorCtor","DynamicInit","SetMotionType","FactoryFn",
                          "CharacterMotionParse","PPI_Handler"};

        // First, disassemble a range around each address
        for (int i = 0; i < addrs.length; i++) {
            long addr = addrs[i];
            Address a = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addr);
            String name = names[i];

            // Force disassemble around each address and try to create functions
            disassemble(a);

            // Now check if a function was created
            Function fn = getFunctionAt(a);

            json.append("    \"").append(name).append("\": {");
            json.append("\"disassembled\": true, ");
            json.append("\"has_fn\": ").append(fn != null).append(", ");

            if (fn != null) {
                json.append("\"fn_name\": \"").append(fn.getName()).append("\", ");
                json.append("\"fn_entry\": \"").append(fn.getEntryPoint()).append("\", ");
                json.append("\"fn_size\": ").append(fn.getBody().getNumAddresses());
            } else {
                // Try to create function anyway
                var cu = currentProgram.getListing().getCodeUnitAt(a);
                boolean isInst = (cu instanceof Instruction);
                json.append("\"is_instruction\": ").append(isInst).append(", ");

                if (isInst) {
                    try {
                        Function newFn = createFunction(a, "FUN_" + Long.toHexString(addr));
                        if (newFn != null) {
                            json.append("\"created_fn\": true, ");
                            json.append("\"created_name\": \"").append(newFn.getName()).append("\", ");
                            json.append("\"created_entry\": \"").append(newFn.getEntryPoint()).append("\"");
                        } else {
                            json.append("\"created_fn\": false");
                        }
                    } catch (Exception e) {
                        json.append("\"created_fn\": false, \"error\": \"").append(escapeJson(e.getMessage())).append("\"");
                    }
                } else {
                    json.append("\"note\": \"still_data\"");
                }
            }

            json.append("}");
            if (i < addrs.length - 1) json.append(",");
            json.append("\n");

            println(name + " disassembled: " + (getFunctionAt(a) != null));
        }
        json.append("  },\n");
    }

    private void searchAcquireSMD() throws Exception {
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
                        var cfn = getFunctionContaining(ref.getFromAddress());
                        json.append("{\"from\":\"").append(ref.getFromAddress()).append("\"");
                        if (cfn != null) json.append(",\"fn\":\"").append(cfn.getName()).append("\",\"entry\":\"")
                            .append(cfn.getEntryPoint()).append("\"");
                        json.append("}");
                    }
                    json.append("]}");
                    count++;
                }
            }
        }
        json.append("\n  ],\n");
        println("AcquireSMD strings: " + count);
    }

    private void searchResourceStrings() throws Exception {
        json.append("  \"resource_strings\": {\n");
        String[] patterns = {".ppi", ".pak", ".smd", ".bml"};
        for (int pi = 0; pi < patterns.length; pi++) {
            String pat = patterns[pi];
            json.append("    \"").append(pat).append("\": [");
            int c = 0;
            var it = currentProgram.getListing().getDefinedData(true);
            while (it.hasNext() && c < 30 && !monitor.isCancelled()) {
                var d = it.next();
                if (d.hasStringValue()) {
                    String v = d.getDefaultValueRepresentation();
                    if (v.toLowerCase().contains(pat.toLowerCase())) {
                        if (c > 0) json.append(",");
                        var refs = currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
                        var rl = new ArrayList<Reference>();
                        while (refs.hasNext()) rl.add(refs.next());
                        json.append("{\"addr\":\"").append(d.getAddress()).append("\"");
                        json.append(",\"xrefs\":").append(rl.size()).append("}");
                        c++;
                    }
                }
            }
            json.append("]");
            if (pi < patterns.length - 1) json.append(",");
            json.append("\n");
            println("  " + pat + ": " + c);
        }
        json.append("  },\n");
    }

    private void decompileFunctions() throws Exception {
        json.append("  \"decompiled\": [\n");

        // Decompile functions at known addresses
        long[] addrs = {0x22EC130L, 0x2371B00L, 0x021C1F00L, 0x229B0B0L, 0x229B4D0L};
        String[] labels = {"AcquireSMDEntry","PPI_Handler","FactoryFn","DDynamicActorCtor","DynamicInit"};

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
                json.append("\"status\":\"no_function\"");
            }
            json.append("}");
            if (i < addrs.length - 1) json.append(",");
            json.append("\n");
            println("  Decompiled: " + labels[i]);
        }
        json.append("  ],\n");
    }

    private void findWSASendTo() throws Exception {
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
                boolean first = true;
                while (refs.hasNext() && ci < 30) {
                    var ref = refs.next();
                    var cfn = getFunctionContaining(ref.getFromAddress());
                    if (ref.getReferenceType().isCall() && cfn != null) {
                        if (!first) json.append(",");
                        first = false;
                        json.append("{\"fn\":\"").append(cfn.getName()).append("\",\"at\":\"")
                            .append(ref.getFromAddress()).append("\"}");
                        ci++;
                    }
                }
                json.append("],\"count\":").append(ci).append("}");
                si++;
            }
        }
        json.append("\n  ]\n");
        println("WSASendTo symbols: " + si);
    }

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
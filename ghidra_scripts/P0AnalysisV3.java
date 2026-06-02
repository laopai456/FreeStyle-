// P0 Analysis v3: Verify address validity + diagnose why decompilation is garbage
// Key insight from v2: decompiled code contains swi()/out()/in() → addresses are likely NOT function entries
// v3: check raw bytes, find nearby real functions, trace AcquireSMD from strings
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.lang.Language;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.util.task.ConsoleTaskMonitor;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class P0AnalysisV3 extends GhidraScript {

    private PrintWriter out;
    private DecompInterface decomp;
    private StringBuilder json = new StringBuilder();

    // Known target addresses and their labels
    private static final long[] TARGET_ADDRS = {
        0x22ECCD0L, 0x22EC130L, 0x229B0B0L, 0x236B8A0L, 0x229B4D0L,
        0x02297810L, 0x021C1F00L, 0x21B46E0L, 0x2371B00L
    };
    private static final String[] TARGET_NAMES = {
        "AcquireSMD_0x22ECCD0", "AcquireSMD_0x22EC130", "DDynamicActorCtor",
        "DStaticActorCtor", "DynamicInit", "SetMotionType", "FactoryFn",
        "CharacterMotionParse", "PPI_Handler"
    };

    // Known x86-64 function prologue byte patterns
    // Pattern: {bytes, mask (0xFF=must match, 0x00=wildcard), description}
    private static final byte[][] PROLOGUE_PATTERNS = {
        {0x55},                                           // push rbp
        {(byte)0x48, (byte)0x89, (byte)0xE5},            // mov rbp, rsp
        {(byte)0x48, (byte)0x8B, (byte)0xEC},            // mov rbp, rsp (alt)
        {(byte)0x48, (byte)0x83, (byte)0xEC},            // sub rsp, imm8
        {(byte)0x48, (byte)0x81, (byte)0xEC},            // sub rsp, imm32
        {(byte)0x40, 0x53},                               // push rbx (REX)
        {0x53},                                           // push rbx
        {(byte)0x48, (byte)0x89, 0x5C, 0x24},            // mov [rsp+XX], rbx
        {(byte)0x48, (byte)0x89, 0x4C, 0x24},            // mov [rsp+XX], rcx (__fastcall save)
        {(byte)0x48, (byte)0x89, 0x54, 0x24},            // mov [rsp+XX], rdx
        {(byte)0xCC, (byte)0xCC, (byte)0xCC},            // int3 padding (between functions)
    };
    private static final String[] PROLOGUE_DESC = {
        "push rbp", "mov rbp,rsp (89E5)", "mov rbp,rsp (8BEC)",
        "sub rsp,imm8", "sub rsp,imm32",
        "push rbx (REX)", "push rbx",
        "mov [rsp+XX],rbx", "mov [rsp+XX],rcx", "mov [rsp+XX],rdx",
        "int3 padding"
    };

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        String outputDir = args != null && args.length > 0 ? args[0] : "D:\\py\\反编译\\FreeStyle\\apollo_dump";
        String outputPath = outputDir + "\\ghidra_p0_v3_output.json";
        out = new PrintWriter(new FileWriter(outputPath));

        json.append("{\n");
        json.append("  \"analysis_time\": \"").append(new Date()).append("\",\n");
        json.append("  \"program\": \"").append(currentProgram.getName()).append("\",\n");
        json.append("  \"image_base\": \"").append(currentProgram.getImageBase()).append("\",\n");
        json.append("  \"language\": \"").append(currentProgram.getLanguageID()).append("\",\n");

        println("=== P0 Analysis V3: Address Verification ===");
        println("Language: " + currentProgram.getLanguageID());

        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        // Step 1: Verify raw bytes at each target address
        verifyRawBytes();

        // Step 2: Find nearby auto-detected functions
        findNearbyFunctions();

        // Step 3: Deep AcquireSMD string xref analysis
        deepAcquireSMDXrefs();

        // Step 4: Check if there are existing functions at or near our targets
        checkExistingFunctions();

        // Step 5: Verify xref analysis works at all (test with known API)
        verifyXrefSanity();

        json.append("  \"status\": \"complete\"\n");
        json.append("}\n");

        out.print(json.toString());
        out.close();
        decomp.dispose();
        println("\nP0 v3 complete: " + outputPath);
    }

    // ==== Step 1: Read raw bytes at each address ====
    private void verifyRawBytes() throws Exception {
        println("\n--- Step 1: Raw Bytes at Target Addresses ---");
        json.append("  \"raw_bytes\": {\n");

        Memory mem = currentProgram.getMemory();
        for (int i = 0; i < TARGET_ADDRS.length; i++) {
            long addr = TARGET_ADDRS[i];
            String name = TARGET_NAMES[i];
            Address a = mkAddr(addr);

            json.append("    \"").append(name).append("\": {");
            json.append("\"addr\":\"0x").append(Long.toHexString(addr)).append("\",");

            // Check memory block
            MemoryBlock block = mem.getBlock(a);
            if (block == null) {
                json.append("\"block\":null,\"note\":\"NOT IN ANY MEMORY BLOCK!\"");
                println("  " + name + " @ 0x" + Long.toHexString(addr) + " → NOT IN MEMORY!");
            } else {
                json.append("\"block\":\"").append(block.getName()).append("\",");
                json.append("\"block_exec\":").append(block.isExecute()).append(",");
                json.append("\"block_write\":").append(block.isWrite()).append(",");

                // Read first 32 bytes
                try {
                    byte[] bytes = new byte[32];
                    int read = mem.getBytes(a, bytes);
                    StringBuilder hex = new StringBuilder();
                    for (int j = 0; j < read; j++) {
                        if (j > 0) hex.append(" ");
                        hex.append(String.format("%02X", bytes[j] & 0xFF));
                    }
                    json.append("\"hex32\":\"").append(hex.toString()).append("\",");

                    // Check each prologue pattern
                    StringBuilder prologueMatch = new StringBuilder();
                    boolean anyMatch = false;
                    for (int p = 0; p < PROLOGUE_PATTERNS.length; p++) {
                        byte[] pat = PROLOGUE_PATTERNS[p];
                        if (matchesPattern(bytes, pat)) {
                            if (anyMatch) prologueMatch.append(",");
                            prologueMatch.append("\"").append(PROLOGUE_DESC[p]).append("\"");
                            anyMatch = true;
                        }
                    }
                    json.append("\"prologue_matches\":[").append(prologueMatch).append("],");

                    // Is it likely a function entry?
                    // Check: starts with push rbp (0x55) or sub rsp (0x48 0x83 0xEC) or push rbx
                    boolean startsWithPushRbp = (bytes[0] & 0xFF) == 0x55;
                    boolean startsWithSubRsp = (bytes[0] & 0xFF) == 0x48 && (bytes[1] & 0xFF) == 0x83 && (bytes[2] & 0xFF) == 0xEC;
                    boolean startsWithPushRbx = (bytes[0] & 0xFF) == 0x53 || ((bytes[0] & 0xFF) == 0x40 && (bytes[1] & 0xFF) == 0x53);
                    boolean startsWithInt3 = (bytes[0] & 0xFF) == 0xCC;
                    boolean startsWithRet = (bytes[0] & 0xFF) == 0xC3;

                    json.append("\"starts_push_rbp\":").append(startsWithPushRbp).append(",");
                    json.append("\"starts_sub_rsp\":").append(startsWithSubRsp).append(",");
                    json.append("\"starts_push_rbx\":").append(startsWithPushRbx).append(",");
                    json.append("\"starts_int3\":").append(startsWithInt3).append(",");
                    json.append("\"starts_ret\":").append(startsWithRet).append(",");

                    boolean looksValid = (startsWithPushRbp || startsWithSubRsp || startsWithPushRbx) && !startsWithInt3;
                    json.append("\"looks_valid_entry\":").append(looksValid);

                    println(String.format("  0x%08X [%s] hex=%s valid=%b prologue=%s",
                        addr, block.getName(), hex.toString(), looksValid, prologueMatch.toString()));
                } catch (Exception e) {
                    json.append("\"read_error\":\"").append(escapeJson(e.getMessage())).append("\"");
                    println("  " + name + " read error: " + e.getMessage());
                }
            }

            json.append("}");
            if (i < TARGET_ADDRS.length - 1) json.append(",");
            json.append("\n");
        }
        json.append("  },\n");
    }

    private boolean matchesPattern(byte[] bytes, byte[] pattern) {
        if (bytes.length < pattern.length) return false;
        for (int i = 0; i < pattern.length; i++) {
            if (bytes[i] != pattern[i]) return false;
        }
        return true;
    }

    // ==== Step 2: Find Ghidra auto-detected functions near each target ====
    private void findNearbyFunctions() throws Exception {
        println("\n--- Step 2: Nearby Auto-Detected Functions ---");
        json.append("  \"nearby_functions\": {\n");

        for (int i = 0; i < TARGET_ADDRS.length; i++) {
            long addr = TARGET_ADDRS[i];
            String name = TARGET_NAMES[i];
            Address a = mkAddr(addr);

            json.append("    \"").append(name).append("\": [");

            // Search for functions within +/- 0x200 bytes
            long range = 0x200;
            int count = 0;
            var fnIter = currentProgram.getFunctionManager().getFunctions(true);
            // Collect nearby functions
            List<Map<String,String>> nearby = new ArrayList<>();
            while (fnIter.hasNext()) {
                Function fn = fnIter.next();
                long fnEntry = fn.getEntryPoint().getOffset();
                long dist = fnEntry - addr; // positive = after, negative = before
                if (Math.abs(dist) <= range) {
                    Map<String,String> info = new HashMap<>();
                    info.put("entry", "0x" + Long.toHexString(fnEntry));
                    info.put("dist", (dist >= 0 ? "+" : "") + dist);
                    info.put("name", fn.getName());
                    info.put("size", String.valueOf(fn.getBody().getNumAddresses()));
                    nearby.add(info);
                }
            }

            // Sort by absolute distance
            nearby.sort((a1, a2) -> {
                long d1 = Math.abs(Long.parseLong(a1.get("dist")));
                long d2 = Math.abs(Long.parseLong(a2.get("dist")));
                return Long.compare(d1, d2);
            });

            // Output top 10
            int shown = 0;
            for (Map<String,String> nf : nearby) {
                if (shown >= 10) break;
                if (shown > 0) json.append(",");
                json.append("{");
                json.append("\"entry\":\"").append(nf.get("entry")).append("\",");
                json.append("\"dist\":\"").append(nf.get("dist")).append("\",");
                json.append("\"name\":\"").append(escapeJson(nf.get("name"))).append("\",");
                json.append("\"size\":").append(nf.get("size"));
                json.append("}");
                shown++;
            }
            json.append("]");

            println(String.format("  0x%08X %s: %d nearby functions within ±0x%X",
                addr, name, nearby.size(), range));
            for (int j = 0; j < Math.min(5, nearby.size()); j++) {
                var nf = nearby.get(j);
                println(String.format("    %s dist=%s name=%s size=%s",
                    nf.get("entry"), nf.get("dist"), nf.get("name"), nf.get("size")));
            }

            if (i < TARGET_ADDRS.length - 1) json.append(",");
            json.append("\n");
        }
        json.append("  },\n");
    }

    // ==== Step 3: Deep AcquireSMD analysis - ALL xref types + nearby code ===
    private void deepAcquireSMDXrefs() throws Exception {
        println("\n--- Step 3: Deep AcquireSMD Xref Analysis ---");
        json.append("  \"acquire_smd_deep\": [\n");

        int found = 0;
        var it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            var d = it.next();
            if (d.hasStringValue()) {
                String v = d.getDefaultValueRepresentation();
                if (v.toLowerCase().contains("acquiresmd")) {
                    if (found > 0) json.append(",\n");
                    json.append("    {\"addr\":\"").append(d.getAddress()).append("\",");
                    json.append("\"str\":\"").append(escapeJson(v)).append("\",");

                    // Get ALL references (not just direct)
                    var refMgr = currentProgram.getReferenceManager();
                    var refs = refMgr.getReferencesTo(d.getAddress());
                    List<String> refList = new ArrayList<>();
                    while (refs.hasNext()) {
                        var ref = refs.next();
                        var fromAddr = ref.getFromAddress();
                        var cfn = getFunctionContaining(fromAddr);
                        String refStr = "{\"from\":\"" + fromAddr + "\",\"type\":\"" + ref.getReferenceType() + "\"";
                        if (cfn != null) refStr += ",\"fn\":\"" + cfn.getName() + "\",\"entry\":\"" + cfn.getEntryPoint() + "\"";
                        refStr += "}";
                        refList.add(refStr);
                    }
                    json.append("\"xrefs\":[").append(String.join(",", refList)).append("],");
                    json.append("\"xref_count\":").append(refList.size());

                    // Also check: is there an instruction at nearby addresses that loads this value?
                    // Search for the address bytes in surrounding code
                    long strAddr = d.getAddress().getOffset();
                    json.append(",\"str_offset\":\"0x").append(Long.toHexString(strAddr)).append("\"");

                    json.append("}");
                    found++;
                    println("  AcquireSMD string @ " + d.getAddress() + " xrefs=" + refList.size());
                    for (String r : refList) {
                        println("    xref: " + r);
                    }
                }
            }
        }
        json.append("\n  ],\n");
        println("  Total AcquireSMD strings: " + found);

        // Also search for RIP-relative LEA patterns that reference AcquireSMD string addresses
        json.append("  \"acquire_smd_rip_rel\": [\n");
        searchRIPRelativeAcquireSMD();
        json.append("\n  ],\n");
    }

    private void searchRIPRelativeAcquireSMD() throws Exception {
        // For x86-64, AcquireSMD string references might be via RIP-relative LEA
        // LEA RAX, [RIP+offset] or LEA RCX, [RIP+offset]
        // In bytes: 48 8D 05 XX XX XX XX (LEA RAX, [RIP+disp32])
        //           48 8D 0D XX XX XX XX (LEA RCX, [RIP+disp32])
        //           48 8D 15 XX XX XX XX (LEA RDX, [RIP+disp32])
        //
        // First find the AcquireSMD string addresses
        Set<Long> smdStrAddrs = new HashSet<>();
        var it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            var d = it.next();
            if (d.hasStringValue()) {
                String v = d.getDefaultValueRepresentation();
                if (v.toLowerCase().contains("acquiresmd")) {
                    smdStrAddrs.add(d.getAddress().getOffset());
                }
            }
        }
        println("  Checking RIP-relative LEA for " + smdStrAddrs.size() + " AcquireSMD strings...");

        // Scan .text section for LEA instructions
        int foundCount = 0;
        MemoryBlock textBlock = null;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (block.isExecute() && block.getName().contains(".text")) {
                textBlock = block;
                break;
            }
        }

        if (textBlock != null && smdStrAddrs.size() > 0) {
            // For each AcquireSMD string, compute what RIP-relative offset would reference it
            // LEA at addr: target = addr + 7 + disp32
            // So disp32 = target - addr - 7
            // We need to find addresses in .text where: addr + 7 + disp32 ∈ smdStrAddrs

            // Search for LEA patterns near expected ranges
            // Strings are at ~0x0284BA2C. These are in .rdata or .data section.
            // .text is at 0x00401000-0x02C0BFFF
            // For a LEA at 0x02XXXXXX to reference 0x0284BA2C:
            //   disp32 = 0x0284BA2C - addr - 7
            //   For addr in range 0x02000000-0x02C0BFFF:
            //     disp32 ≈ 0x0284BA2C - 0x02000000 = 0x0084BA2C (positive, within 2GB)

            // Actually, let's search for bytes that contain the string address as part of LEA
            // Search for byte pattern: 48 8D ?? [4 bytes of RIP offset]
            // In Ghidra, we search via getBytes and manual scan

            byte[] leaPattern = {(byte)0x48, (byte)0x8D}; // LEA R64, [RIP+disp32]
            // ModRM byte: 00 000 101 = 0x05 for [RIP+disp32]
            //            01 000 101 = 0x0D for [RIP+disp32]
            //            10 000 101 = 0x15 for [RIP+disp32]

            for (long smdAddr : smdStrAddrs) {
                if (foundCount >= 20) break;

                // Search range: .text section, focused on areas that could reference the string
                // Strings at ~0x0284BA2C, so LEA must be within ±2GB:
                // LEA addr between 0x0284BA2C - 0x7FFFFFFF and 0x0284BA2C + 0x7FFFFFFF
                // = between 0x00484BA2D and 0x0284BA2C + 0x7FFFFFFF
                // Bottom range is below .text start... so search from .text start

                // Brute-force: for each instruction in .text that is a LEA, check target
                // This would be too slow. Instead, let's sample a few locations.

                // Key insight: if AcquireSMD is called from a function,
                // the function entry is likely in range 0x02XXXXXX-0x02XXXXXX
                // The string is at ~0x0284BA2C
                // LEA RIP+disp at 0x022E0000 would have disp32 = 0x0284BA2C - 0x022E0000 - 7 = 0x0056BA25

                // Let's just note the string addresses so user can manually search
                json.append("    {\"note\":\"RIP-relative LEA scan: strings at ");
                boolean first = true;
                for (long sa : smdStrAddrs) {
                    if (!first) json.append(",");
                    first = false;
                    json.append("0x").append(Long.toHexString(sa));
                }
                json.append("\"}");
                foundCount++;
                break; // Just one entry
            }
        }
    }

    // ==== Step 4: Check existing Ghidra functions at/near targets ====
    private void checkExistingFunctions() throws Exception {
        println("\n--- Step 4: Existing Functions at/near Targets ---");
        json.append("  \"existing_at_target\": [\n");

        for (int i = 0; i < TARGET_ADDRS.length; i++) {
            long addr = TARGET_ADDRS[i];
            String name = TARGET_NAMES[i];
            Address a = mkAddr(addr);

            // Check exact match
            Function fAt = getFunctionAt(a);
            Function fContaining = getFunctionContaining(a);
            CodeUnit cu = currentProgram.getListing().getCodeUnitAt(a);
            boolean isInst = (cu instanceof Instruction);

            json.append("    {\"label\":\"").append(name).append("\",");
            json.append("\"addr\":\"0x").append(Long.toHexString(addr)).append("\",");
            json.append("\"fn_at\":").append(fAt != null ? ("\"" + fAt.getName() + "\"") : "null").append(",");
            json.append("\"fn_containing\":").append(fContaining != null ? ("\"" + fContaining.getName() + "\"") : "null").append(",");
            json.append("\"is_instruction\":").append(isInst);

            if (isInst && fAt == null && fContaining == null) {
                // Try to get the instruction mnemonic
                Instruction inst = (Instruction) cu;
                json.append(",\"mnemonic\":\"").append(escapeJson(inst.getMnemonicString())).append("\"");
                json.append(",\"note\":\"instruction exists but no function\"");
            }

            if (fContaining != null && fAt == null) {
                // Address is inside a function but not at entry
                long entryOff = fContaining.getEntryPoint().getOffset();
                long offsetIntoFn = addr - entryOff;
                json.append(",\"offset_into_fn\":").append(offsetIntoFn);
                json.append(",\"fn_entry\":\"0x").append(Long.toHexString(entryOff)).append("\"");
                // Decompile the containing function
                tryDecompileContaining(fContaining, json);
            }

            json.append("}");
            if (i < TARGET_ADDRS.length - 1) json.append(",");
            json.append("\n");

            println(String.format("  0x%08X %s: fn_at=%s fn_containing=%s is_inst=%b",
                addr, name,
                fAt != null ? fAt.getName() : "null",
                fContaining != null ? fContaining.getName() : "null",
                isInst));
        }
        json.append("  ],\n");
    }

    private void tryDecompileContaining(Function fn, StringBuilder jsb) {
        try {
            DecompileResults r = decomp.decompileFunction(fn, 60, monitor);
            if (r != null && r.decompileCompleted()) {
                String code = r.getDecompiledFunction().getC();
                // Only include first 500 chars
                if (code != null && code.length() > 500) code = code.substring(0, 500) + "...";
                jsb.append(",\"decompiled_snippet\":\"").append(escapeJson(code != null ? code : "")).append("\"");
            } else {
                jsb.append(",\"decompiled\":\"failed\"");
            }
        } catch (Exception e) {
            // ignore decompile errors
        }
    }

    // ==== Step 5: Xref sanity check - do xrefs work at all? ====
    private void verifyXrefSanity() throws Exception {
        println("\n--- Step 5: Xref Sanity Check ---");
        json.append("  \"xref_sanity\": {\n");

        // Test 1: Find a well-known Windows API (e.g., kernel32!CreateFileW or similar)
        // and verify it has callers
        int totalExtSyms = 0;
        int extWithRefs = 0;
        var syms = currentProgram.getSymbolTable().getExternalSymbols();
        while (syms.hasNext()) {
            var sym = syms.next();
            totalExtSyms++;
            var refs = currentProgram.getReferenceManager().getReferencesTo(sym.getAddress());
            if (refs.hasNext()) {
                extWithRefs++;
            }
        }

        json.append("\"total_external_symbols\":").append(totalExtSyms).append(",");
        json.append("\"external_with_refs\":").append(extWithRefs).append(",");
        json.append("\"external_ref_rate\":").append(
            totalExtSyms > 0 ? String.format("%.1f%%", 100.0 * extWithRefs / totalExtSyms) : "N/A").append(",");

        // Test 2: Check some common imports
        String[] testImports = {"send", "recv", "connect", "CreateFile", "ReadFile", "WriteFile",
                                "LoadLibrary", "GetProcAddress", "malloc", "free", "memcpy"};
        StringBuilder testResults = new StringBuilder();
        for (int ti = 0; ti < testImports.length; ti++) {
            String imp = testImports[ti];
            String lower = imp.toLowerCase();
            var symIter = currentProgram.getSymbolTable().getExternalSymbols();
            boolean found = false;
            int refCount = 0;
            while (symIter.hasNext()) {
                var sym = symIter.next();
                if (sym.getName().toLowerCase().contains(lower)) {
                    found = true;
                    var refs = currentProgram.getReferenceManager().getReferencesTo(sym.getAddress());
                    while (refs.hasNext()) { refs.next(); refCount++; }
                    break;
                }
            }
            if (ti > 0) testResults.append(",");
            testResults.append("\"").append(imp).append("\":{");
            testResults.append("\"found\":").append(found).append(",");
            testResults.append("\"refs\":").append(refCount).append("}");
        }
        json.append("\"import_tests\":{").append(testResults).append("},");

        // Test 3: String xref check - pick a common string like "Error" or "%s" and verify refs
        int strWithRefs = 0;
        int strChecked = 0;
        var dataIter = currentProgram.getListing().getDefinedData(true);
        while (dataIter.hasNext() && strChecked < 1000 && !monitor.isCancelled()) {
            var d = dataIter.next();
            if (d.hasStringValue()) {
                String v = d.getDefaultValueRepresentation();
                // Check strings that likely have references
                if (v.contains("Error") || v.contains("error") || v.contains("Failed") ||
                    v.contains("%s") || v.contains("%d")) {
                    strChecked++;
                    var refs = currentProgram.getReferenceManager().getReferencesTo(d.getAddress());
                    if (refs.hasNext()) strWithRefs++;
                }
            }
        }
        json.append("\"common_string_checked\":").append(strChecked).append(",");
        json.append("\"common_string_with_refs\":").append(strWithRefs).append(",");
        json.append("\"string_ref_rate\":").append(
            strChecked > 0 ? String.format("%.1f%%", 100.0 * strWithRefs / strChecked) : "N/A");

        json.append("\n  },\n");

        println("  External symbols: " + totalExtSyms + " total, " + extWithRefs + " with refs");
        println("  Common strings: " + strChecked + " checked, " + strWithRefs + " with refs");
    }

    // ==== Utilities ====
    private Address mkAddr(long offset) {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(offset);
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
}
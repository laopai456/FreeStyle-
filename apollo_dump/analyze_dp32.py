import struct, os

dp32 = r'D:\py\x32\plugins\x64dbg_mcp.dp32'
data = open(dp32, 'rb').read()

pe_off = struct.unpack_from('<I', data, 0x3C)[0]

# Import table
import_rva = struct.unpack_from('<I', data, pe_off + 0x7C)[0]
import_size = struct.unpack_from('<I', data, pe_off + 0x80)[0]

# Find all imported DLLs by scanning for DLL names
print("=== Imported DLLs ===")
dlls = []
i = 0
while i < len(data) - 5:
    if data[i:i+4] == b'.dll':
        start = i
        while start > 0 and data[start-1] >= 0x20 and data[start-1] < 0x7F:
            start -= 1
        name = data[start:i+4].decode('ascii', errors='replace')
        if name not in dlls:
            dlls.append(name)
        i += 4
    else:
        i += 1

for d in dlls:
    print(f"  {d}")

# Check for specific runtime DLLs
print("\n=== Runtime check ===")
vc_dlls = [d for d in dlls if 'VCRUNTIME' in d or 'MSVCP' in d or 'MSVCR' in d or 'UCRT' in d]
if vc_dlls:
    print(f"  Needs: {vc_dlls}")
    print(f"  These come from: Visual C++ Redistributable 2015-2022")
else:
    print("  No MSVC runtime DLLs found - may use static linking")

# Check export table
export_rva = struct.unpack_from('<I', data, pe_off + 0x78)[0]
export_size = struct.unpack_from('<I', data, pe_off + 0x7C)[0]
print(f"\n  Export RVA: 0x{export_rva:X}, Size: {export_size}")

# Check for DllMain in export names
if export_rva > 0:
    # Find section containing export RVA
    num_sections = struct.unpack_from('<H', data, pe_off + 6)[0]
    opt_size = struct.unpack_from('<H', data, pe_off + 20)[0]
    section_start = pe_off + 24 + opt_size
    for s in range(num_sections):
        s_off = section_start + s * 40
        s_rva = struct.unpack_from('<I', data, s_off + 12)[0]
        s_vsize = struct.unpack_from('<I', data, s_off + 8)[0]
        s_raw = struct.unpack_from('<I', data, s_off + 20)[0]
        if s_rva <= export_rva < s_rva + s_vsize:
            export_offset = export_rva - s_rva + s_raw
            num_funcs = struct.unpack_from('<I', data, export_offset + 20)[0]
            num_names = struct.unpack_from('<I', data, export_offset + 24)[0]
            name_rva = struct.unpack_from('<I', data, export_offset + 32)[0]
            print(f"  Exports: {num_funcs} functions, {num_names} names")
            break

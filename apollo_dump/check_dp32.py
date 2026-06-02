import struct

# Check both plugin files
for path in [r'D:\py\x32\plugins\x64dbg_mcp.dp32',
             r'D:\py\x64dbg-new\release\x32\plugins\x64dbg_mcp.dp32']:
    try:
        data = open(path, 'rb').read()
        print(f'\n{path}')
        print(f'  Size: {len(data)} bytes')
        if data[:2] == b'MZ':
            pe_off = struct.unpack_from('<I', data, 0x3C)[0]
            machine = struct.unpack_from('<H', data, pe_off+4)[0]
            print(f'  Machine: {"x86" if machine==0x14C else "x64" if machine==0x8664 else "unknown"}')
            # Check exports
            export_rva = struct.unpack_from('<I', data, pe_off+0x78)[0]
            print(f'  Export table RVA: 0x{export_rva:X}')
            # Check for DllMain
            if b'DllMain' in data:
                print(f'  Contains "DllMain": YES')
            else:
                print(f'  Contains "DllMain": NO')
            if b'_DllMain' in data:
                print(f'  Contains "_DllMain": YES')
            # Check import table
            import_rva = struct.unpack_from('<I', data, pe_off+0x7C)[0]
            print(f'  Import table RVA: 0x{import_rva:X}')
            # List DLL imports
            dlls = set()
            pos = 0
            while True:
                idx = data.find(b'.dll', pos)
                if idx < 0: break
                start = idx
                while start > 0 and data[start-1] >= 0x20 and data[start-1] < 0x7F:
                    start -= 1
                dlls.add(data[start:idx+4].decode('ascii', errors='replace'))
                pos = idx + 4
            print(f'  Referenced DLLs: {sorted(dlls)}')
    except FileNotFoundError:
        print(f'\n{path} - NOT FOUND')

import struct
data = open(r'd:\py\release\x32\plugins\x64dbg_mcp.dp32', 'rb').read()
print(f'Size: {len(data)} bytes')
pe_off = struct.unpack_from('<I', data, 0x3C)[0]
machine = struct.unpack_from('<H', data, pe_off+4)[0]
arch = 'x86' if machine == 0x14C else 'x64' if machine == 0x8664 else 'unknown'
print(f'Machine: {arch}')

dlls = set()
i = 0
while i < len(data) - 5:
    if data[i:i+4] == b'.dll':
        start = i
        while start > 0 and data[start-1] >= 0x20 and data[start-1] < 0x7F:
            start -= 1
        dlls.add(data[start:i+4].decode('ascii', errors='replace'))
        i += 4
    else:
        i += 1
print('DLLs:')
for d in sorted(dlls): print(f'  {d}')

# Check subsystem
subsystem = struct.unpack_from('<H', data, pe_off + 92)[0]
print(f'Subsystem: {subsystem} (2=GUI, 3=Console)')

# Check DLL characteristics
dll_chars = struct.unpack_from('<H', data, pe_off + 94)[0]
print(f'DLL Characteristics: 0x{dll_chars:X}')

# Check if DllMain exists as export
if b'DllMain' in data:
    print('Contains DllMain string: YES')
else:
    print('Contains DllMain string: NO')

# Check for MSVC runtime dependency
msvc = [d for d in dlls if 'MSVCP' in d or 'VCRUNTIME' in d or 'UCRT' in d]
if msvc:
    print(f'MSVC runtime needed: {msvc}')

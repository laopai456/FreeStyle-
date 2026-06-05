import struct
data = open(r'D:\py\x32\release\x32\plugins\x64dbg_mcp.dp32', 'rb').read()
print(f'Size: {len(data)} bytes')
print(f'First 4 bytes: {data[:4].hex()}')
if data[:2] == b'MZ':
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    machine = struct.unpack_from('<H', data, pe_offset+4)[0]
    arch = 'x86' if machine == 0x14C else 'x64' if machine == 0x8664 else 'unknown'
    print(f'PE offset: 0x{pe_offset:X}')
    print(f'Machine: 0x{machine:X} ({arch})')

import struct
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_PATH = os.path.join(SCRIPT_DIR, 'FreeStyle.exe')
DUMP_PATH = os.path.join(SCRIPT_DIR, '..', 'dump', 'dump_text.bin')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'dump', 'FreeStyle_patched.exe')

with open(EXE_PATH, 'rb') as f:
    exe_data = bytearray(f.read())

# PE signature offset
e_lfanew = struct.unpack_from('<I', exe_data, 0x3C)[0]
print(f'[+] PE signature @ 0x{e_lfanew:X}')

# Number of sections
num_sections = struct.unpack_from('<H', exe_data, e_lfanew + 6)[0]
print(f'[+] Sections: {num_sections}')

# Section headers start after PE header
section_offset = e_lfanew + 248
print(f'[+] Section headers @ 0x{section_offset:X}')

text_section = None
for i in range(num_sections):
    sec_start = section_offset + i * 40
    sec_name = exe_data[sec_start:sec_start+8].rstrip(b'\x00').decode('ascii', errors='replace')
    sec_vsize = struct.unpack_from('<I', exe_data, sec_start + 8)[0]
    sec_vaddr = struct.unpack_from('<I', exe_data, sec_start + 12)[0]
    sec_rsize = struct.unpack_from('<I', exe_data, sec_start + 16)[0]
    sec_rptr = struct.unpack_from('<I', exe_data, sec_start + 20)[0]
    print(f'  [{i}] {sec_name}: VA=0x{sec_vaddr:X} VSz={sec_vsize} RawPtr=0x{sec_rptr:X} RawSz={sec_rsize}')
    if sec_name == '.text':
        text_section = (sec_start, sec_vaddr, sec_vsize, sec_rptr, sec_rsize)

if text_section is None:
    print('[!] .text section not found')
    exit(1)

sec_start, sec_vaddr, sec_vsize, sec_rptr, sec_rsize = text_section
print(f'\n[+] .text: raw_ptr=0x{sec_rptr:X}, raw_size={sec_rsize}')

dump_size = os.path.getsize(DUMP_PATH)
print(f'[+] dump_text.bin: {dump_size} bytes')

if dump_size > sec_rsize:
    print(f'[!] dump ({dump_size}) > raw_size ({sec_rsize}), will truncate')
    dump_data = open(DUMP_PATH, 'rb').read()[:sec_rsize]
else:
    dump_data = open(DUMP_PATH, 'rb').read()

# Write decrypted .text into PE
exe_data[sec_rptr:sec_rptr + len(dump_data)] = dump_data

with open(OUTPUT_PATH, 'wb') as f:
    f.write(exe_data)

print(f'[OK] Patched exe saved: {OUTPUT_PATH}')
print(f'[*] Size: {os.path.getsize(OUTPUT_PATH)} bytes')
print(f'\nNow import into Ghidra:\n')
print(f'& "X:\\ghidra_12.0.1_PUBLIC\\support\\analyzeHeadless.bat" ^')
print(f'  "D:\\ghidra_projects" "FreeStylePatched" ^')
print(f'  -import "X:\\FreeStyle\\dump\\FreeStyle_patched.exe"')
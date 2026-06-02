#!/usr/bin/env python3
"""
PE Import Analysis Tool
Parses a PE32 file and extracts import directory info,
finds thunks (.text jmp stubs) + IAT entries,
locates AES S-box and 907f patterns in the binary.
"""

import sys
import os
import struct
from collections import defaultdict

try:
    import pefile
except ImportError:
    print("[!] pefile not installed. Run: py -m pip install pefile")
    sys.exit(1)

# --- Configuration ---
PE_PATH = r"d:\py\反编译\FreeStyle\apollo_dump\FreeStyle.exe"

# Functions to highlight
HIGHLIGHT_FUNCS = {
    b"WSASendTo", b"WSASend", b"WSARecvFrom", b"WSARecv",
    b"sendto", b"recvfrom",
    b"CryptEncrypt", b"CryptImportKey", b"CryptGenRandom",
    b"CryptAcquireContextA", b"CryptCreateHash", b"CryptHashData",
}

# Patterns to search in raw binary
AES_SBOX_PATTERN = bytes.fromhex("637c777b")  # first 4 bytes of AES S-box
PATTERN_907F = bytes.fromhex("907f")           # 0x90 0x7f


# --- Helpers ---
def rva_to_section_name(rva, pe):
    """Return section name that contains the given RVA, or '???' if none."""
    for section in pe.sections:
        va_start = section.VirtualAddress
        va_end = va_start + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if va_start <= rva < va_end:
            return section.Name.decode("utf-8", errors="replace").rstrip("\x00")
    return "???"


def offset_to_rva(offset, pe):
    """Convert file offset to RVA."""
    try:
        return pe.get_rva_from_offset(offset)
    except Exception:
        return None


def offset_to_section_name(offset, pe):
    """Return section name containing the given file offset."""
    for section in pe.sections:
        start = section.PointerToRawData
        end = start + section.SizeOfRawData
        if start <= offset < end:
            return section.Name.decode("utf-8", errors="replace").rstrip("\x00")
    return "???"


def format_rva(rva):
    return f"0x{rva:08X}"


def find_all_bytes(data, pattern):
    """Find all offsets of pattern in data. Returns list of file offsets."""
    offsets = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        offsets.append(pos)
        pos += 1
    return offsets


# --- Main Analysis ---
def main():
    print("=" * 80)
    print("  PE32 Import Analysis Tool")
    print("=" * 80)

    if not os.path.isfile(PE_PATH):
        print(f"[!] File not found: {PE_PATH}")
        sys.exit(1)

    pe = pefile.PE(PE_PATH)
    print(f"\n[*] Loaded: {os.path.basename(PE_PATH)}")
    print(f"    Size: {os.path.getsize(PE_PATH):,} bytes")

    # --- Section Layout ---
    print("\n" + "=" * 80)
    print("  SECTION LAYOUT")
    print("=" * 80)
    print(f"{'Name':<10} {'VirtAddr':>10} {'VirtSize':>10} {'RawAddr':>10} {'RawSize':>10}")
    print("-" * 50)
    for sec in pe.sections:
        name = sec.Name.decode("utf-8", errors="replace").rstrip("\x00")
        print(f"{name:<10} {format_rva(sec.VirtualAddress):>10} "
              f"{format_rva(sec.Misc_VirtualSize):>10} "
              f"0x{sec.PointerToRawData:08X} "
              f"0x{sec.SizeOfRawData:08X}")

    # --- Base Info ---
    print("\n" + "=" * 80)
    print("  IMAGE BASE & ENTRY POINT")
    print("=" * 80)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    entry_rva = pe.OPTIONAL_HEADER.AddressOfEntryPoint
    print(f"    ImageBase:      0x{image_base:08X}")
    print(f"    EntryPoint RVA: {format_rva(entry_rva)} "
          f"({rva_to_section_name(entry_rva, pe)})")

    # --- Import Directory ---
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        print("\n[!] No import directory found.")
        pe.close()
        sys.exit(1)

    print("\n" + "=" * 80)
    print("  IMPORT DIRECTORY ANALYSIS")
    print("=" * 80)

    # Collect all IAT RVAs for thunk scanning
    all_iat_rvas = {}  # {IAT_RVA: (dll_name, func_name_or_ordinal)}
    highlighted_entries = []

    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = entry.dll.decode("utf-8", errors="replace")
        print(f"\n--- {dll_name} ---")
        print(f"{'  Func Name':<35} {'Ord':>6} {'IAT RVA':>10} {'IAT Sec':>8}")

        for imp in entry.imports:
            func_name = imp.name.decode("utf-8", errors="replace") if imp.name else f"Ordinal_{imp.ordinal}"
            ordinal = imp.ordinal if imp.ordinal else 0
            iat_rva = imp.address
            iat_sec = rva_to_section_name(iat_rva, pe)

            line = f"  {func_name:<35} {ordinal:>6} {format_rva(iat_rva):>10} {iat_sec:>8}"
            print(line)

            all_iat_rvas[iat_rva] = (dll_name, func_name)

            # Check highlight
            if imp.name and imp.name in HIGHLIGHT_FUNCS:
                highlighted_entries.append((dll_name, func_name, 0, iat_rva, iat_sec))

    # --- Find Thunk Stubs (jmp [IAT_entry]) in executable sections ---
    print("\n" + "=" * 80)
    print("  THUNK STUBS (jmp [IAT_entry]) — .text stubs calling into IAT")
    print("=" * 80)

    thunk_found = {}  # {IAT_RVA: thunk_rva}

    # Read the raw file bytes
    with open(PE_PATH, "rb") as f:
        raw_data = f.read()

    # Scan executable sections for jmp [abs_addr] = FF 25 XX XX XX XX
    # Only scan sections with IMAGE_SCN_MEM_EXECUTE flag
    for section in pe.sections:
        characteristics = section.Characteristics
        is_executable = bool(characteristics & 0x20000000)  # IMAGE_SCN_MEM_EXECUTE
        if not is_executable:
            continue

        sec_name = section.Name.decode("utf-8", errors="replace").rstrip("\x00")
        sec_start_offset = section.PointerToRawData
        sec_size = section.SizeOfRawData
        sec_va = section.VirtualAddress

        if sec_start_offset == 0 or sec_size == 0:
            continue

        sec_data = raw_data[sec_start_offset:sec_start_offset + sec_size]

        # Scan for FF 25 pattern
        pos = 0
        while pos < len(sec_data) - 5:
            if sec_data[pos] == 0xFF and sec_data[pos + 1] == 0x25:
                # Extract the absolute address (4 bytes little-endian)
                abs_addr = struct.unpack_from("<I", sec_data, pos + 2)[0]
                # abs_addr is the virtual address (not RVA) of the IAT entry
                # Convert to RVA: IAT_RVA = abs_addr - ImageBase
                iat_rva = abs_addr - image_base

                if iat_rva in all_iat_rvas:
                    thunk_rva = sec_va + (pos - (section.PointerToRawData - section.PointerToRawData))
                    # Actually, the offset within section data is (pos + sec_start_offset - sec_start_offset) = pos
                    # thunk_rva = sec_va + (raw_offset - sec_start_offset)
                    # raw_offset = sec_start_offset + pos
                    thunk_rva = sec_va + pos
                    dll_name, func_name = all_iat_rvas[iat_rva]
                    thunk_found[iat_rva] = thunk_rva
            pos += 1

    # Print thunks
    if thunk_found:
        print(f"\nFound {len(thunk_found)} thunk stub(s) across executable sections.\n")
        print(f"{'  DLL':<20} {'Func Name':<35} {'Thunk RVA':>10} {'Thunk Sec':>10} {'IAT RVA':>10}")
        print("-" * 95)
        for iat_rva, thunk_rva in sorted(thunk_found.items()):
            dll_name, func_name = all_iat_rvas[iat_rva]
            thunk_sec = rva_to_section_name(thunk_rva, pe)
            iat_sec = rva_to_section_name(iat_rva, pe)
            print(f"  {dll_name:<20} {func_name:<35} "
                  f"{format_rva(thunk_rva):>10} {thunk_sec:>10} "
                  f"{format_rva(iat_rva):>10}")
    else:
        print("\n  (No jmp [IAT] thunk stubs found — possibly __declspec(dllimport) used directly)")

    # --- Highlighted Functions ---
    print("\n" + "=" * 80)
    print("  HIGHLIGHTED FUNCTIONS (network / crypto)")
    print("=" * 80)

    highlighted_found = []
    highlighted_not_found = []

    for dll_name, func_name, _, iat_rva, iat_sec in highlighted_entries:
        thunk_rva = thunk_found.get(iat_rva, None)
        highlighted_found.append((dll_name, func_name, thunk_rva, iat_rva, iat_sec))
        if thunk_rva:
            print(f"  [+] {dll_name}!{func_name}")
            print(f"      IAT RVA:  {format_rva(iat_rva)} ({iat_sec})")
            print(f"      Thunk:    {format_rva(thunk_rva)} ({rva_to_section_name(thunk_rva, pe)})")
        else:
            print(f"  [ ] {dll_name}!{func_name}")
            print(f"      IAT RVA:  {format_rva(iat_rva)} ({iat_sec})")
            print(f"      Thunk:    (not found in executable sections — likely dllimport)")

    # --- AES S-box pattern search ---
    print("\n" + "=" * 80)
    print("  AES S-BOX PATTERN: 63 7C 77 7B")
    print("=" * 80)

    sbox_hits = find_all_bytes(raw_data, AES_SBOX_PATTERN)
    if sbox_hits:
        print(f"  Found {len(sbox_hits)} occurrence(s):\n")
        for i, off in enumerate(sbox_hits):
            rva = offset_to_rva(off, pe)
            sec = offset_to_section_name(off, pe)
            rva_str = format_rva(rva) if rva is not None else "N/A"
            print(f"  [{i}] file offset=0x{off:08X}  RVA={rva_str}  section={sec}")
            # Show a few more bytes of context
            ctx = raw_data[off:off+16].hex(" ").upper()
            print(f"      context: {ctx}")
    else:
        print("  (not found)")

    # --- 907F pattern search ---
    print("\n" + "=" * 80)
    print("  907F PATTERN: 90 7F")
    print("=" * 80)

    pat907f_hits = find_all_bytes(raw_data, PATTERN_907F)
    if pat907f_hits:
        print(f"  Found {len(pat907f_hits)} occurrence(s):\n")
        for i, off in enumerate(pat907f_hits):
            rva = offset_to_rva(off, pe)
            sec = offset_to_section_name(off, pe)
            rva_str = format_rva(rva) if rva is not None else "N/A"
            print(f"  [{i}] file offset=0x{off:08X}  RVA={rva_str}  section={sec}")
            # Show a few more bytes of context
            ctx_start = max(0, off - 4)
            ctx_end = min(len(raw_data), off + 8)
            ctx = raw_data[ctx_start:ctx_end].hex(" ").upper()
            marker_pos = (off - ctx_start) * 3  # each byte = "XX "
            print(f"      context: {ctx}")
            print(f"               {' ' * marker_pos}^^^^")
    else:
        print("  (not found)")

    # --- Ghidra Summary ---
    print("\n" + "=" * 80)
    print("  GHIDRA SUMMARY — To find callers, search for CALL instructions")
    print("  targeting these thunk/IAT addresses:")
    print("=" * 80)

    for dll_name, func_name, thunk_rva, iat_rva, iat_sec in highlighted_found:
        if thunk_rva is not None:
            print(f"\n  {dll_name}!{func_name}:")
            print(f"    CALL → {format_rva(thunk_rva)} (jmp [IAT] thunk in "
                  f"{rva_to_section_name(thunk_rva, pe)})")
        else:
            print(f"\n  {dll_name}!{func_name}:")
            print(f"    CALL → [{format_rva(iat_rva)}] (direct IAT ref in "
                  f"{iat_sec})")

    print("\n" + "=" * 80)
    print("  ANALYSIS COMPLETE")
    print("=" * 80)

    pe.close()


if __name__ == "__main__":
    main()
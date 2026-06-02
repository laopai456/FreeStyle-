# patch_pak_bml.py — 修改 item PAK 中 BML 的 mesh 路径，实现静态→动态发型
#
# 步骤:
#   1. 解密 BML (XOR 0xFF)
#   2. 替换 mesh 路径 (MN → MT)
#   3. 重新加密
#   4. 重建 PAK
#
# 用法:
#   py patch_pak_bml.py <pak_path> <bml_name> <src_mesh_prefix> <dst_mesh_prefix>
#   py patch_pak_bml.py --revert <pak_path>
#
# 例: 把 item747.pak 中的 i50122931.bml 的 res765/i50125241 mesh 替换为 res768/i50125711
#   py patch_pak_bml.py ..\item747.pak i50122931.bml res765\i50125241 res768\i50125711

import sys, os, struct, shutil, hashlib

XOR_KEY = 0xFF

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def bml_replace_mesh(bml_text, src_prefix, dst_prefix):
    """Replace mesh paths in BML XML text"""
    new_text = bml_text
    # Replace mesh paths: <mesh>src_prefix_M*.smd</mesh> → <mesh>dst_prefix_M*.smd</mesh>
    # Also handle texture paths
    count = 0

    # Simple string replacement - works for both mesh and texture paths
    old_mesh = src_prefix.encode('utf-8')
    new_mesh = dst_prefix.encode('utf-8')

    # Work on bytes level to preserve exact formatting
    new_bytes = bml_text.replace(old_mesh, new_mesh)
    count = bml_text.count(old_mesh)
    return new_bytes, count

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py patch_pak_bml.py <pak_path> <bml_name> <src_prefix> <dst_prefix>")
        print("  py patch_pak_bml.py --revert <pak_path>")
        print()
        print("Example:")
        print("  py patch_pak_bml.py item747.pak i50122931.bml res765\\i50125241 res768\\i50125711")
        return

    # Add parent dir for imports
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    sys.path.insert(0, parent_dir)

    from repack_pak import PGFNPak

    if sys.argv[1] == '--revert':
        pak_path = sys.argv[2]
        bak_path = pak_path + '.bak'
        if not os.path.exists(bak_path):
            print(f'[!] No backup: {bak_path}')
            return
        shutil.copy2(bak_path, pak_path)
        print(f'[*] Reverted from {bak_path}')
        return

    pak_path = sys.argv[1]
    bml_name = sys.argv[2]
    src_prefix = sys.argv[3]  # e.g. res765\i50125241
    dst_prefix = sys.argv[4]  # e.g. res768\i50125711

    print(f'[*] PAK: {pak_path}')
    print(f'[*] BML: {bml_name}')
    print(f'[*] Replace: {src_prefix} → {dst_prefix}')

    # Load PAK
    pak = PGFNPak(pak_path)
    entry = pak.find_entry(bml_name)
    if not entry:
        print(f'[!] {bml_name} not found in PAK')
        print(f'    Available: {pak.list_files()[:10]}...')
        return

    print(f'[*] Found {bml_name}: offset=0x{entry["data_offset"]:X} size={entry["data_size"]}')

    # Read and decrypt
    raw = open(pak_path, 'rb').read()
    bml_encrypted = raw[entry['data_offset']:entry['data_offset'] + entry['data_size']]
    bml_decrypted = xor_crypt(bml_encrypted)

    print(f'\n[*] Original BML (decrypted):')
    print(bml_decrypted.decode('utf-8', errors='replace'))

    # Replace
    new_bml_decrypted, count = bml_replace_mesh(bml_decrypted, src_prefix, dst_prefix)
    if count == 0:
        print(f'\n[!] No matches for "{src_prefix}" in BML')
        return

    print(f'\n[*] Modified BML ({count} replacements):')
    print(new_bml_decrypted.decode('utf-8', errors='replace'))

    # Re-encrypt
    new_bml_encrypted = xor_crypt(new_bml_decrypted)

    print(f'\n[*] Size: {len(bml_encrypted)} → {len(new_bml_encrypted)}')

    # Backup original
    bak_path = pak_path + '.bak'
    if not os.path.exists(bak_path):
        shutil.copy2(pak_path, bak_path)
        print(f'[*] Backup: {bak_path}')

    # Rebuild PAK
    print(f'[*] Rebuilding PAK...')
    pak.rebuild(pak_path, replacements={bml_name: new_bml_encrypted})

    # Verify
    pak2 = PGFNPak(pak_path)
    entry2 = pak2.find_entry(bml_name)
    if entry2:
        raw2 = open(pak_path, 'rb').read()
        verify = xor_crypt(raw2[entry2['data_offset']:entry2['data_offset'] + entry2['data_size']])
        if dst_prefix.encode() in verify:
            print(f'[+] Verified: {bml_name} patched successfully')
            print(f'    New mesh prefix: {dst_prefix}')
        else:
            print(f'[!] Verification failed')
    else:
        print(f'[!] Could not find {bml_name} in rebuilt PAK')

    print(f'\n[*] Done. Revert: py patch_pak_bml.py --revert {pak_path}')

if __name__ == '__main__':
    main()

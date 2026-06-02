"""SSKF v1 正确解析 - 根据二进制实际布局"""
import struct

def hexdump(data, offset, size=32):
    return ' '.join(f'{data[offset+i]:02x}' for i in range(min(size, len(data)-offset)))

def parse_sname(data, pos):
    """SName in v1: null-term ASCII string, 4-byte aligned"""
    end = data.find(b'\x00', pos)
    if end == -1 or end - pos > 200:
        return None, pos
    name = data[pos:end].decode('ascii', errors='replace')
    next_pos = end + 1
    next_pos = (next_pos + 3) & ~3
    return name, next_pos

def parse_sskf(path, label):
    with open(path, 'rb') as f:
        data = f.read()
    
    print(f'\n{"="*70}')
    print(f'{label} ({len(data)} bytes)')
    print(f'{"="*70}')
    
    pos = 0
    magic = data[0:4].decode('ascii')
    ver = struct.unpack('<I', data[4:8])[0]
    print(f'[0x{pos:04x}] SSKF v{ver}')
    pos = 8
    
    # Mesh Name: null-term ASCII
    name, pos = parse_sname(data, pos)
    print(f'[0x{pos-1:04x}] Mesh Name: "{name}"')
    
    # Skeleton Name: "None" at offset 73
    # Find "None" string
    none_pos = data.find(b'None\x00', pos)
    if none_pos > 0:
        print(f'[0x{none_pos:04x}] Skeleton.Name = "None"')
        skel_end = none_pos + 5
        skel_end = (skel_end + 3) & ~3
    else:
        print(f'Skeleton.Name not found')
        skel_end = pos
    
    # Find bone count marker: 0x75 before first bone name
    # Scan for 0x75 + int32 + "Bip01"
    bip_pos = data.find(b'Bip01\x00', skel_end)
    if bip_pos > 0:
        # Count byte is at bip_pos - 5 (0x75 + int32)
        count_marker = data[bip_pos - 5]
        bone_count = struct.unpack('<I', data[bip_pos-4:bip_pos])[0]
        print(f'[0x{bip_pos-5:04x}] Bone Table: marker=0x{count_marker:02x} count={bone_count}')
        
        # Parse bones
        bp = bip_pos
        bone_list = []
        for i in range(bone_count):
            # Each SBone:
            #   Name(SName) + Group(SName) = 2 null-term strings
            #   ParentIndex(4) + NumChildren(4) + Depth(4) + Flags(4) = 16B
            #   Pos(12) + Quat(16) + Scale(12) = 40B
            # Total fixed after Group = 56B
            
            bname, np = parse_sname(data, bp)
            if not bname:
                print(f'  ERROR: cannot parse bone name at {bp}')
                break
            
            group, np2 = parse_sname(data, np)
            
            if np2 + 56 > len(data):
                print(f'  ERROR: past EOF at bone {i}')
                break
            
            pi = struct.unpack('<i', data[np2:np2+4])[0]
            nc = struct.unpack('<I', data[np2+4:np2+8])[0]
            dep = struct.unpack('<I', data[np2+8:np2+12])[0]
            flg = struct.unpack('<I', data[np2+12:np2+16])[0]
            
            bone_list.append((i, bname, group, pi, flg))
            
            if i < 5 or i >= bone_count - 3 or pi == -1 or bname.startswith('Dummy') or bname.startswith('Bone'):
                print(f'  [{i:3d}] "{bname}" group="{group}" parent={pi} flags=0x{flg:08X}')
            elif i == 5:
                print(f'  ... ({bone_count - 8} more bones) ...')
            
            bp = np2 + 56  # Group end + 56 fixed bytes
        
        print(f'\n  Bones parsed: {len(bone_list)}')
        print(f'  Last bone pos: 0x{bp:04x}')
        
        # After bones: Materials section
        # SMaterial: Name(SName) + BlendType(4) + bTwosided(1)+bUseAlpha(1)+Alpha(1)+Element(1) + DiffuseTex(SName)
        # = 2 SNames + 8 bytes fixed
        print(f'\n--- After bones (0x{bp:04x}) ---')
        print(f'  {hexdump(data, bp, min(48, len(data)-bp))}')
        
        # Find texture references
        print(f'\n--- Textures ---')
        for pat in [b'.dds', b'.tga', b'.png']:
            off = 0
            while True:
                off = data.find(pat, off)
                if off == -1:
                    break
                ns = data.rfind(b'\x00', max(0, off-60), off)
                if ns != -1:
                    tex = data[ns+1:off+4]
                    try:
                        tex_str = tex.decode('ascii')
                        if all(32 <= ord(c) < 127 for c in tex_str):
                            print(f'  0x{off:04x}: {tex_str}')
                    except:
                        pass
                off += 1
    else:
        print('Bip01 not found')

parse_sskf(r'D:\py\反编译\FreeStyle\cookies\smd_compare\i50125461_MT.smd', 'STATIC borrow i50125461_MT')
parse_sskf(r'D:\py\反编译\FreeStyle\cookies\smd_compare\i50125671_MT.smd', 'DYNAMIC i50125671_MT')
parse_sskf(r'D:\py\反编译\FreeStyle\cookies\smd_compare\i50125331_MT.smd', 'DYNAMIC i50125331_MT')
parse_sskf(r'D:\py\反编译\FreeStyle\cookies\smd_compare\i50125711_MT.smd', 'DYNAMIC i50125711_MT')
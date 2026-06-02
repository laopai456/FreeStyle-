"""measure_smd_sizes.py — 通过SSKF魔数直接测量SMD文件大小"""
import sys, os, struct
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'

def find_smd_sizes(pak_path, item_code):
    """在res PAK中搜索item_code相关的SMD文件，通过SSKF测量大小"""
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    target = item_code.encode()
    results = {}
    
    # 搜索所有SSKF魔数位置
    pos = 0
    sskf_list = []
    while True:
        sskf = data.find(b'SSKF', pos)
        if sskf < 0:
            break
        sskf_list.append(sskf)
        pos = sskf + 4
    
    # 对每个SSKF，检查附近500字节内是否有item_code
    for i, sskf in enumerate(sskf_list):
        search_start = max(0, sskf - 500)
        search_end = min(len(data), sskf + 10)
        region = data[search_start:search_end]
        
        if target in region:
            # 在SSKF前找文件名
            name_start = sskf
            back_bytes = data[max(0, sskf-200):sskf]
            last_null = back_bytes.rfind(b'\x00')
            if last_null >= 0:
                fname_start_in_back = last_null + 1
                fname_bytes = back_bytes[fname_start_in_back:]
            else:
                fname_bytes = back_bytes
            
            try:
                fname = fname_bytes.decode('ascii', errors='replace').strip('\x00')
            except:
                fname = ''
            
            fname = fname.split('\x00')[0].strip()
            
            if item_code not in fname or not fname.endswith('.smd'):
                continue
            
            # 计算SMD大小: 从当前SSKF到下一个SSKF
            next_sskf = sskf_list[i + 1] if i + 1 < len(sskf_list) else None
            
            # 也尝试用SMD header中的信息
            # SSKF header: 4 bytes magic + 可能有大小字段
            # 保守估计：从SSKF到下一个SSKF（或文件结尾）
            if next_sskf:
                # 但中间可能有非SMD数据（下一个SSKF可能是不同文件）
                # 用SMD header尝试更精确
                smd_end_guess = next_sskf
            else:
                smd_end_guess = len(data)
            
            smd_size_est = smd_end_guess - sskf
            
            # 尝试从SMD header读取实际大小
            # 常见SMD格式: SSKF(4) + version(4) + total_vertices(4) + ...
            # 通常SSKF后跟着一些header信息
            smd_size_actual = None
            if sskf + 8 <= len(data):
                # 尝试不同offset读取可能的size字段
                for size_offset in [4, 8, 12, 16, 20, 24]:
                    if sskf + size_offset + 4 <= len(data):
                        maybe_size = struct.unpack_from('<I', data, sskf + size_offset)[0]
                        # SMD文件通常在 10KB-500KB 范围
                        if 10000 < maybe_size < 500000:
                            smd_size_actual = maybe_size
                            break
            
            if smd_size_actual:
                results[fname] = smd_size_actual
            else:
                results[fname] = smd_size_est
    
    return results


# 同时检查: 在res758中搜索任何包含"50124"的SMD
def check_res758():
    pak_path = os.path.join(GAME, 'res758.pak')
    if not os.path.exists(pak_path):
        return
    
    print('=== res758.pak 特别检查 ===')
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    # 搜索所有50124开头的SMD文件名
    pos = 0
    found_any = False
    for prefix in [b'i50124', b'i50125']:
        pos = 0
        while True:
            idx = data.find(prefix, pos)
            if idx < 0:
                break
            # 检查附近是否为文件名
            end = data.find(b'\x00', idx)
            if end > 0:
                try:
                    fname = data[idx:end].decode('ascii', errors='replace')
                except:
                    fname = ''
                if '.smd' in fname:
                    found_any = True
                    print(f'  发现: {fname} @0x{idx:X}')
            pos = idx + len(prefix)
    
    if not found_any:
        print(f'  未找到任何50124/50125开头的SMD文件名')
    
    # 搜索"24241"
    print(f'\n  搜索"24241"在所有字符串中:')
    pos = 0
    count = 0
    while True:
        idx = data.find(b'24241', pos)
        if idx < 0:
            break
        # 显示上下文
        ctx = data[max(0,idx-10):idx+30]
        try:
            ctx_str = ctx.decode('ascii', errors='replace')
        except:
            ctx_str = repr(ctx)
        print(f'    @0x{idx:X}: ...{ctx_str}...')
        pos = idx + 1
        count += 1
        if count > 20:
            print(f'    ... (截断)')
            break


# 分析目标
targets = {
    '50119961': 'res723.pak',
    '50120651': 'res727.pak',
    '50124241': 'res758.pak',
    '50125651': 'res767.pak',
    '50125711': 'res768.pak',
}

print('=== SMD文件大小测量 (通过SSKF魔数) ===')
for ic, pak_name in targets.items():
    pak_path = os.path.join(GAME, pak_name)
    if not os.path.exists(pak_path):
        continue
    fsize = os.path.getsize(pak_path)
    print(f'\n{ic} ({pak_name}, {fsize/1024/1024:.1f}MB):')
    smds = find_smd_sizes(pak_path, ic)
    for name, sz in sorted(smds.items()):
        variant = name.replace('.smd','').split('_')
        var_suffix = '_'.join(variant[1:]) if len(variant) > 1 else '(base)'
        print(f'  {name}: {sz}B ({sz/1024:.1f}KB) [{var_suffix}]')

print()
check_res758()
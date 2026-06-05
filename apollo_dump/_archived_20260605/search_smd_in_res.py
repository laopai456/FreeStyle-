"""search_smd_in_res.py — 通过已知文件名搜索res PAK中的SMD"""
import sys, os, struct
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\py\反编译\FreeStyle')
from repack_pak import PGFNPak
import time

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'

# 只分析关键的几个res PAK
targets = [
    ('res723.pak', ['i50119961_MT.smd','i50119961_MN.smd','i50119961_MF.smd',
                     'i50119961_FT.smd','i50119961_FN.smd','i50119961_FSC.smd']),
    ('res727.pak', ['i50120651_MT.smd','i50120651_MN.smd','i50120651_MF.smd',
                     'i50120651_FT.smd','i50120651_FN.smd','i50120651_FSC.smd']),
    ('res758.pak', ['i50124241_MT.smd','i50124241_MS.smd','i50124241_MN.smd','i50124241_MF.smd',
                     'i50124241_FT.smd','i50124241_FS.smd','i50124241_FN.smd','i50124241_FSC.smd']),
    ('res767.pak', ['i50125651_M.smd','i50125651_MS.smd','i50125651_F.smd','i50125651_FS.smd','i50125651_Fsc.smd']),
    ('res768.pak', ['i50125711_MT.smd','i50125711_MS.smd','i50125711_MN.smd','i50125711_MF.smd',
                     'i50125711_FT.smd','i50125711_FS.smd','i50125711_FN.smd','i50125711_FSC.smd']),
]

for pak_name, smd_names in targets:
    pak_path = os.path.join(GAME, pak_name)
    if not os.path.exists(pak_path):
        print(f'{pak_name}: 不存在')
        continue
    
    fsize = os.path.getsize(pak_path)
    print(f'\n=== {pak_name} ({fsize/1024/1024:.1f}MB) ===')
    
    t0 = time.time()
    with open(pak_path, 'rb') as f:
        data = f.read()
    
    # 方法1: 搜索每个SMD文件名
    for sname in smd_names:
        idx = data.find(sname.encode('ascii'))
        if idx >= 0:
            print(f'  [文件名] {sname} found @0x{idx:X}')
        else:
            print(f'  [文件名] {sname} NOT found')
    
    # 方法2: 用PGFNPak解析（只对<80MB的）
    if fsize < 80 * 1024 * 1024:
        print(f'  [PGFNPak] 解析中...')
        try:
            rpak = PGFNPak(pak_path)
            for prefix in set(n.split('_')[0] for n in smd_names):
                items = [(e['name'], e['data_size']) for e in rpak.entries 
                         if prefix in e['name'] and e['name'].endswith('.smd')]
                for name, sz in items:
                    print(f'  [PGFNPak] {name} ({sz}B, {sz/1024:.1f}KB)')
        except Exception as ex:
            print(f'  [PGFNPak] Error: {ex}')
        print(f'  耗时: {time.time()-t0:.1f}s')
    else:
        print(f'  [PGFNPak] 跳过 (文件>80MB)')
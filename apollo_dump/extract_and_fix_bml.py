"""extract_and_fix_bml.py — 提取i50125711.png纹理，修复BML结构"""
import sys, os, struct, shutil
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF
OUT_DIR = os.path.join(GAME, 'Resource', 'item')

def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

# ===== 1. 从res768.pak手动提取 i50125711.png =====
print('=== 1. 从res768.pak提取 i50125711.png ===')
res768_path = os.path.join(GAME, 'res768.pak')
with open(res768_path, 'rb') as f:
    rdata = f.read()

# 找到i50125711.png文件名位置
name_idx = rdata.find(b'i50125711.png')
print(f'  文件名 @0x{name_idx:X}')

# 从文件名往前找entry header，然后找PNG数据
# 在PAK中，文件名前面是entry header (20字节: 4+4+4+4+4)
# 但不同格式可能有变。尝试在文件名附近找\x89PNG魔数
png_magic_pos = name_idx
# 往前找20字节看entry header
if name_idx >= 20:
    entry_hdr_start = name_idx - 20
    # 尝试读取header
    d0 = struct.unpack_from('<I', rdata, entry_hdr_start)[0]
    d1 = struct.unpack_from('<I', rdata, entry_hdr_start + 4)[0]
    d2 = struct.unpack_from('<I', rdata, entry_hdr_start + 8)[0]
    d3 = struct.unpack_from('<I', rdata, entry_hdr_start + 12)[0]
    print(f'  Header候选: d0={d0} d1={d1} d2={d2} d3={d3}')

# 从文件名往前搜索PNG魔数
png_start = rdata.find(b'\x89PNG', max(0, name_idx - 1000))
if png_start >= 0:
    print(f'  PNG魔数 @0x{png_start:X} (距文件名 {png_start - name_idx} bytes)')
    
    # 找PNG结束(IEND + 4字节CRC)
    iend = rdata.find(b'IEND', png_start)
    if iend > 0:
        png_size = iend + 8 - png_start
        png_data = rdata[png_start:png_start + png_size]
        print(f'  PNG大小: {png_size}B ({png_size/1024:.1f}KB)')
        
        # 验证PNG有效性
        if png_data[:4] == b'\x89PNG' and png_data[-4:] == b'IEND':
            # 保存
            png_out = os.path.join(GAME, 'Resource', 'item', 'i50125711.png')
            with open(png_out, 'wb') as f:
                f.write(png_data)
            print(f'  [+] 已提取: {png_out}')
        else:
            print(f'  [!] PNG验证失败!')
    else:
        print(f'  [!] 未找到IEND!')
else:
    print(f'  [!] 未找到PNG魔数!')

# 也尝试直接向后搜索（文件名后可能有PNG数据）
# 在PAK中，entry通常这么布局: [header(20)][name\0]...[alignment]...[PNG data]
# 文件名在name_idx处结束于\0
name_end = rdata.find(b'\x00', name_idx)
if name_end > 0:
    print(f'  文件名结束于 @0x{name_end:X}')
    # 对齐后应该是PNG数据
    data_start = name_end + 1
    # 对齐到4字节
    pad = (4 - (data_start % 4)) % 4
    data_start += pad
    fb = rdata[data_start:data_start+4]
    print(f'  数据区域 @0x{data_start:X}, 前4字节: {fb.hex()}')
    if fb == b'\x89PNG':
        iend = rdata.find(b'IEND', data_start)
        if iend > 0:
            png_size = iend + 8 - data_start
            png_data = rdata[data_start:data_start + png_size]
            png_out = os.path.join(GAME, 'Resource', 'item', 'i50125711.png')
            with open(png_out, 'wb') as f:
                f.write(png_data)
            print(f'  [+] 方法2提取成功: {png_out} ({png_size}B)')

# ===== 2. 修复BML结构 =====
print('\n=== 2. 修复BML结构 ===')

# 原始BML的问题:
# - char[1]有object+object type="2" (MT+MS → 都换为fn)
# - char[4]有object+object type="2" (FT+FS → 都换为fn)
# - 纹理引用i50125701_f.png应改为i50125711.png
# 
# 策略: 保持简洁结构，char[1]/[4]只保留1个object (因为只有1个fn.smd可用)

fixed_bml_xml = """<?xml version="1.0"?>
<root>
   <channel>1</channel>
   <character type="1">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
   <character type="2">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
   <character type="3">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
   <character type="4">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
   <character type="5">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
   <character type="6">
      <object>
         <type>normal</type>
         <mesh>res768\i50125711_fn.smd</mesh>
         <texture>res768\i50125711.png</texture>
      </object>
   </character>
</root>"""

print('  修复内容:')
print('  1. 移除char[1]和char[4]中重复的<object type="2"> (MS/FS变体)')
print('  2. 纹理从 i50125701_f.png 改为 i50125711.png')
print('  3. 所有角色统一使用 i50125711_fn.smd')

# ===== 3. 部署修复后的BML =====
print('\n=== 3. 部署修复后的BML ===')

bml_bytes = fixed_bml_xml.encode('utf-8')
encoded = xor_crypt(bml_bytes)

out_path = os.path.join(OUT_DIR, 'i50125711.bml')

# 备份当前版本
if os.path.exists(out_path):
    bak = out_path + '.bak2'
    shutil.copy2(out_path, bak)
    print(f'  已备份: {bak}')

with open(out_path, 'wb') as f:
    f.write(encoded)
print(f'  [+] 已部署: {out_path} ({len(encoded)}B)')

# XML参考
xml_out = os.path.join(OUT_DIR, 'i50125711.xml')
with open(xml_out, 'w', encoding='utf-8') as f:
    f.write(fixed_bml_xml)
print(f'  [+] XML参考: {xml_out}')

# ===== 4. 验证 =====
print('\n=== 4. 验证 ===')
with open(out_path, 'rb') as f:
    verify = xor_crypt(f.read())
vtext = verify.decode('utf-8')

errors = []
warnings = []

# 检查不应该存在的
if 'i50125711_MT.smd' in vtext: errors.append('仍有_MT引用!')
if 'i50125711_MS.smd' in vtext: errors.append('仍有_MS引用!')
if 'i50125711_FT.smd' in vtext: errors.append('仍有_FT引用!')
if 'i50125711_FS.smd' in vtext: errors.append('仍有_FS引用!')
if 'i50125711_MN.smd' in vtext: errors.append('仍有_MN引用!')
if 'i50125711_MF.smd' in vtext: errors.append('仍有_MF引用!')
if 'i50125711_FSC.smd' in vtext: errors.append('仍有_FSC引用!')
if 'i50125701_f.png' in vtext: errors.append('仍引用旧纹理i50125701_f.png!')

# 检查应该存在的
if 'i50125711_fn.smd' not in vtext: errors.append('缺少fn.smd引用!')
if 'i50125711.png' not in vtext: errors.append('缺少i50125711.png纹理引用!')
if 'character type="1"' not in vtext: errors.append('缺少char[1]!')
if 'character type="6"' not in vtext: errors.append('缺少char[6]!')

# 检查object type="2"
if 'object type="2"' in vtext: errors.append('仍有残留的object type="2"!')

if errors:
    print(f'  [!] 验证失败 ({len(errors)}个错误):')
    for e in errors:
        print(f'    - {e}')
else:
    print(f'  [OK] 验证通过，无错误!')

# 检查资源
print(f'\n  资源检查:')
res_files = {
    'SMD': os.path.join(GAME, 'res768.pak'),
    'PNG': os.path.join(GAME, 'Resource', 'item', 'i50125711.png'),
    'BML': out_path,
}
for label, fp in res_files.items():
    if os.path.exists(fp):
        sz = os.path.getsize(fp)
        print(f'    [{label}] OK: {fp} ({sz}B)')
    else:
        print(f'    [{label}] MISSING: {fp}')

print(f'\n=== 当前BML内容 ===')
print(fixed_bml_xml)
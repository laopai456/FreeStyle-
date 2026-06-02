"""extract_png_fix.py — 修正PNG提取偏移"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'C:\Program Files (x86)\T2CN\街头篮球'
res768 = os.path.join(GAME, 'res768.pak')

with open(res768, 'rb') as f:
    data = f.read()

name_idx = data.find(b'i50125711.png')
print(f'文件名 @0x{name_idx:X}')

# 查看周围字节
print(f'\n文件名周围 (原始hex):')
for i in range(max(0, name_idx-24), min(len(data), name_idx+50)):
    if i == name_idx:
        print(f'  @0x{i:06X}: {data[i]:02X}  <-- 文件名开始')
    elif i % 16 == 0:
        pass
    elif i % 8 == 0:
        pass

# 连续显示
ctx = data[max(0,name_idx-20):name_idx+30]
print(f'\n20字节前: {ctx[:20].hex()}')
print(f'文件名: {ctx[20:34]}')
print(f'30字节后: {ctx[34:].hex()}')

# 关键：找\x89PNG魔数
# \x89PNG\r\n\x1a\n = 89 50 4E 47 0D 0A 1A 0A
# 从文件名结束位置开始找
name_len = len('i50125711.png')
for offset in range(name_idx + name_len - 5, min(len(data), name_idx + name_len + 20)):
    fb8 = data[offset:offset+8]
    if fb8[:4] == b'\x89PNG' or fb8[1:5] == b'\x89PNG' or fb8 == b'\x89PNG\r\n\x1a\n':
        print(f'\n[+] 找到PNG魔数 @0x{offset:X}: {fb8.hex()}')
        
        # 从PNG魔数到IEND
        png_start = offset
        iend = data.find(b'IEND', png_start)
        if iend > 0:
            png_size = iend + 8 - png_start
            png_data = data[png_start:png_start + png_size]
            
            out_path = os.path.join(GAME, 'Resource', 'item', 'i50125711.png')
            with open(out_path, 'wb') as f:
                f.write(png_data)
            print(f'[+] 提取成功! {out_path} ({png_size}B, {png_size/1024:.1f}KB)')
            
            # 验证
            if png_data[:8] == b'\x89PNG\r\n\x1a\n' and png_data[-12:-8] == b'IEND':
                print(f'[+] PNG格式验证通过!')
            break

# 如果上面的没找到，用更宽泛的搜索
else:
    print('\n[搜索] 在文件名附近100字节内找PNG魔数...')
    for offset in range(name_idx + name_len, min(len(data), name_idx + name_len + 100)):
        if data[offset:offset+2] == b'PN' and data[offset+2:offset+3] == b'G':
            print(f'  "PNG" @0x{offset:X}: {data[offset-2:offset+10].hex()}')
        if data[offset] == 0x89 and data[offset+1:offset+4] == b'PNG':
            print(f'  \\x89PNG @0x{offset:X}!')
            png_start = offset
            iend = data.find(b'IEND', png_start)
            if iend > 0:
                png_size = iend + 8 - png_start
                png_data = data[png_start:png_start + png_size]
                out_path = os.path.join(GAME, 'Resource', 'item', 'i50125711.png')
                with open(out_path, 'wb') as f:
                    f.write(png_data)
                print(f'  [+] 提取成功! {out_path} ({png_size}B)')
            break
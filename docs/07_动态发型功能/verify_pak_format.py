import struct
from pathlib import Path

def parse_pak(pak_path):
    """解析pak文件结构"""
    with open(pak_path, 'rb') as f:
        # 读取文件数量
        file_count = struct.unpack('<I', f.read(4))[0]
        print(f'文件数量: {file_count}\n')

        # 读取索引表
        file_entries = []
        for i in range(file_count):
            # 读取文件名（直到遇到\0）
            name_bytes = bytearray()
            while True:
                byte = f.read(1)
                if byte == b'\x00':
                    break
                name_bytes.extend(byte)

            # 读取文件大小
            size = struct.unpack('<I', f.read(4))[0]

            # 尝试解码文件名
            try:
                name = name_bytes.decode('gbk')
            except:
                name = name_bytes.decode('latin1', errors='ignore')

            file_entries.append({'name': name, 'size': size})

            if i < 5:  # 只显示前5个
                print(f'{i+1}. {name} - {size} bytes')

        print(f'...\n共 {file_count} 个文件\n')

        # 记录索引表结束位置
        index_end = f.tell()
        print(f'索引表结束位置: offset {index_end}')

        # 计算文件数据总大小
        total_data_size = sum(entry['size'] for entry in file_entries)
        print(f'文件数据总大小: {total_data_size} bytes')

        # 验证文件总大小
        pak_size = Path(pak_path).stat().st_size
        print(f'pak文件总大小: {pak_size} bytes')
        print(f'计算总大小(索引+数据): {index_end + total_data_size} bytes')

        if pak_size == index_end + total_data_size:
            print('✓ 格式验证通过')
        else:
            print(f'✗ 格式验证失败，相差 {pak_size - (index_end + total_data_size)} bytes')

# 解析原始pak
print('=== 原始 item764.pak ===')
original_pak = r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764.pak.backup'
if not Path(original_pak).exists():
    # 如果没有备份，用游戏目录的
    original_pak = r'C:\Users\w\Desktop\fs\item764.pak'
parse_pak(original_pak)

print('\n' + '='*50 + '\n')

# 解析新生成的pak
print('=== 新生成的 item764.pak ===')
new_pak = r'D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764.pak'
parse_pak(new_pak)

"""
BML文件解码器 - 测试脚本
直接解码指定的BML文件
"""

import os

def decode_bml(bml_path, output_xml_path=None):
    """解码BML文件为XML文件"""
    if output_xml_path is None:
        base_name = os.path.splitext(bml_path)[0]
        output_xml_path = base_name + '.xml'

    # 读取BML文件
    with open(bml_path, 'rb') as f:
        bml_data = f.read()

    # 解码：每个字节与0xFF进行XOR运算
    decoded_data = bytearray(len(bml_data))
    for i, byte in enumerate(bml_data):
        decoded_data[i] = byte ^ 0xFF

    # 写入XML文件
    with open(output_xml_path, 'wb') as f:
        f.write(decoded_data)

    print(f'已解码: {bml_path}')
    print(f'输出到: {output_xml_path}')
    print(f'文件大小: {len(bml_data)} bytes')

    return output_xml_path

# 测试解码动态发型BML文件
bml_file = r"D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak\i50125031.bml"
decode_bml(bml_file)

# 测试解码静态发型BML文件
bml_file2 = r"D:\py\反编译\FS服装搭配专家v5.3.6\bin\Debug\cookies\item764_pak\i50125001.bml"
decode_bml(bml_file2)

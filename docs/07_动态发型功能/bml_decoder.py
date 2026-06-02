"""
BML文件解码器
BML文件是简单的XOR加密的XML文件，使用0xFF作为密钥
"""

def decode_bml(bml_path, output_xml_path=None):
    """
    解码BML文件为XML文件

    Args:
        bml_path: BML文件路径
        output_xml_path: 输出XML文件路径（可选，默认为原文件名.xml）

    Returns:
        output_xml_path: 输出文件路径
    """
    # 如果没有指定输出路径，使用原文件名.xml
    if output_xml_path is None:
        import os
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


def encode_xml(xml_path, output_bml_path=None):
    """
    编码XML文件为BML文件

    Args:
        xml_path: XML文件路径
        output_bml_path: 输出BML文件路径（可选，默认为原文件名.bml）

    Returns:
        output_bml_path: 输出文件路径
    """
    # 如果没有指定输出路径，使用原文件名.bml
    if output_bml_path is None:
        import os
        base_name = os.path.splitext(xml_path)[0]
        output_bml_path = base_name + '.bml'

    # 读取XML文件
    with open(xml_path, 'rb') as f:
        xml_data = f.read()

    # 编码：每个字节与0xFF进行XOR运算
    encoded_data = bytearray(len(xml_data))
    for i, byte in enumerate(xml_data):
        encoded_data[i] = byte ^ 0xFF

    # 写入BML文件
    with open(output_bml_path, 'wb') as f:
        f.write(encoded_data)

    print(f'已编码: {xml_path}')
    print(f'输出到: {output_bml_path}')
    print(f'文件大小: {len(xml_data)} bytes')

    return output_bml_path


if __name__ == '__main__':
    import sys
    import os

    if len(sys.argv) < 2:
        print('BML文件编解码器')
        print('')
        print('用法:')
        print('  解码: python bml_decoder.py <bml文件>')
        print('  编码: python bml_decoder.py <xml文件> --encode')
        print('')
        print('示例:')
        print('  python bml_decoder.py i50125031.bml')
        print('  python bml_decoder.py i50125031.xml --encode')
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f'错误: 文件不存在: {input_file}')
        sys.exit(1)

    # 判断是编码还是解码
    if len(sys.argv) > 2 and sys.argv[2] == '--encode':
        # 编码
        encode_xml(input_file)
    else:
        # 解码
        decode_bml(input_file)

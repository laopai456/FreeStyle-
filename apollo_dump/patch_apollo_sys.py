# patch_apollo_sys.py
# 层次 4：静态 Patch Apollo.sys 的 DR 清零函数
#
# 步骤：
#   1. 解压 UPX（如果压缩）
#   2. 找到 DR_clear_area 的文件偏移
#   3. Patch 为 RET (0xC3)
#   4. 备份原文件，写入修改后的文件
#
# 前提：
#   - bcdedit /set testsigning on（允许未签名驱动）
#   - 管理员权限

import sys
import os
import struct
import shutil

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APOLLO_SYS = os.path.join(SCRIPT_DIR, 'Apollo.sys')
APOLLO_BACKUP = os.path.join(SCRIPT_DIR, 'Apollo.sys.original')

# 目标函数信息
DR_CLEAR_VA = 0x140001986
BASE_ADDR = 0x140000000
DR_CLEAR_RVA = DR_CLEAR_VA - BASE_ADDR  # 0x1986

def analyze_pe(filepath):
    """分析 PE 文件结构"""
    with open(filepath, 'rb') as f:
        # DOS header
        dos = f.read(64)
        e_lfanew = struct.unpack_from('<I', dos, 60)[0]

        # PE header
        f.seek(e_lfanew)
        pe_sig = f.read(4)
        if pe_sig != b'PE\x00\x00':
            print(f'无效 PE 文件')
            return None

        # COFF header
        machine = struct.unpack('<H', f.read(2))[0]
        num_sections = struct.unpack('<H', f.read(2))[0]
        f.read(12)  # 跳过时间戳等
        opt_header_size = struct.unpack('<H', f.read(2))[0]
        f.read(2)  # characteristics

        # Optional header (PE32+)
        magic = struct.unpack('<H', f.read(2))[0]
        is_pe32_plus = (magic == 0x20b)

        print(f'PE 类型: {"PE32+ (64位)" if is_pe32_plus else "PE32 (32位)"}')
        print(f'节数量: {num_sections}')

        # 跳过剩余 optional header
        f.seek(e_lfanew + 24 + opt_header_size)

        # 节表
        sections = []
        for i in range(num_sections):
            section_data = f.read(40)
            name = section_data[:8].rstrip(b'\x00').decode('ascii', errors='ignore')
            virt_size = struct.unpack_from('<I', section_data, 8)[0]
            virt_addr = struct.unpack_from('<I', section_data, 12)[0]
            raw_size = struct.unpack_from('<I', section_data, 16)[0]
            raw_ptr = struct.unpack_from('<I', section_data, 20)[0]

            sections.append({
                'name': name,
                'virt_size': virt_size,
                'virt_addr': virt_addr,
                'raw_size': raw_size,
                'raw_ptr': raw_ptr,
            })

            print(f'  节 {name}: VA=0x{virt_addr:x} Raw=0x{raw_ptr:x} Size={raw_size}')

        return sections

def rva_to_offset(rva, sections):
    """将 RVA 转换为文件偏移"""
    for s in sections:
        if s['virt_addr'] <= rva < s['virt_addr'] + s['virt_size']:
            offset = rva - s['virt_addr'] + s['raw_ptr']
            return offset
    return None

def check_upx(sections):
    """检查是否 UPX 压缩"""
    for s in sections:
        if 'UPX' in s['name']:
            return True
    return False

def find_dr_clear_pattern(data, offset):
    """在指定偏移附近查找 DR_clear_area 的特征"""
    # DR_clear_area 是个 wrapper:
    #   call FUN_140063780
    #   ret
    # 特征: E8 xx xx xx xx C3

    if offset + 10 > len(data):
        return False

    bytes_at = data[offset:offset+10]
    print(f'  偏移 0x{offset:x} 处的字节: {bytes_at.hex()}')

    # 检查是否是 wrapper 函数
    # 通常以 push r13 (41 55) 或 sub rsp 开始
    if bytes_at[0:2] == b'\x41\x55':  # push r13
        print(f'  发现 push r13 开头')
        return True
    elif bytes_at[0:4] == b'\x48\x83\xec':  # sub rsp, xx
        print(f'  发现 sub rsp 开头')
        return True

    return False

def patch_file(filepath, offset, new_bytes):
    """在指定偏移写入新字节"""
    with open(filepath, 'r+b') as f:
        f.seek(offset)
        old = f.read(len(new_bytes))
        f.seek(offset)
        f.write(new_bytes)
        return old

def main():
    print('=== Apollo.sys Patch 分析 ===')
    print(f'文件: {APOLLO_SYS}')
    print(f'目标: DR_clear_area @ VA 0x{DR_CLEAR_VA:x}')
    print(f'RVA: 0x{DR_CLEAR_RVA:x}')
    print('')

    if not os.path.exists(APOLLO_SYS):
        print('Apollo.sys 不存在')
        return

    # 分析 PE
    print('分析 PE 结构...')
    sections = analyze_pe(APOLLO_SYS)

    if not sections:
        return

    # 检查 UPX
    is_upx = check_upx(sections)
    print(f'\nUPX 压缩: {"是 ⚠️" if is_upx else "否"}')

    # 计算 RVA 对应的文件偏移
    print(f'\n计算文件偏移...')
    offset = rva_to_offset(DR_CLEAR_RVA, sections)

    if offset is None:
        print('无法计算偏移，可能因为 UPX 压缩')
        print('需要先解压: upx -d Apollo.sys')
        return

    print(f'RVA 0x{DR_CLEAR_RVA:x} → 文件偏移 0x{offset:x}')

    # 读取当前字节
    with open(APOLLO_SYS, 'rb') as f:
        data = f.read()

    print(f'\n当前字节:')
    find_dr_clear_pattern(data, offset)

    # 如果是 UPX 压缩，警告
    if is_upx:
        print('\n⚠️ 文件被 UPX 压缩，静态 patch 可能无效')
        print('建议:')
        print('  1. 安装 UPX: winget install upx')
        print('  2. 解压: upx -d Apollo.sys')
        print('  3. 重新运行此脚本')
        print('')
        resp = input('是否继续 patch（可能无效）？(y/n): ')
        if resp.lower() != 'y':
            return

    # 备份
    print(f'\n备份原文件到 {APOLLO_BACKUP}...')
    shutil.copy2(APOLLO_SYS, APOLLO_BACKUP)

    # Patch 方案
    print('\nPatch 方案:')
    print('  1. NOP: 90 90 (推荐，保持函数结构)')
    print('  2. RET: C3 (直接返回，最激进)')
    print('')

    choice = input('选择方案 (1/2): ').strip()

    if choice == '1':
        new_bytes = b'\x90\x90'  # NOP NOP
    elif choice == '2':
        new_bytes = b'\xC3'  # RET
    else:
        print('无效选择')
        return

    # 执行 patch
    print(f'\nPatch 偏移 0x{offset:x}...')
    old_bytes = patch_file(APOLLO_SYS, offset, new_bytes)
    print(f'原字节: {old_bytes.hex()}')
    print(f'新字节: {new_bytes.hex()}')

    # 验证
    with open(APOLLO_SYS, 'rb') as f:
        f.seek(offset)
        verify = f.read(len(new_bytes))

    if verify == new_bytes:
        print('\n✅ Patch 成功')
        print('\n下一步:')
        print('  1. 开测试模式: bcdedit /set testsigning on')
        print('  2. 重启系统')
        print('  3. 替换系统驱动:')
        print('     takeown /f C:\\Windows\\System32\\drivers\\Apollo.sys')
        print('     icacls C:\\Windows\\System32\\drivers\\Apollo.sys /grant Administrators:F')
        print('     copy /Y Apollo.sys C:\\Windows\\System32\\drivers\\Apollo.sys')
        print('  4. 重启游戏，测试硬件断点')
    else:
        print('\n❌ Patch 失败')

if __name__ == '__main__':
    main()
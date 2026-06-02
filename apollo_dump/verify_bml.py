"""
verify_bml.py — 验证部署的 BML 内容
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

BML_PATH = r'C:\Program Files (x86)\T2CN\街头篮球\Resource\item768\i50125711.bml'
XOR_KEY = 0xFF

def main():
    try:
        with open(BML_PATH, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f'[!] 文件不存在: {BML_PATH}')
        return

    dec = bytes(b ^ XOR_KEY for b in data)
    text = dec.decode('utf-8')

    print('=== 部署的 BML 内容 ===')
    print(text)
    print()
    print('=== 引用的资源 ===')

    import re
    smd_refs = re.findall(r'res768\\([^"]+\.smd)', text)
    png_refs = re.findall(r'res768\\([^"]+\.png)', text)

    print(f'SMD 引用 ({len(smd_refs)} 个):')
    for s in smd_refs:
        print(f'  - {s}')

    print(f'\nPNG 引用 ({len(png_refs)} 个):')
    for p in png_refs:
        print(f'  - {p}')

if __name__ == '__main__':
    main()
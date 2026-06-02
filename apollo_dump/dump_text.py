# dump_text.py — 用 Pymem (ReadProcessMemory) dump 解密后的 .text 段
#
# 用法:
#   1. 管理员: sc.exe stop ApolloProtect
#   2. 启动游戏，等进到大厅
#   3. py dump_text.py
#
# Frida 用于枚举段信息，Pymem 用于读内存（已知不被 Apollo 拦截）

import frida
import pymem
import sys
import os
import struct
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DUMP_DIR = os.path.join(SCRIPT_DIR, '..', 'dump')
DUMP_FILE = os.path.join(DUMP_DIR, 'dump_text.bin')
SECTION_FILE = os.path.join(DUMP_DIR, 'dump_sections.txt')

JS_CODE = r"""
'use strict';
var fsMod = Process.getModuleByName('FreeStyle.exe');
var base = fsMod.base;
var sections = [];
fsMod.enumerateSections().forEach(function(s) {
    sections.push({name: s.name, base: s.address.toString(), size: s.size, rva: s.address.sub(base).toInt32()});
});
rpc.exports = {
    sections: function() { return sections; },
    base: function() { return base.toString(); }
};
"""


def find_pid():
    try:
        result = subprocess.run(
            ['tasklist.exe', '/fi', 'IMAGENAME eq FreeStyle.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'FreeStyle.exe' in line:
                return int(line.split(',')[1].strip('"'))
    except Exception as e:
        print(f'[!] tasklist failed: {e}')
    return None


def main():
    pid = None
    args = sys.argv[1:]
    if '--pid' in args:
        idx = args.index('--pid')
        if idx + 1 < len(args):
            pid = int(args[idx + 1])

    if pid is None:
        print('[*] Finding FreeStyle.exe...')
        pid = find_pid()
        if pid is None:
            print('[!] FreeStyle.exe not found.')
            sys.exit(1)
    print(f'[+] PID: {pid}')

    # Frida: 枚举段信息
    print('[*] Frida: getting section info...')
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)
    script.load()
    api = script.exports_sync
    sections = api.sections()
    base_addr = int(api.base(), 16)
    session.detach()

    text_section = next((s for s in sections if s['name'] == '.text'), None)
    if not text_section:
        print('[!] .text section not found')
        sys.exit(1)

    os.makedirs(DUMP_DIR, exist_ok=True)

    with open(SECTION_FILE, 'w') as f:
        f.write(f"Base: 0x{base_addr:X}\n\n")
        f.write(f"{'Name':<12} {'Address':<16} {'Size':>12} {'RVA':>10}\n")
        f.write('-' * 52 + '\n')
        for s in sections:
            f.write(f"{s['name']:<12} {s['base']:<16} {s['size']:>12} {s['rva']:>#10x}\n")
    print(f'[*] Sections -> {SECTION_FILE}')

    text_base = int(text_section['base'], 16)
    total = text_section['size']
    print(f'[*] .text: 0x{text_base:X} {total/1024/1024:.1f}MB')

    # Pymem: 读内存
    print('[*] Pymem: reading .text...')
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    CHUNK = 4 * 1024 * 1024
    with open(DUMP_FILE, 'wb') as f:
        offset = 0
        while offset < total:
            addr = text_base + offset
            read_size = min(CHUNK, total - offset)
            try:
                data = pm.read_bytes(addr, read_size)
                f.write(data)
            except Exception as e:
                print(f'  [WARN] Read failed at 0x{offset:X} (0x{addr:X}): {e}')
                f.write(b'\x00' * read_size)
            offset += read_size
            pct = offset * 100 // total
            if pct % 10 == 0:
                print(f'  [{pct:3d}%] {offset/1024/1024:.1f}/{total/1024/1024:.1f} MB')

    pm.close_process()

    actual = os.path.getsize(DUMP_FILE)
    # 检查是否全零
    with open(DUMP_FILE, 'rb') as f:
        sample = f.read(4096)
        nonzero = sum(1 for b in sample if b != 0)

    print(f'[OK] {actual/1024/1024:.1f} MB -> {DUMP_FILE}')
    print(f'[*] First 4KB: {nonzero}/4096 non-zero bytes')

    if nonzero == 0:
        print('[WARN] All zeros! Memory may still be encrypted or unreadable.')
    else:
        print('[OK] Data looks valid (non-zero content detected)')


if __name__ == '__main__':
    main()

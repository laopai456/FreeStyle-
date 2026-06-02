# _check_quick.py
import sys, os
sys.path.insert(0, r'D:\py\反编译\FreeStyle')
sys.stdout.reconfigure(encoding='utf-8')
from repack_pak import PGFNPak

GAME = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')

# Check specific item PAKs for the working hairstyle codes
for code, pak_nums in [(50125711, [768]), (50122451, [742, 743]), (50120651, [727])]:
    print(f'\n=== {code} ===')
    for pn in pak_nums:
        ipath = os.path.join(GAME, f'item{pn}.pak')
        if os.path.exists(ipath):
            ipak = PGFNPak(ipath)
            for e in ipak.entries:
                if str(code) in e['name']:
                    print(f'  item{pn}.pak: {e}')
        
        rpath = os.path.join(GAME, f'res{pn}.pak')
        if os.path.exists(rpath):
            rpak = PGFNPak(rpath)
            for e in rpak.entries:
                if str(code) in e['name']:
                    print(f'  res{pn}.pak: {e["name"]} ({e["data_size"]}B)')
            # Also check for PNG
            for e in rpak.entries:
                if str(code) in e['name'] and e['name'].endswith('.png'):
                    print(f'  res{pn}.pak PNG: {e}')

# deploy_resources.py
# Deploy complete 50125711 resources to game directory
import sys
import os
import shutil

sys.stdout.reconfigure(encoding='utf-8')

SRC_DIR = 'C:\\Users\\w\\Desktop\\res768_pak'
GAME_DIR = 'C:\\Program Files (x86)\\T2CN\\街头篮球'
DST_DIR = os.path.join(GAME_DIR, 'Resource', 'res768')

RESOURCES = [
    'i50125711.png',
    'i50125711_fn.smd',
    'i50125711_ft.smd',
    'i50125711_fs.smd',
    'i50125711_fsc.smd',
    'i50125711_mt.smd',
    'i50125711_ms.smd',
    'i50125711_mn.smd',
    'i50125711_mf.smd',
]

def main():
    print('=== Deploy 50125711 Resources ===')
    print('Source:', SRC_DIR)
    print('Target:', DST_DIR)
    print()

    if not os.path.isdir(SRC_DIR):
        print('[!] Source not found:', SRC_DIR)
        return

    os.makedirs(DST_DIR, exist_ok=True)
    print('[+] Target dir created')

    deployed = 0
    missing = []

    for res in RESOURCES:
        src_path = os.path.join(SRC_DIR, res)
        dst_path = os.path.join(DST_DIR, res)

        if not os.path.isfile(src_path):
            print('  [!] Missing:', res)
            missing.append(res)
            continue

        if os.path.exists(dst_path):
            bak_path = dst_path + '.bak'
            shutil.copy2(dst_path, bak_path)
            print('  [~] Backup:', res)

        shutil.copy2(src_path, dst_path)
        print('  [+] Deployed:', res)
        deployed += 1

    print()
    print('=== Done ===')
    print('Deployed:', deployed)

    if missing:
        print('Missing:', len(missing))
        for m in missing:
            print('  -', m)

    print()
    print('=== Verify ===')
    for res in RESOURCES:
        dst_path = os.path.join(DST_DIR, res)
        exists = os.path.isfile(dst_path)
        status = 'OK' if exists else 'MISSING'
        print(' ', status, res)

    print()
    print('Next: py deploy_clean_bml.py')

if __name__ == '__main__':
    main()
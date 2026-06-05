"""
auto_deploy.py — 自动提取并部署发型资源

原理：
  - BML: XOR解密 item{pak}.pak，搜索 itemcode → 找到 <root>...</root> 提取
  - SMD/PNG: 从 res{pak}.pak 条目中提取 i{itemcode}_* 文件
  - 部署到 Resource\item{pak}\i{itemcode}.bml + Resource\res{pak}\i{itemcode}_*

用法：
  python auto_deploy.py list                   # 查看已部署状态
  python auto_deploy.py scan                   # 扫描PAK中可用资源
  python auto_deploy.py 50125711               # 部署指定发型
  python auto_deploy.py 50120651               # 部署极限超赛
  python auto_deploy.py all                    # 部署全部
"""

import sys, os, shutil, time, struct, json
sys.stdout.reconfigure(encoding='utf-8')

GAME_DIR = os.path.join('C:\\', 'Program Files (x86)', 'T2CN', '\u8857\u5934\u7bee\u7403')
XOR_KEY = 0xFF

# 发型数据库（从 itemshop.json 提取）
# 格式: (itemcode, pak, name)
HAIR_TABLE = [
    (50120651, 727, '\u6781\u9650\u8d85\u8d5b\u53d1\u578b'),    # 极限超赛
    (50120701, 728, '\u9ed1\u8272\u6700\u5f3a\u8d85\u8d5b3'),   # 黑色最强超赛3
    (50121251, 732, '\u8d85\u8d5b\u4e4b\u795e\u53d1\u578b'),    # 超赛之神
    (50121981, 739, '\u6de1\u7c89\u8d85\u8d5b\u53d1\u578b'),    # 淡粉超赛
    (50122921, 747, '\u706b\u7130\u8d85\u8d5b\u53d1\u578b'),    # 火焰超赛
    (50119961, 723, '\u6700\u5f3a\u8d85\u8d5b\u53d1\u578b'),    # 最强超赛
    (50118411, 717, '\u5f69\u8272\u8d85\u8d5b5'),               # 彩色超赛5
    (50124241, 758, '\u91d1\u8272\u8d85\u8d5b\u53d1\u578b'),    # 金色超赛
    (50124911, 764, '\u9ed1\u767d\u8d85\u8d5b5\u53d1\u578b'),   # 黑白超赛5
    (50124971, 764, '\u9713\u8679\u8d85\u8d5b\u53d1\u578b'),    # 霓虹超赛
    (50125031, 764, '\u7834\u574f\u8005\u8d85\u8d5b\u53d1\u578b'),# 破坏者超赛
    (50125261, 766, '\u9ed1\u767d\u6700\u5f3a\u8d85\u8d5b3'),   # 黑白最强超赛3
    (50125651, 767, '\u95ea\u8000\u91d1\u8d85\u8d5b\u53d1\u578b'),# 闪耀金超赛
    (50125711, 768, '\u7d2b\u8272\u8d85\u8d5b\u53d1\u578b'),    # 紫色超赛 ✅ 工作中
    (50122451, 742, '\u9b3c\u9b45\u53d1\u578b'),                # 鬼魅 ✅ 工作中
]

def xor(data):
    return bytes(b ^ XOR_KEY for b in data)

def log(msg):
    print(f'  {msg}')

# ─── BML 提取（从 XOR 解密数据中搜 <root>...itemcode...</root>）───

def extract_bml_xml(item_pak_path, itemcode):
    """从 item{pak}.pak 中提取 BML 的 XML 内容"""
    if not os.path.exists(item_pak_path):
        return None
    with open(item_pak_path, 'rb') as f:
        raw = f.read()
    dec = xor(raw)
    needle = str(itemcode).encode('ascii')
    idx = dec.find(needle)
    if idx < 0:
        return None
    # 向前找最近的 <root>
    root_start = dec.rfind(b'<root>', max(0, idx - 5000), idx)
    if root_start < 0:
        return None
    # 向后找 </root>
    root_end = dec.find(b'</root>', idx, idx + 5000)
    if root_end < 0:
        return None
    root_end += len(b'</root>')
    xml_bytes = dec[root_start:root_end]
    # 验证
    text = xml_bytes.decode('utf-8', errors='replace')
    if '<root>' not in text:
        return None
    return text

# ─── SMD/PNG 提取（从 PAK 文件条目中扫文件名）───

def list_pak_file_names(pak_path):
    """返回 PAK 中所有文件名列表（字节搜索，不顺序解析）"""
    if not os.path.exists(pak_path):
        return []
    with open(pak_path, 'rb') as f:
        raw = f.read()
    is_xor = raw[0] > 0x7F
    buf = xor(raw) if is_xor else raw

    # 先找到所有文件名位置，再验证入口头
    # 文件名格式: iXXXXXXX.xxx\0 (或 cXXXXXXX.bml\0 等)
    results = []
    searched = set()

    for start_char in [b'i', b'c', b'e', b'a']:
        pos = 0
        while True:
            idx = buf.find(start_char, pos)
            if idx < 0 or len(results) > 5000:
                break
            # 找 null 终止
            end = buf.find(b'\x00', idx)
            if end < 0 or end - idx > 100:
                pos = idx + 1; continue
            name = buf[idx:end].decode('ascii', errors='replace')
            if '.' not in name or not all(c.isascii() and (c.isalnum() or c in '._-') for c in name):
                pos = idx + 1; continue
            if name in searched:
                pos = idx + 1; continue
            searched.add(name)

            # 向前 20 字节找入口头
            for hdr_ofs in range(20, 0, -1):
                hdr_start = idx - hdr_ofs
                if hdr_start < 0: continue
                nl = struct.unpack_from('<I', buf, hdr_start + 4)[0]
                if nl != end - idx + 1:  # name_len 要等于名字长度+1(null)
                    continue
                ds = struct.unpack_from('<I', buf, hdr_start + 12)[0]
                if ds <= 0 or ds > 100 * 1024 * 1024:
                    continue
                # 验证数据位置
                data_off = hdr_start + hdr_ofs + nl
                pad = (4 - (data_off % 4)) % 4
                data_off += pad
                if data_off + ds <= len(buf):
                    results.append((name, data_off, ds))
                    break  # 用了这个 header，跳出
            pos = idx + 1

    # 去重（可能有大小写不同版本）
    seen_names = set()
    unique = []
    for r in results:
        if r[0] not in seen_names:
            seen_names.add(r[0])
            unique.append(r)
    return unique

def read_pak_data(pak_path, offset, size):
    with open(pak_path, 'rb') as f:
        f.seek(offset)
        return f.read(size)

# ─── 部署 ───

def deploy_one(itemcode, pak_num, name=''):
    name_str = f' ({name})' if name else ''
    print(f'\n{"=" * 50}')
    print(f'  {itemcode}{name_str} (pak{pak_num})')
    print(f'{"=" * 50}')

    t0 = time.time()

    # === 1. BML ===
    ipak_path = os.path.join(GAME_DIR, f'item{pak_num}.pak')
    bml_ok = False
    if os.path.exists(ipak_path):
        xml_text = extract_bml_xml(ipak_path, itemcode)
        if xml_text:
            out_dir = os.path.join(GAME_DIR, 'Resource', f'item{pak_num}')
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f'i{itemcode}.bml')
            if os.path.exists(out_path):
                shutil.copy2(out_path, out_path + '.bak')
            encoded = xor(xml_text.encode('utf-8'))
            with open(out_path, 'wb') as f:
                f.write(encoded)
            log(f'  ✅ BML: i{itemcode}.bml ({len(encoded)}B)')
            # XML 参考
            xml_path = out_path.replace('.bml', '.xml')
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_text)
            bml_ok = True
        else:
            log(f'  ⚠️  BML: item{pak_num}.pak 中未找到 {itemcode} 的 <root>')
    else:
        log(f'  ⚠️  item{pak_num}.pak 不存在')

    # === 2. SMD/PNG ===
    rpak_path = os.path.join(GAME_DIR, f'res{pak_num}.pak')
    res_ok = False
    res_files = []
    if os.path.exists(rpak_path):
        entries = list_pak_file_names(rpak_path)
        prefix = f'i{itemcode}'.lower()
        matching = [e for e in entries if e[0].lower().startswith(prefix)]
        if matching:
            out_dir = os.path.join(GAME_DIR, 'Resource', f'res{pak_num}')
            os.makedirs(out_dir, exist_ok=True)
            for name, off, sz in matching:
                data = read_pak_data(rpak_path, off, sz)
                fpath = os.path.join(out_dir, name)
                if os.path.exists(fpath):
                    shutil.copy2(fpath, fpath + '.bak')
                with open(fpath, 'wb') as f:
                    f.write(data)
                res_files.append(name)
            log(f'  ✅ RES: {len(res_files)} 个文件')
            for fn in res_files[:6]:
                log(f'    {fn}')
            if len(res_files) > 6:
                log(f'    ... +{len(res_files)-6}')
            res_ok = True
        else:
            log(f'  ⚠️  RES: res{pak_num}.pak 中无 i{itemcode}* 文件')
    else:
        log(f'  ⚠️  res{pak_num}.pak 不存在')

    elapsed = time.time() - t0
    if bml_ok or res_ok:
        print(f'  ✅ 完成 ({elapsed:.1f}s)')
    else:
        print(f'  ❌ 失败 ({elapsed:.1f}s)')

def main():
    if len(sys.argv) < 2:
        print(__doc__); return

    arg = sys.argv[1].lower()
    
    if arg == 'list':
        print(f'\n{"Code":>10}  {"发型":<22}  PAK   BML   RES')
        print('-' * 55)
        seen = set()
        for code, pak, name in HAIR_TABLE:
            if (code, pak) in seen: continue
            seen.add((code, pak))
            bml_path = os.path.join(GAME_DIR, 'Resource', f'item{pak}', f'i{code}.bml')
            res_dir = os.path.join(GAME_DIR, 'Resource', f'res{pak}')
            bml_ok = os.path.exists(bml_path)
            res_ok = False
            if os.path.isdir(res_dir):
                for f in os.listdir(res_dir):
                    if f.lower().startswith(f'i{code}'.lower()):
                        res_ok = True; break
            s = f'{"✅" if bml_ok else " "}    {"✅" if res_ok else " "}'
            print(f'  {code:>8}  {name:<20}  {pak:<4}  {s}')

    elif arg == 'scan':
        print(f'\n{"Code":>10}  {"发型":<22}  PAK   BML?   RES?')
        print('-' * 55)
        seen = set()
        for code, pak, name in HAIR_TABLE:
            if (code, pak) in seen: continue
            seen.add((code, pak))
            # 查 BML
            ipak = os.path.join(GAME_DIR, f'item{pak}.pak')
            has_bml = False
            if os.path.exists(ipak):
                with open(ipak, 'rb') as f:
                    raw = f.read()
                dec = xor(raw)
                needle = str(code).encode('ascii')
                idx = dec.find(needle)
                if idx >= 0:
                    rs = dec.rfind(b'<root>', max(0, idx-5000), idx)
                    re = dec.find(b'</root>', idx, idx+5000)
                    has_bml = rs >= 0 and re >= 0
            # 查 RES SMD
            rpak = os.path.join(GAME_DIR, f'res{pak}.pak')
            res_count = 0
            if os.path.exists(rpak):
                with open(rpak, 'rb') as f:
                    rdata = f.read()
                needle2 = f'i{code}'.encode('ascii')
                pos = 0
                while True:
                    p = rdata.find(needle2, pos)
                    if p < 0: break
                    ext = rdata[p+len(needle2):p+len(needle2)+4]
                    if any(ext.lower().startswith(e) for e in [b'.smd', b'.png']):
                        res_count += 1
                    pos = p + 1
            print(f'  {code:>8}  {name:<20}  {pak:<4}  {"✅" if has_bml else " "}    {res_count}')

    elif arg == 'all':
        seen = set()
        for code, pak, name in HAIR_TABLE:
            if (code, pak) in seen: continue
            seen.add((code, pak))
            deploy_one(code, pak, name)
    else:
        try:
            code = int(arg)
        except:
            print(f'未知参数: {arg}')
            return
        for c, pak, name in HAIR_TABLE:
            if c == code:
                deploy_one(code, pak, name)
                return
        print(f'未找到 ItemCode {code}')

if __name__ == '__main__':
    main()

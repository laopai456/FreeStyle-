"""
repack_pak.py — PAK 文件读写 (NFGP 格式)
"""
import struct, os, shutil

class PGFNPak:
    def __init__(self, path):
        self.path = path
        self.entries = []
        self.file_count = 0
        self._load(path)

    def _load(self, path):
        data = open(path, 'rb').read()
        pos = 24
        # 尝试 2 种头大小
        for hdr_size in (20, 16):
            self.entries = []
            pos = 24
            ok_count = 0
            while pos + 24 < len(data):
                found = False
                for head_sz in (hdr_size,):  # try 16 or 20
                    if pos + head_sz + 4 > len(data):
                        continue
                    name_len_or_off = struct.unpack_from('<I', data, pos + 4)[0]
                    d0 = struct.unpack_from('<I', data, pos)[0]
                    d1 = struct.unpack_from('<I', data, pos + 8)[0] if head_sz >= 12 else 0
                    d2 = struct.unpack_from('<I', data, pos + 12)[0] if head_sz >= 16 else 0
                    
                    # name_len should be small and plausible
                    if not (3 <= name_len_or_off <= 80):
                        continue
                    
                    try:
                        name = data[pos + head_sz:pos + head_sz + name_len_or_off - 1].decode('ascii')
                    except:
                        continue
                    
                    if '.' not in name or not all(c.isascii() and (c.isalnum() or c in '._-') for c in name):
                        continue
                    
                    data_start = pos + head_sz + name_len_or_off
                    # 对齐到4字节
                    pad = (4 - (data_start % 4)) % 4
                    data_start += pad
                    
                    # data_size: 从 d0, d1, d2 中取合理值
                    data_size_candidates = []
                    for v in (d0, d1, d2):
                        if 0 < v < 500000000:
                            data_size_candidates.append(v)
                    
                    if not data_size_candidates:
                        continue
                    
                    data_size = min(data_size_candidates)
                    if data_start + data_size > len(data):
                        continue
                    
                    # 验证数据魔数（非强制）
                    fb = data[data_start:data_start+4]
                    if name.endswith('.png') and fb != b'\x89PNG':
                        continue
                    if name.endswith('.smd') and fb != b'SSKF':
                        continue
                    
                    self.entries.append({
                        'name': name,
                        'data_offset': data_start,
                        'data_size': data_size,
                    })
                    pos = data_start + data_size
                    ok_count += 1
                    found = True
                    break
                
                if not found:
                    pos += 1
                    
                if pos >= len(data) - 20:
                    break
            
            if ok_count > 5:  # 如果有足够条目，这个头大小是对的
                self.file_count = ok_count
                return
        
        self.file_count = len(self.entries)

    def find_entry(self, name):
        name = name.lower()
        for e in self.entries:
            if e['name'] == name:
                return e
        return None

    def list_files(self):
        return [e['name'] for e in self.entries]

    def verify_integrity(self):
        data = open(self.path, 'rb').read()
        for e in self.entries:
            if e['data_offset'] + e['data_size'] > len(data):
                return False
        return True

    def rebuild(self, output_path, replacements=None):
        data = open(self.path, 'rb').read()
        new_pak = bytearray()
        new_pak.extend(data[:24])
        for e in self.entries:
            name = e['name']
            if replacements and name in replacements:
                fd = replacements[name]
            else:
                fd = data[e['data_offset']:e['data_offset'] + e['data_size']]
            nb = name.encode('ascii') + b'\0'
            nl = len(nb)
            pad = (4 - (nl % 4)) % 4
            nb_padded = nb + b'\x00' * pad
            hdr = struct.pack('<IIII', 0, nl, 0, len(fd))
            new_pak.extend(hdr)
            new_pak.extend(nb_padded)
            new_pak.extend(fd)
        new_pak.extend(struct.pack('<IIII', 0x53554349, 1, 0, 0))
        bak = output_path + '.tmp'
        with open(bak, 'wb') as f:
            f.write(new_pak)
        os.replace(bak, output_path)

    def get_entry_checksum(self, name):
        import hashlib
        e = self.find_entry(name)
        if not e:
            return None
        data = open(self.path, 'rb').read()
        return hashlib.md5(data[e['data_offset']:e['data_offset'] + e['data_size']]).hexdigest()

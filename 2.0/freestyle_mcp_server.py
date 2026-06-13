"""
freestyle_mcp_server.py — FreeStyle 游戏 MCP Server
通过 server.py TCP 接口操作 Frida 运行时，本地脚本处理文件操作
"""
import json, os, sys, socket, struct, subprocess, logging

# MCP stdio 模式下 stdout 是协议通道，日志必须走 stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='[MCP] %(message)s')
log = logging.info

# ===== 常量 =====
ENGINE_HOST = '127.0.0.1'
ENGINE_PORT = 18731
GAME_DIR = r'C:\Program Files (x86)\T2CN\街头篮球'
XOR_KEY = 0xFF
ITEMSHOP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'bin', 'Debug', 'net8.0-windows', 'data', 'itemshop.json')

# ===== server.py TCP 通信 =====
def _send_cmd(cmd_dict):
    """向 server.py 发送 TCP 命令并获取响应"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((ENGINE_HOST, ENGINE_PORT))
        msg = json.dumps(cmd_dict, ensure_ascii=False) + '\n'
        sock.sendall(msg.encode('utf-8'))
        buf = b''
        while b'\n' not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        sock.close()
        line = buf.split(b'\n')[0]
        return json.loads(line.decode('utf-8'))
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

# ===== PAK/BML/SSKF 解析 =====
def xor_crypt(data):
    return bytes(b ^ XOR_KEY for b in data)

def parse_pgfn(data):
    """解析 PAK 的 PGFN 格式，返回 {name: element_data}"""
    if data[:4] != b'PGFN':
        return {}
    entries = {}
    # 先收集所有条目信息：{name_offset: (name, data_offset)}
    entry_list = []
    text = data.decode('latin-1')  # 用 latin-1 保留原始字节
    for name_bytes in [b'itemshop.txt', b'itemshopex.txt', b'badgepackex.txt',
                       b'effectitem.txt', b'effectmotion.txt', b'effectskin.txt',
                       b'effectspecialty.txt', b'packageitem.txt', b'packagerareitem.txt']:
        idx = data.find(name_bytes)
        if idx < 0:
            continue
        entry_start = idx - 20
        if entry_start < 0x18:
            continue
        dw1 = struct.unpack_from('<I', data, entry_start + 4)[0]  # name size
        dw2 = struct.unpack_from('<I', data, entry_start + 8)[0]  # data offset
        name = data[idx:idx + dw1].rstrip(b'\x00').decode('ascii', errors='replace')
        entry_list.append((name, dw2))
    # 按 data_offset 排序，相邻条目之间的差值就是数据大小
    entry_list.sort(key=lambda x: x[1])
    for i, (name, offset) in enumerate(entry_list):
        if i + 1 < len(entry_list):
            size = entry_list[i + 1][1] - offset
        else:
            size = len(data) - offset
        entries[name] = data[offset:offset + size]
    return entries

def find_sskf_in_data(data, target_name=None):
    """在数据中搜索 SSKF 条目"""
    results = []
    magic = b'SSKF'
    pos = 0
    while True:
        idx = data.find(magic, pos)
        if idx == -1:
            break
        name_start = idx + 8
        name_end = data.find(b'\x00', name_start, name_start + 64)
        if name_end == -1:
            name_end = name_start + 64
        sskf_name = data[name_start:name_end].decode('ascii', errors='replace')
        mesh_count = struct.unpack_from('<I', data, idx + 4)[0] if idx + 4 <= len(data) else 0
        if target_name is None or target_name in sskf_name:
            results.append({'offset': idx, 'name': sskf_name, 'mesh_count': mesh_count})
        pos = idx + 4
    return results

# ===== MCP Server =====
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FreeStyle-Toolkit")

# ---------- Frida 运行时工具 ----------

@mcp.tool()
def frida_connect() -> str:
    """连接到 FreeStyle.exe 进程（Frida attach）。需要游戏正在运行。"""
    result = _send_cmd({'cmd': 'CONNECT'})
    if result.get('status') == 'ok':
        return f"已连接 PID={result['pid']}"
    return f"连接失败: {result.get('error', '未知错误')}"

@mcp.tool()
def frida_status() -> str:
    """查询当前 Frida 连接状态、替换映射、已收集装备数。"""
    result = _send_cmd({'cmd': 'STATUS'})
    if result.get('status') == 'ok':
        lines = [
            f"连接: {'是' if result['connected'] else '否'}",
            f"PID: {result.get('pid', '无')}",
            f"替换映射: {len(result.get('replace_map', {}))} 条",
            f"已收集装备: {result.get('collected', 0)} 个",
        ]
        if result.get('replace_map'):
            for src, dst in result['replace_map'].items():
                lines.append(f"  {src} → {dst}")
        return '\n'.join(lines)
    return f"查询失败: {result.get('error', '未知错误')}"

@mcp.tool()
def launch_game() -> str:
    """启动 FreeStyle.exe 并自动 CRC patch（绕过 Apollo 反作弊）。需要游戏未在运行。"""
    result = _send_cmd({'cmd': 'LAUNCH_GAME', 'game_dir': GAME_DIR})
    if result.get('status') == 'ok':
        return f"已启动 PID={result['pid']}: {result.get('msg', '')}"
    return f"启动失败: {result.get('error', '未知错误')}"

@mcp.tool()
def read_current_outfit() -> str:
    """读取当前角色穿搭（8个装备槽的 ItemCode 和名称）。需要先进一次房间触发收集。"""
    result = _send_cmd({'cmd': 'READ_CURRENT'})
    if result.get('status') != 'ok':
        return f"读取失败: {result.get('error', '未知错误')}"
    slots = result.get('slots', {})
    if not slots:
        return result.get('hint', '无数据，请先进房间触发收集')
    lines = []
    for slot_str in sorted(slots.keys(), key=lambda x: int(x)):
        s = slots[slot_str]
        lines.append(f"Slot{slot_str}: {s['code']} ({s.get('name', '?')}) pak={s.get('pak', '?')}")
    return '\n'.join(lines)

@mcp.tool()
def replace_outfit(src_dst_map: dict, effect_map: dict = None, enable_effect: bool = True) -> str:
    """设置装备替换映射。src_dst_map: {源ItemCode: 目标ItemCode}，effect_map: {目标ItemCode: 特效ID}。设置后进房间自动触发替换。"""
    cmd = {
        'cmd': 'REPLACE',
        'map': {str(k): str(v) for k, v in src_dst_map.items()},
        'enable_effect': enable_effect,
    }
    if effect_map:
        cmd['effect_map'] = {str(k): int(v) for k, v in effect_map.items()}
    result = _send_cmd(cmd)
    if result.get('status') == 'ok':
        rmap = result.get('map', {})
        return f"替换已设置: {len(rmap)} 个映射\n" + '\n'.join(f"  {s} → {d}" for s, d in rmap.items())
    return f"设置失败: {result.get('error', '未知错误')}"

@mcp.tool()
def restore_outfit() -> str:
    """还原所有装备替换，恢复原始 ItemCode。"""
    result = _send_cmd({'cmd': 'RESTORE'})
    if result.get('status') == 'ok':
        return "已还原"
    return f"还原失败: {result.get('error', '未知错误')}"

@mcp.tool()
def recollect_outfit() -> str:
    """重置装备收集状态，下次进房间会重新收集穿搭数据。"""
    result = _send_cmd({'cmd': 'RECOLLECT'})
    if result.get('status') == 'ok':
        return "已重置收集状态"
    return f"重置失败: {result.get('error', '未知错误')}"

@mcp.tool()
def dword_scan() -> str:
    """手动触发 DWORD 内存扫描（替换 ItemCode + 写入特效）。需要已连接且已设置替换映射。"""
    result = _send_cmd({'cmd': 'DWORD_SCAN'})
    if result.get('status') == 'ok':
        return f"扫描完成: {result.get('replaced', 0)} 替换, {result.get('effects', 0)} 特效"
    return f"扫描失败: {result.get('error', '未知错误')}"

@mcp.tool()
def get_hook_log(since: int = 0, keyword: str = "") -> str:
    """获取 Hook 日志缓冲区。since: 从第几条开始获取（0=全部）。keyword: 过滤关键词（如'异常','batch_reset','sprintf命中'）"""
    result = _send_cmd({'cmd': 'HOOK_LOG', 'since': since})
    if result.get('status') == 'ok':
        lines = result.get('lines', [])
        total = result.get('total', 0)
        if not lines:
            return "无日志"
        if keyword:
            lines = [l for l in lines if keyword in l]
            if not lines:
                return f"无包含'{keyword}'的日志（共{total}条）"
            return f"过滤'{keyword}'（{len(lines)}/{total}条）:\n" + '\n'.join(lines[-50:])
        return f"日志 (共{total}条):\n" + '\n'.join(lines[-50:])  # 最多返回50条
    return f"获取失败: {result.get('error', '未知错误')}"

# ---------- Resources（只读资源，按需读取，不自动推送） ----------

@mcp.resource("frida://status")
def resource_status() -> str:
    """Frida 连接状态、替换映射数、已收集装备数"""
    result = _send_cmd({'cmd': 'STATUS'})
    if result.get('status') != 'ok':
        return f"查询失败: {result.get('error', '未知错误')}"
    lines = [
        f"连接: {'是' if result['connected'] else '否'}",
        f"PID: {result.get('pid', '无')}",
        f"替换映射: {len(result.get('replace_map', {}))} 条",
        f"已收集装备: {result.get('collected', 0)} 个",
    ]
    if result.get('replace_map'):
        for src, dst in result['replace_map'].items():
            lines.append(f"  {src} → {dst}")
    return '\n'.join(lines)

@mcp.resource("frida://hook_log")
def resource_hook_log() -> str:
    """Hook 日志缓冲区（最近50条，含异常/批次重置/替换命中）"""
    result = _send_cmd({'cmd': 'HOOK_LOG', 'since': 0})
    if result.get('status') != 'ok':
        return f"获取失败: {result.get('error', '未知错误')}"
    lines = result.get('lines', [])
    total = result.get('total', 0)
    if not lines:
        return "无日志"
    return f"日志 (共{total}条):\n" + '\n'.join(lines[-50:])

@mcp.resource("frida://current_outfit")
def resource_current_outfit() -> str:
    """当前角色穿搭（各装备槽的 ItemCode 和名称）"""
    result = _send_cmd({'cmd': 'READ_CURRENT'})
    if result.get('status') != 'ok':
        return f"读取失败: {result.get('error', '未知错误')}"
    slots = result.get('slots', {})
    if not slots:
        return result.get('hint', '无数据，请先进房间触发收集')
    lines = []
    for slot_str in sorted(slots.keys(), key=lambda x: int(x)):
        s = slots[slot_str]
        lines.append(f"Slot{slot_str}: {s['code']} ({s.get('name', '?')}) pak={s.get('pak', '?')}")
    return '\n'.join(lines)

@mcp.resource("frida://replace_map")
def resource_replace_map() -> str:
    """当前装备替换映射表"""
    result = _send_cmd({'cmd': 'STATUS'})
    if result.get('status') != 'ok':
        return f"查询失败: {result.get('error', '未知错误')}"
    rmap = result.get('replace_map', {})
    if not rmap:
        return "无替换映射（未设置或已还原）"
    lines = [f"共 {len(rmap)} 个映射:"]
    for src, dst in rmap.items():
        lines.append(f"  {src} → {dst}")
    emap = result.get('effect_map', {})
    if emap:
        lines.append(f"特效映射 ({len(emap)} 个):")
        for code, eid in emap.items():
            lines.append(f"  {code} → effect={eid}")
    return '\n'.join(lines)

# ---------- 道具查询工具 ----------

@mcp.tool()
def search_item(keyword: str, limit: int = 20) -> str:
    """搜索道具。keyword: 名称或编号关键词，limit: 最大返回数。"""
    result = _send_cmd({'cmd': 'SEARCH', 'keyword': keyword})
    if result.get('status') != 'ok':
        return f"搜索失败: {result.get('error', '未知错误')}"
    items = result.get('results', [])[:limit]
    if not items:
        return f"未找到匹配 '{keyword}' 的道具"
    lines = [f"找到 {len(items)} 个道具:"]
    for item in items:
        lines.append(f"  {item['code']} | {item.get('name', '?')} | pak={item.get('pak', '?')}")
    return '\n'.join(lines)

@mcp.tool()
def item_lookup(code: str) -> str:
    """查询单个道具详情。code: ItemCode（如 50125461）。"""
    result = _send_cmd({'cmd': 'SEARCH', 'keyword': code})
    if result.get('status') != 'ok':
        return f"查询失败: {result.get('error', '未知错误')}"
    for item in result.get('results', []):
        if item['code'] == str(code):
            return f"ItemCode: {item['code']}\n名称: {item.get('name', '?')}\nPAK: {item.get('pak', '?')}"
    # 直接从 itemshop.json 查
    try:
        with open(ITEMSHOP_PATH, 'r', encoding='utf-8') as f:
            db = json.load(f)
        info = db.get(str(code))
        if info:
            return f"ItemCode: {code}\n名称: {info.get('name', '?')}\nPAK: {info.get('pak', '?')}\n特效: {info.get('effect', '?')}"
    except Exception:
        pass
    return f"未找到 ItemCode={code}"

# ---------- 文件操作工具 ----------

@mcp.tool()
def pak_list(pak_path: str) -> str:
    """列出 PAK 文件中的所有条目。pak_path: PAK 文件完整路径。"""
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()
        entries = parse_pgfn(data)
        if not entries:
            return "PAK 文件为空或格式不正确（非 PGFN 格式）"
        lines = [f"PAK 文件: {pak_path} ({len(data)} bytes, {len(entries)} 个条目)"]
        for name, edata in entries.items():
            lines.append(f"  {name} ({len(edata)} bytes)")
        return '\n'.join(lines)
    except FileNotFoundError:
        return f"文件不存在: {pak_path}"
    except Exception as e:
        return f"解析失败: {e}"

@mcp.tool()
def pak_extract(pak_path: str, entry_name: str, output_dir: str = "") -> str:
    """从 PAK 提取指定条目并保存。pak_path: PAK路径, entry_name: 条目名, output_dir: 输出目录（默认PAK同目录）。"""
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()
        entries = parse_pgfn(data)
        if entry_name not in entries:
            available = list(entries.keys())[:10]
            return f"条目 '{entry_name}' 不存在。可用条目: {available}"
        out_dir = output_dir or os.path.dirname(pak_path)
        out_path = os.path.join(out_dir, entry_name.replace('/', '_'))
        with open(out_path, 'wb') as f:
            f.write(entries[entry_name])
        return f"已提取: {out_path} ({len(entries[entry_name])} bytes)"
    except Exception as e:
        return f"提取失败: {e}"

@mcp.tool()
def bml_decode(pak_path: str, item_code: str = "") -> str:
    """解码 PAK 中的 BML 文件为 XML。pak_path: PAK路径, item_code: 可选，只提取包含此 ItemCode 的 <root> 段。"""
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()
        entries = parse_pgfn(data)
        bmls = [n for n in entries if n.endswith('.bml')]
        if not bmls:
            return "PAK 中没有 BML 文件"
        bml_data = entries[bmls[0]]
        decoded = xor_crypt(bml_data)
        try:
            xml_text = decoded.decode('utf-8', errors='replace')
        except Exception:
            xml_text = decoded.decode('ascii', errors='replace')
        if item_code:
            # 提取包含目标 ItemCode 的 <root> 段
            search_str = item_code.encode('utf-8')
            idx = decoded.find(search_str)
            if idx < 0:
                return f"BML 中未找到 ItemCode={item_code}"
            root_start = decoded.rfind(b'<root>', 0, idx)
            root_end = decoded.find(b'</root>', idx)
            if root_start < 0 or root_end < 0:
                return "XML 结构不完整"
            root_end += len(b'</root>')
            section = decoded[root_start:root_end].decode('utf-8', errors='replace')
            # 限制返回长度
            if len(section) > 4000:
                section = section[:4000] + '\n... (截断)'
            return section
        # 返回完整 XML（截断）
        if len(xml_text) > 4000:
            xml_text = xml_text[:4000] + '\n... (截断，共' + str(len(xml_text)) + '字符)'
        return xml_text
    except Exception as e:
        return f"解码失败: {e}"

@mcp.tool()
def sskf_list(pak_path: str, filter_name: str = "") -> str:
    """列出 PAK 中的 SSKF 条目。pak_path: PAK路径, filter_name: 可选，按名称过滤。"""
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()
        results = find_sskf_in_data(data, filter_name or None)
        if not results:
            return "未找到 SSKF 条目" + (f" 匹配 '{filter_name}'" if filter_name else "")
        lines = [f"找到 {len(results)} 个 SSKF 条目:"]
        for r in results[:30]:
            lines.append(f"  offset=0x{r['offset']:08X} name=\"{r['name']}\" mesh_count={r['mesh_count']}")
        return '\n'.join(lines)
    except Exception as e:
        return f"搜索失败: {e}"

@mcp.tool()
def sskf_extract(pak_path: str, target_name: str, output_dir: str = "") -> str:
    """从 PAK 提取 SSKF 数据。pak_path: PAK路径, target_name: 目标文件名, output_dir: 输出目录。"""
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()
        results = find_sskf_in_data(data, target_name)
        targets = [r for r in results if target_name in r['name']]
        if not targets:
            return f"未找到包含 '{target_name}' 的 SSKF"
        t = targets[0]
        # 提取 header (512B) + mesh data
        header = data[t['offset']:t['offset'] + 512]
        mesh_start = t['offset'] + 512
        # 找下一个 SSKF 确定边界
        next_sskf = data.find(b'SSKF', t['offset'] + 4)
        if next_sskf > mesh_start:
            mesh_size = next_sskf - mesh_start
        else:
            mesh_size = min(200000, len(data) - mesh_start)
        mesh = data[mesh_start:mesh_start + mesh_size]
        out_dir = output_dir or os.path.dirname(pak_path)
        out_path = os.path.join(out_dir, f"sskf_{target_name.replace('/', '_')}.bin")
        with open(out_path, 'wb') as f:
            f.write(header + mesh)
        return f"已提取: {out_path} ({512 + len(mesh)} bytes, name=\"{t['name']}\")"
    except Exception as e:
        return f"提取失败: {e}"

@mcp.tool()
def update_itemshop() -> str:
    """从游戏的 item_text.pak 解包 itemshop.txt 并重建 itemshop.json（最新最全数据源）。"""
    pak_path = os.path.join(GAME_DIR, 'item_text.pak')
    if not os.path.isfile(pak_path):
        return f"item_text.pak 不存在: {pak_path}"
    try:
        with open(pak_path, 'rb') as f:
            data = f.read()

        # 解包 PAK，提取 itemshop.txt
        entries = parse_pgfn(data)
        if 'itemshop.txt' not in entries:
            # fallback: 直接搜索 ItemCode 标记
            marker = b'ItemCode\tPakNum'
            idx = data.find(marker)
            if idx < 0:
                return "item_text.pak 中未找到 itemshop.txt 条目和 ItemCode 标记"
            end = data.find(b'\n', idx)
            text_data = data[end + 1:].decode('gbk', errors='replace')
        else:
            raw = entries['itemshop.txt']
            # 找到表头行，跳过
            header_end = raw.find(b'\n')
            if header_end < 0:
                return "itemshop.txt 内容异常：无换行"
            text_data = raw[header_end + 1:].decode('gbk', errors='replace')

        # 解析 TSV 数据，重建 JSON
        db = {}
        for line in text_data.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 4 and parts[0].strip().isdigit():
                code = parts[0].strip()
                pak_num = parts[1].strip() if len(parts) > 1 else ''
                effect = parts[2].strip() if len(parts) > 2 else ''
                name = parts[3].strip() if len(parts) > 3 else ''
                comment = parts[4].strip() if len(parts) > 4 else ''
                db[code] = {
                    'name': name,
                    'pak': pak_num,
                    'effect': effect or comment
                }

        # 同时提取 itemshopex.txt 补充额外道具
        if 'itemshopex.txt' in entries:
            raw_ex = entries['itemshopex.txt']
            header_end = raw_ex.find(b'\n')
            if header_end >= 0:
                text_ex = raw_ex[header_end + 1:].decode('gbk', errors='replace')
                new_from_ex = 0
                for line in text_ex.split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 4 and parts[0].strip().isdigit():
                        code = parts[0].strip()
                        if code not in db:
                            pak_num = parts[1].strip() if len(parts) > 1 else ''
                            effect = parts[2].strip() if len(parts) > 2 else ''
                            name = parts[3].strip() if len(parts) > 3 else ''
                            comment = parts[4].strip() if len(parts) > 4 else ''
                            db[code] = {
                                'name': name,
                                'pak': pak_num,
                                'effect': effect or comment
                            }
                            new_from_ex += 1

        # 写入 itemshop.json（C# 工具运行时读取）
        os.makedirs(os.path.dirname(ITEMSHOP_PATH), exist_ok=True)
        with open(ITEMSHOP_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

        return f"重建完成: 共{len(db)}条道具（从 item_text.pak 全量重建）"
    except Exception as e:
        return f"更新失败: {e}"

# ===== 运行 =====
if __name__ == "__main__":
    mcp.run()

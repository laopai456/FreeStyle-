#!/usr/bin/env python3
"""
archive_session.py — 进度文件归档工具

用法:
  # 归档单个进度文件
  python archive_session.py progress_20260530.md

  # 批量归档所有未归档的进度文件
  python archive_session.py --batch

  # 强制重新归档所有进度文件
  python archive_session.py --batch --force

功能:
  1. 从进度文件中提取试验记录 → 追加到 02_试验记录.md
  2. 从进度文件中提取地址表 → 追加到 03_常量地址表.md
  3. 从进度文件中提取知识结论 → 追加到 01_知识库.md
  4. 在进度文件头部添加 # 已归档 标记

工作目录: 脚本所在的 apollo_dump 目录
"""
import sys, os, re, json
from datetime import datetime

# ── 路径 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_DIR = os.path.join(SCRIPT_DIR, 'progress')
KB_FILE = os.path.join(SCRIPT_DIR, '01_知识库.md')
TEST_LOG_FILE = os.path.join(SCRIPT_DIR, '02_试验记录.md')
ADDR_TABLE_FILE = os.path.join(SCRIPT_DIR, '03_常量地址表.md')
STATE_FILE = os.path.join(SCRIPT_DIR, '.archive_state.json')

os.makedirs(PROGRESS_DIR, exist_ok=True)

# ── 工具函数 ───────────────────────────────────────────

def read_file(path):
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

def append_file(path, text):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(text)

def get_date_from_filename(fname):
    """从文件名提取日期，如 progress_20260530.md → 05-30"""
    m = re.search(r'(\d{4})(\d{2})(\d{2})', fname)
    if m:
        return f'{m.group(2)}-{m.group(3)}'
    return '??-??'

def is_already_archived(content):
    return '已归档' in content[:200]

def mark_archived(filepath):
    """在进度文件头部添加已归档标记"""
    content = read_file(filepath)
    if is_already_archived(content):
        return False
    # 在第一行#后面添加归档标记
    lines = content.split('\n')
    if lines[0].startswith('# '):
        lines.insert(1, '')
        lines.insert(2, '> ⏳ **已归档** — 信息已提取到 01_知识库 / 02_试验记录 / 03_常量地址表')
        lines.insert(3, '')
    write_file(filepath, '\n'.join(lines))
    return True

# ── 试验记录提取 ───────────────────────────────────────

def extract_test_records(content, date_tag):
    """
    从进度文件中提取试验记录。
    匹配模式:
      - "结果: ❌/✅/⚠️/🔁" 的段落
      - "**结果**" 段落
      - "### N.N Title" + "根因:" 的结构
    """
    records = []
    lines = content.split('\n')
    
    current_section = ''
    current_method = ''
    current_result = ''
    current_cause = ''
    collecting = False
    in_method_block = False
    
    for i, line in enumerate(lines):
        # 检测段落标题
        m_section = re.match(r'^#{2,4}\s+(§?\d+[\.\d]*)?\s*(.+)', line)
        if m_section:
            # 如果正在收集，保存上一个
            if current_method and current_result:
                records.append(_make_record(date_tag, current_section, current_method, current_result, current_cause))
            current_section = line.strip()
            current_method = ''
            current_result = ''
            current_cause = ''
            collecting = False
            in_method_block = False
        
        # 检测方法/实验名称
        if re.match(r'^#{2,4}\s+.*(实验|test|Test|Hook|方法|方案|尝试)', line, re.IGNORECASE):
            current_method = line.strip()
            collecting = True
        
        # 检测行内结果标记
        m_r = re.search(r'\*\*结果\*\*[：:]\s*([✅❌⚠️🔁])', line)
        if m_r:
            current_result = m_r.group(1)
            collecting = True
        m_r2 = re.search(r'(结果|Result)[：:]\s*([✅❌⚠️🔁])', line)
        if m_r2:
            current_result = m_r2.group(2)
            collecting = True
        
        # 检测行内根因
        m_c = re.search(r'\*\*根因\*\*[：:]\s*(.+)', line)
        if m_c:
            current_cause = m_c.group(1).strip()
        m_c2 = re.search(r'(根因|Root Cause)[：:]\s*(.+)', line)
        if m_c2:
            current_cause = m_c2.group(2).strip()
        
        # 检测失败/成功行
        m_fail = re.search(r'^[-*]\s+\*\*结果\*\*[：:]\s*([✅❌⚠️🔁])\s*(.*)', line)
        if m_fail:
            records.append(_make_record(date_tag, current_section, m_fail.group(2).strip() or current_method, m_fail.group(1), ''))
            continue
        
        # 检测表格行中的结果
        if '|' in line and ('✅' in line or '❌' in line or '⚠️' in line or '🔁' in line):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                # 尝试从表格列推断：通常有方法名/结果/说明等
                for cell in cells:
                    if cell in ('✅', '❌', '⚠️', '🔁'):
                        result_icon = cell
                        break
                else:
                    continue
                # 取表格第一列作为方法名
                method_name = cells[0]
                records.append(_make_record(date_tag, current_section, method_name, result_icon, ''))
                continue
    
    # 最后一个
    if current_method and current_result:
        records.append(_make_record(date_tag, current_section, current_method, current_result, current_cause))
    
    return records


def _make_record(date, section, method, result, cause):
    return {
        'date': date,
        'section': section[:80] if section else '',
        'method': method[:100] if method else '',
        'result': result,
        'cause': cause[:200] if cause else '',
        'source': f'progress_{date.replace("-","")}' if date else ''
    }


def append_test_records(records):
    """将新发现的试验记录追加到 02_试验记录.md"""
    if not records:
        return 0
    
    # 读取已有记录（去重）
    existing = read_file(TEST_LOG_FILE)
    existing_lines = set()
    for line in existing.split('\n'):
        if line.startswith('| ') and not line.startswith('| 日期 |'):
            existing_lines.add(line.strip())
    
    new_count = 0
    with open(TEST_LOG_FILE, 'a', encoding='utf-8') as f:
        for r in records:
            row = f'| {r["date"]} | {r["method"]} | {r["result"]} | {r["cause"]} | {r["source"]} |'
            if row not in existing_lines:
                f.write(row + '\n')
                existing_lines.add(row)
                new_count += 1
    
    return new_count

# ── 地址表提取 ────────────────────────────────────────

def extract_addresses(content, date_tag, source_file):
    """
    提取地址/偏移量信息。
    匹配:
      - Markdown表格: | 名称 | RVA | ...
      - 行内: RVA: 0x... 或 @0x... 或 地址: 0x...
    """
    addrs = []
    lines = content.split('\n')
    
    # 检测地址表
    in_table = False
    table_headers = []
    
    for i, line in enumerate(lines):
        # Markdown表格行
        if line.startswith('| ') and '|' in line[2:]:
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]  # 去掉首尾空
            
            if i > 0 and lines[i-1].startswith('|---'):
                # 表头后紧跟的|---行，说明前面一行是表头
                in_table = True
                header_line = lines[i-1]
                if i >= 2:
                    table_headers = [c.strip() for c in lines[i-2].split('|') if c.strip()]
                continue
            
            if in_table and len(cells) >= 2:
                has_rva = False
                rva_val = ''
                name_val = cells[0] if len(cells) > 0 else ''
                
                for ci, cell in enumerate(cells):
                    if '0x' in cell:
                        has_rva = True
                        rva_val = cell
                
                if has_rva and name_val:
                    # 提取说明列
                    desc = ''
                    for ci, cell in enumerate(cells):
                        if ci > 0 and '0x' not in cell and cell not in ('✅', '❌'):
                            desc = cell[:100]
                    addrs.append({
                        'name': name_val[:80],
                        'rva': rva_val[:40],
                        'desc': desc,
                        'source': source_file
                    })
        else:
            in_table = False
        
        # 单行地址模式
        m_addr = re.search(r'(RVA|地址|Address|入口)\s*[：:]\s*(0x[0-9a-fA-F]+)', line)
        if m_addr:
            # 找前面的函数名
            before = line[:m_addr.start()].strip()
            func_name = before.split()[-1] if before else '?'
            addrs.append({
                'name': func_name[:80],
                'rva': m_addr.group(2)[:40],
                'desc': line.strip()[:100],
                'source': source_file
            })
    
    return addrs


def append_addresses(addrs):
    """追加地址到 03_常量地址表.md"""
    if not addrs:
        return 0
    
    existing = read_file(ADDR_TABLE_FILE)
    existing_lines = set()
    for line in existing.split('\n'):
        if line.startswith('| ') and '|' in line[2:]:
            existing_lines.add(line.strip())
    
    new_count = 0
    with open(ADDR_TABLE_FILE, 'a', encoding='utf-8') as f:
        for a in addrs:
            row = f'| {a["name"]} | {a["rva"]} | {a["desc"]} | {a["source"]} |'
            if row not in existing_lines:
                f.write(row + '\n')
                existing_lines.add(row)
                new_count += 1
    
    return new_count

# ── 知识库内容提取 ─────────────────────────────────────

def extract_knowledge(content, date_tag, source_file):
    """
    提取关键结论/发现。
    匹配:
      - ## 关键结论 / 关键发现 段落
      - **关键发现**: ... 行
      - **结论**: ... 行
    """
    knowledge_items = []
    lines = content.split('\n')
    
    in_conclusion = False
    conclusion_lines = []
    current_topic = ''
    
    for line in lines:
        stripped = line.strip()
        
        # 检测结论段落
        if re.match(r'^#{1,4}\s+(关键结论|关键发现|结论|Summary|Findings)', stripped, re.IGNORECASE):
            if conclusion_lines:
                knowledge_items.append({
                    'topic': current_topic,
                    'content': '\n'.join(conclusion_lines)[:500],
                    'source': source_file
                })
                conclusion_lines = []
            in_conclusion = True
            current_topic = stripped
            continue
        
        # 检测行内结论
        m = re.search(r'\*\*(关键结论|关键发现|结论)\*\*[：:]\s*(.+)', stripped)
        if m:
            if conclusion_lines:
                knowledge_items.append({
                    'topic': current_topic,
                    'content': '\n'.join(conclusion_lines)[:500],
                    'source': source_file
                })
                conclusion_lines = []
            in_conclusion = True
            current_topic = m.group(2)[:80]
            conclusion_lines.append(m.group(2))
            continue
        
        if in_conclusion:
            if stripped and not stripped.startswith('#'):
                conclusion_lines.append(stripped)
            elif not stripped:
                conclusion_lines.append('')
            else:
                # 下一个标题
                if conclusion_lines:
                    knowledge_items.append({
                        'topic': current_topic,
                        'content': '\n'.join(conclusion_lines)[:500],
                        'source': source_file
                    })
                    conclusion_lines = []
                in_conclusion = False
        
        # 检测"关键发现"开头的行
        if stripped.startswith('关键发现') or stripped.startswith('**关键发现**'):
            knowledge_items.append({
                'topic': '关键发现',
                'content': stripped[:300],
                'source': source_file
            })
    
    # 最后一段
    if conclusion_lines:
        knowledge_items.append({
            'topic': current_topic,
            'content': '\n'.join(conclusion_lines)[:500],
            'source': source_file
        })
    
    return knowledge_items


def append_knowledge(items):
    """追加知识到 01_知识库.md"""
    if not items:
        return 0
    
    existing = read_file(KB_FILE)
    new_count = 0
    
    with open(KB_FILE, 'a', encoding='utf-8') as f:
        for item in items:
            topic = item['topic']
            content = item['content']
            source = item['source']
            
            # 检查是否已存在
            marker = f'<!-- src:{source}:{topic[:30]} -->'
            if marker in existing:
                continue
            
            f.write(f'\n{marker}\n')
            f.write(f'### {topic}\n\n')
            f.write(f'{content}\n\n')
            f.write(f'_来源: {source}_\n\n')
            new_count += 1
    
    return new_count

# ── 主流程 ─────────────────────────────────────────────

def archive_file(filepath, date_tag=None):
    """归档单个进度文件"""
    fname = os.path.basename(filepath)
    if date_tag is None:
        date_tag = get_date_from_filename(fname)
    
    content = read_file(filepath)
    if not content.strip():
        print(f'  [跳过] {fname} (空文件)')
        return
    
    # 提取
    records = extract_test_records(content, date_tag)
    addrs = extract_addresses(content, date_tag, fname)
    knowledge = extract_knowledge(content, date_tag, fname)
    
    # 写入
    n_records = append_test_records(records)
    n_addrs = append_addresses(addrs)
    n_knowledge = append_knowledge(knowledge)
    
    # 标记已归档
    marked = mark_archived(filepath)
    
    if marked or n_records or n_addrs or n_knowledge:
        parts = []
        if marked: parts.append('标记归档')
        if n_records: parts.append(f'{n_records}条试验')
        if n_addrs: parts.append(f'{n_addrs}条地址')
        if n_knowledge: parts.append(f'{n_knowledge}条知识')
        print(f'  [OK] {fname}: {", ".join(parts)}')
    else:
        print(f'  [--] {fname}: 无新内容')


def batch_archive(force=False):
    """批量归档所有进度文件"""
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE, 'r'))
        except:
            pass
    
    files = sorted(os.listdir(PROGRESS_DIR))
    md_files = [f for f in files if f.endswith('.md') and f.startswith('progress_')]
    
    total = len(md_files)
    archived = 0
    skipped = 0
    
    for fname in md_files:
        fpath = os.path.join(PROGRESS_DIR, fname)
        content = read_file(fpath)
        
        if not force and is_already_archived(content):
            skipped += 1
            continue
        
        archive_file(fpath)
        archived += 1
    
    # 保存状态
    state['last_batch'] = datetime.now().isoformat()
    state['total_files'] = total
    state['archived'] = archived
    state['skipped'] = skipped
    json.dump(state, open(STATE_FILE, 'w'))
    
    print(f'\n批量归档完成: {total}个文件, 新归档{archived}, 跳过{skipped}')


def init_docs():
    """创建3个合并文档（如不存在）"""
    templates = {
        KB_FILE: """# 知识库

> 所有已确认的知识结论，按主题分类。
> 更新方式: `python archive_session.py <进度文件>` 自动追加。
> 最后更新: 初始创建

""",
        TEST_LOG_FILE: """# 试验记录

> 所有已做测试的统一日志。**新想法先查此表**，避免重复。
> 更新方式: `python archive_session.py <进度文件>` 自动追加。
>
> 标记: ✅ 成功 | ❌ 失败 | ⚠️ 有条件可用 | 🔁 未走完

| 日期 | 方法 | 结果 | 根因 | 来源 |
|------|------|------|------|------|
""",
        ADDR_TABLE_FILE: """# 常量地址表

> 所有已验证的函数地址/偏移量。基础地址: 0x400000 (无ASLR)
> 更新方式: `python archive_session.py <进度文件>` 自动追加。

| 名称 | RVA | 说明 | 来源 |
|------|-----|------|------|
"""
    }
    
    for path, content in templates.items():
        if not os.path.exists(path):
            write_file(path, content)
            print(f'  [新建] {os.path.basename(path)}')


if __name__ == '__main__':
    init_docs()
    
    if '--batch' in sys.argv:
        force = '--force' in sys.argv
        batch_archive(force)
    elif len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            # 可能在progress目录下
            filepath = os.path.join(PROGRESS_DIR, sys.argv[1])
        if not os.path.exists(filepath):
            print(f'[错误] 文件不存在: {sys.argv[1]}')
            sys.exit(1)
        archive_file(filepath)
    else:
        print(__doc__.strip())
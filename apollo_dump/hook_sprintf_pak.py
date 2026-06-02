"""
hook_sprintf_pak.py — 方案2: sprintf替换 + BML数据注入
1. 从res768.pak提取i50125711.bml到C:\tmp\
2. sprintf hook: 50125461 → 50125711
3. 在LoadItemFile代码区域查找DFileGPack::Open调用
4. Hook GPack Open, 当查找i50125711.bml时提供预加载数据

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, struct, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'sprintf_pak_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

SRC_IC = 50125461
DST_IC = 50125711

# 游戏资源目录
GAME_DIR = r"C:\Program Files (x86)\T2CN\街头篮球"
BML_OUT = r"C:\tmp\i50125711.bml"


def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_F:
        LOG_F.write(line + '\n')
        LOG_F.flush()


def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None


def extract_bml_from_pak():
    """从res768.pak提取i50125711.bml"""
    # 尝试多个可能的资源子目录
    pak_paths = [
        os.path.join(GAME_DIR, "res768.pak"),
        os.path.join(GAME_DIR, "resource", "res768.pak"),
        os.path.join(GAME_DIR, "data", "res768.pak"),
    ]

    pak_path = None
    for p in pak_paths:
        if os.path.exists(p):
            pak_path = p
            break

    if not pak_path:
        # 搜索整个游戏目录
        for root, dirs, files in os.walk(GAME_DIR):
            if "res768.pak" in files:
                pak_path = os.path.join(root, "res768.pak")
                break

    if not pak_path:
        log(f'  [错误] 找不到res768.pak')
        return False

    log(f'  找到pak: {pak_path}')

    # GPack格式: 文件头包含条目列表, 每个条目有name+offset+size
    with open(pak_path, 'rb') as f:
        data = f.read()

    log(f'  pak大小: {len(data)} bytes')

    # 搜索条目名 "i50125711" 或 "50125711"
    target_names = [b'i50125711', b'50125711']
    found = {}

    for name in target_names:
        offset = 0
        while True:
            pos = data.find(name, offset)
            if pos < 0:
                break
            # 读周围上下文
            ctx_start = max(0, pos - 32)
            ctx = data[ctx_start:pos + 64]
            # 检查是否包含 ".bml"
            end_pos = data.find(b'\x00', pos)
            if end_pos > pos:
                full_name = data[pos:end_pos].decode('ascii', errors='replace')
                if '.bml' in full_name or '.bm' in full_name:
                    log(f'  找到BML条目: "{full_name}" at offset {pos}')
                    found[full_name] = pos
            offset = pos + 1

    if not found:
        log(f'  [错误] 在res768.pak中未找到50125711的BML条目')
        # 列出pak中前20个条目帮助诊断
        log(f'  pak前200字节hex: {data[:200].hex()}')
        return False

    # 提取第一个找到的BML
    bml_name = list(found.keys())[0]
    name_pos = found[bml_name]

    # GPack条目格式: name(变长\0结尾) + offset(4B) + size(4B) 或类似
    # 需要解析实际格式 — 先尝试找到条目数据
    # 在名字后面找offset和size字段
    null_pos = data.find(b'\x00', name_pos)
    entry_start = null_pos + 1

    # 尝试读取offset和size (little-endian uint32)
    if entry_start + 8 <= len(data):
        entry_offset = struct.unpack_from('<I', data, entry_start)[0]
        entry_size = struct.unpack_from('<I', data, entry_start + 4)[0]
        log(f'  条目 offset={entry_offset} size={entry_size}')

        if entry_offset + entry_size <= len(data):
            bml_data = data[entry_offset:entry_offset + entry_size]
            os.makedirs(os.path.dirname(BML_OUT), exist_ok=True)
            with open(BML_OUT, 'wb') as out:
                out.write(bml_data)
            log(f'  已提取到: {BML_OUT} ({len(bml_data)} bytes)')
            return True
        else:
            log(f'  [错误] offset+size超出pak范围')

    # 如果上面的解析不对, 尝试另一种格式
    # 有些GPack格式把条目放在pak末尾, 头部是索引
    # 搜索数据本身: BML是XOR 0xFF编码的, 但也可能是明文XML
    xor_key = 0xFF
    for name in found:
        pos = found[name]
        log(f'  尝试从pak头部解析条目格式...')

        # 尝试: GPack头部可能有固定格式
        # 读pak头部看结构
        header = data[:64]
        log(f'  pak头部: {header.hex()}')

        # 检查是否是GPack格式
        magic = data[:4]
        log(f'  pak magic: {magic}')

    return False


def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== sprintf+PAK双hook === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想) → {DST_IC}(紫色超赛)')

    # Step 1: 提取BML
    log('Step 1: 从res768.pak提取BML...')
    bml_ok = extract_bml_from_pak()

    if not bml_ok:
        log('BML提取失败, 仅执行sprintf替换')
        bml_path = ''
    else:
        bml_path = BML_OUT

    # Step 2: Frida注入
    log(f'日志: {LOG_FILE}')

    BML_PATH_ARG = bml_path.replace('\\', '\\\\')

    JS_CODE = r"""
'use strict';

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;
var BML_PATH = '""" + BML_PATH_ARG + """';

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});

var base = ptr('0x400000');

// ==========================================
// 1. 加载BML数据 (如果提取成功)
// ==========================================
var bmlData = null;
var bmlSize = 0;

if (BML_PATH.length > 0) {
    var crtMod = Process.getModuleByName('msvcrt.dll');
    var _fopen = new NativeFunction(crtMod.getExportByName('fopen'), 'pointer', ['pointer', 'pointer']);
    var _fread = new NativeFunction(crtMod.getExportByName('fread'), 'int', ['pointer', 'int', 'int', 'pointer']);
    var _fclose = new NativeFunction(crtMod.getExportByName('fclose'), 'int', ['pointer']);

    var pathStr = Memory.allocUtf8String(BML_PATH);
    var modeStr = Memory.allocUtf8String('rb');
    var fp = _fopen(pathStr, modeStr);

    if (!fp.isNull()) {
        // 获取文件大小
        var fseek = new NativeFunction(crtMod.getExportByName('fseek'), 'int', ['pointer', 'int', 'int']);
        var ftell = new NativeFunction(crtMod.getExportByName('ftell'), 'int', ['pointer']);
        fseek(fp, 0, 2); // SEEK_END
        bmlSize = ftell(fp);
        fseek(fp, 0, 0); // SEEK_SET

        bmlData = Memory.alloc(bmlSize);
        var totalRead = 0;
        while (totalRead < bmlSize) {
            var chunk = _fread(bmlData.add(totalRead), 1, bmlSize - totalRead, fp);
            if (chunk <= 0) break;
            totalRead += chunk;
        }
        _fclose(fp);

        send({t: 'step', msg: 'BML加载: ' + totalRead + '/' + bmlSize + ' bytes'});
    } else {
        send({t: 'step', msg: 'BML文件无法打开: ' + BML_PATH});
    }
} else {
    send({t: 'step', msg: '无BML数据, 仅sprintf替换模式'});
}

// ==========================================
// 2. sprintf hook — 替换ItemCode
// ==========================================
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
var patchCount = 0;

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0 || fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);
                patchCount++;
                send({t: 'patched', n: patchCount, orig: SRC_IC, new: DST_IC});
            }
        } catch(e) {}
    }
});

// ==========================================
// 3. 搜索LoadItemFile函数区域, 找DFileGPack::Open调用
// ==========================================
// sprintf返回地址0x1AE2563, LoadItemFile在附近
// 先dump该区域的字节, 分析调用模式
var codeArea = base.add(0x1AE2400);
var dumpSize = 0x300; // 768字节
try {
    var codeBytes = new Uint8Array(codeArea.readByteArray(dumpSize));
    var dumpLines = [];
    for (var di = 0; di < dumpSize; di += 16) {
        var hex = '';
        var ascii = '';
        for (var dj = 0; dj < 16 && di + dj < dumpSize; dj++) {
            var b = codeBytes[di + dj];
            hex += ('0' + b.toString(16)).slice(-2) + ' ';
            ascii += (b >= 0x20 && b < 0x7f) ? String.fromCharCode(b) : '.';
        }
        var rva = 0x1AE2400 + di;
        dumpLines.push('0x' + rva.toString(16) + ': ' + hex + ' | ' + ascii);
    }
    send({t: 'code_dump', area: '0x1AE2400', size: dumpSize, lines: dumpLines});
} catch(e) {
    send({t: 'error', msg: 'code dump failed: ' + e});
}

// ==========================================
// 4. AcquireSMD监控
// ==========================================
var acquireCaller = base.add(0x01EEBA30);
var acquireCount = 0;

Interceptor.attach(acquireCaller, {
    onEnter: function(args) {
        try {
            var pathPtr = this.context.ecx.add(0x10).readPointer();
            var path = readAscii(pathPtr, 80);
            acquireCount++;
            if (path.indexOf('50125') >= 0 || acquireCount <= 15) {
                send({t: 'acquire', n: acquireCount, path: path});
            }
        } catch(e) {}
    }
});

send({t: 'ready', msg: 'sprintf+PAK双hook就绪'});

rpc.exports = {
    status: function() {
        return JSON.stringify({patches: patchCount, acquires: acquireCount});
    }
};
"""

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'step':
                log(f'  [步骤] {p["msg"]}')
            elif t == 'ready':
                log(f'  {p["msg"]}')
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]} {p["orig"]}→{p["new"]}')
            elif t == 'acquire':
                log(f'  [AcquireSMD] #{p["n"]} path="{p["path"]}"')
            elif t == 'code_dump':
                log(f'  [代码dump] area={p["area"]} size={p["size"]}')
                for line in p['lines'][:50]:
                    log(f'    {line}')
                if len(p['lines']) > 50:
                    log(f'    ... ({len(p["lines"])-50} more lines)')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('进房间触发角色加载。')
    log('命令: status | quit')
    log('')

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'status':
                log(f'  {script.exports_sync.status()}')
    except (KeyboardInterrupt, EOFError):
        pass

    script.unload()
    session.detach()
    if LOG_F:
        LOG_F.close()
    print('已断开。')


if __name__ == '__main__':
    main()

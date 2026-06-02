"""
hook_xref_diag.py — 搜索格式串交叉引用，定位SetCharacterFeature

策略:
  1. 在.text段搜索 push 0x062A1680 ("customize\item\i%d.xml"的绝对地址)
     x86 push imm32 = 68 xx xx xx xx → 搜索 "80 16 6a 02" (0x062A1680 LE)
  2. 同时搜索 mov reg, 0x062A1680 → B8- BF xx xx xx xx
  3. 找到引用点后，回溯找函数入口 (找前一个 CC 55 8B EC 或 CC 83 EC)
  4. Hook该函数，捕获参数，定位ItemCode

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'xref_diag_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

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

JS_CODE = r"""
'use strict';

function readAscii(buf, maxLen) {
    var s = '';
    for (var i = 0; i < maxLen; i++) {
        var c = buf.add(i).readU8();
        if (c === 0) break;
        s += String.fromCharCode(c);
    }
    return s;
}

function readHex(buf, len) {
    var s = '';
    var bytes = new Uint8Array(buf.readByteArray(len));
    for (var i = 0; i < bytes.length; i++) {
        s += ('0' + bytes[i].toString(16)).slice(-2) + ' ';
    }
    return s;
}

send({t: 'step', msg: 'JS开始执行'});

var base = ptr('0x400000');
var mod = Process.getModuleByName('FreeStyle.exe');

// 格式串绝对地址
var fmtItemAddr = base.add(0x22a1680);  // "customize\item\i%d.xml"
var fmtFaceAddr = base.add(0x22a1698);  // "customize\item\c%d.xml"
send({t: 'step', msg: '格式串地址: item=' + fmtItemAddr + ' face=' + fmtFaceAddr});

// 验证字符串内容
send({t: 'step', msg: 'item格式串: "' + readAscii(fmtItemAddr, 40) + '"'});
send({t: 'step', msg: 'face格式串: "' + readAscii(fmtFaceAddr, 40) + '"'});

// ==========================================
// 1. 搜索 .text 段中的交叉引用
// ==========================================
var sections = mod.enumerateSections();
var textRange = null;
for (var si = 0; si < sections.length; si++) {
    if (sections[si].name === '.text') {
        textRange = {base: sections[si].address, size: sections[si].size};
        send({t: 'step', msg: '.text: base=' + sections[si].address + ' size=' + sections[si].size});
        break;
    }
}

if (!textRange) {
    // 回退: 用整个模块
    textRange = {base: mod.base, size: mod.size};
    send({t: 'step', msg: '.text未找到, 使用整个模块'});
}

// 搜索地址的字节模式
// 编译器可能用 push(68), mov B8-BF, 或其他方式加载地址
// 策略: 只搜地址本身(4字节LE), 找到后检查前一字节判断指令类型
// 0x062A1680 → 80 16 2a 06
// 0x062A1698 → 98 16 2a 06
// 0x062BC764 → 64 c7 2b 06  (i%4d.xml版本)
var patterns = [
    {name: 'item_fmt_id', addr: '80 16 2a 06', desc: 'i%d.xml'},
    {name: 'face_fmt_id', addr: '98 16 2a 06', desc: 'c%d.xml'},
    {name: 'item_fmt_4d', addr: '64 c7 2b 06', desc: 'i%4d.xml'},
];

var xrefResults = [];

for (var pi = 0; pi < patterns.length; pi++) {
    var pat = patterns[pi];
    try {
        var matches = Memory.scanSync(textRange.base, textRange.size, pat.addr);
        for (var mi = 0; mi < matches.length; mi++) {
            var addr = matches[mi].address;
            var rva = addr.sub(base).toInt32();
            var prevByte = addr.sub(1).readU8();
            var instrType = '0x' + prevByte.toString(16);
            if (prevByte === 0x68) instrType += '(push)';
            else if (prevByte >= 0xB8 && prevByte <= 0xBF) instrType += '(mov)';
            else if (prevByte === 0x05) instrType += '(add eax)';

            var ctx = '';
            try { ctx = readHex(addr.sub(4), 16); } catch(e) {}

            send({t: 'xref', name: pat.name, desc: pat.desc,
                  rva: '0x' + rva.toString(16), instr: instrType, ctx: ctx});
            xrefResults.push({name: pat.name, rva: rva, addr: addr, instr: instrType});
        }
    } catch(e) {
        send({t: 'error', msg: '搜索' + pat.name + ': ' + e});
    }
}

send({t: 'step', msg: 'xref搜索完成, 共 ' + xrefResults.length + ' 处'});

// ==========================================
// 2. 对每个xref, 回溯找函数入口
// ==========================================
for (var xi = 0; xi < xrefResults.length; xi++) {
    var xref = xrefResults[xi];
    // 从xref地址向上搜索, 找函数入口模式
    var searchStart = xref.addr.sub(0x200); // 往前搜索512字节
    if (searchStart.compare(base) < 0) searchStart = base;
    var searchSize = xref.addr.sub(searchStart).toInt32();

    // 先搜 "55 8b ec" (push ebp; mov ebp, esp), 取最后一个匹配
    try {
        var prologueMatches = Memory.scanSync(searchStart, searchSize, '55 8b ec');
        if (prologueMatches.length > 0) {
            var entryAddr = prologueMatches[prologueMatches.length - 1].address;
            var entryRva = entryAddr.sub(base).toInt32();
            send({t: 'func_entry', for_rva: '0x' + xref.rva.toString(16),
                  entry: entryAddr.toString(), entry_rva: '0x' + entryRva.toString(16),
                  distance: xref.addr.sub(entryAddr).toInt32()});
            xref.funcEntry = entryAddr;
            xref.funcRva = entryRva;
        }
    } catch(e) {}
}

// ==========================================
// 3. Hook找到的函数, 捕获参数
// ==========================================
// 收集所有唯一的函数入口
var uniqueEntries = {};
for (var xi = 0; xi < xrefResults.length; xi++) {
    if (xrefResults[xi].funcEntry) {
        uniqueEntries[xrefResults[xi].funcRva] = xrefResults[xi];
    }
}

var entryKeys = Object.keys(uniqueEntries);
send({t: 'step', msg: '找到 ' + entryKeys.length + ' 个唯一函数入口'});

for (var ei = 0; ei < entryKeys.length; ei++) {
    var entry = uniqueEntries[entryKeys[ei]];
    var hookAddr = entry.funcEntry;

    (function(hAddr, hName, hRva) {
        try {
            Interceptor.attach(hAddr, {
                onEnter: function(args) {
                    // 捕获调用栈
                    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                    var btStrs = [];
                    for (var bi = 0; bi < bt.length; bi++) {
                        var rva = bt[bi].sub(base).toInt32();
                        btStrs.push('0x' + rva.toString(16));
                    }

                    // 尝试读取栈上的参数 (thiscall: ecx=this, 栈上args)
                    // SetCharacterFeature签名: (int iType, DAnimation*, int iFaceID, list<int>&)
                    // 栈布局(从esp算): +04=retaddr, +08=iType, +0C=pAnimation, +10=iFaceID, +14=pItemList
                    var esp = this.context.esp;
                    var stackDump = '';
                    try {
                        stackDump = readHex(esp.add(4), 32); // retaddr + 7个参数
                    } catch(e2) {}

                    send({t: 'func_call', name: hName, rva: '0x' + hRva.toString(16),
                          ecx: this.context.ecx.toString(),
                          stack: stackDump,
                          backtrace: btStrs});

                    // 如果栈上有50125461相关值, 标记
                    try {
                        for (var si = 0; si < 16; si++) {
                            var val = esp.add(4 + si * 4).readU32();
                            if (val === 50125461) {
                                send({t: 'itemcode_found', name: hName,
                                      stack_offset: '+0x' + (4 + si * 4).toString(16),
                                      value: val});
                            }
                        }
                    } catch(e3) {}
                }
            });
            send({t: 'hook_ok', name: hName, rva: '0x' + hRva.toString(16)});
        } catch(e) {
            send({t: 'hook_fail', name: hName, rva: '0x' + hRva.toString(16), error: e.toString()});
        }
    })(hookAddr, entry.name, entry.funcRva);
}

// ==========================================
// 4. Hook sprintf (MSVCR100 + msvcrt 都hook)
// ==========================================
var sprintfAddrs = [];
try {
    var msvcr100 = Process.getModuleByName('MSVCR100.dll');
    sprintfAddrs.push({name: 'MSVCR100', addr: msvcr100.getExportByName('sprintf')});
} catch(e) {}
try {
    var msvcrtMod = Process.getModuleByName('msvcrt.dll');
    sprintfAddrs.push({name: 'msvcrt', addr: msvcrtMod.getExportByName('sprintf')});
} catch(e) {}

for (var si = 0; si < sprintfAddrs.length; si++) {
    send({t: 'step', msg: sprintfAddrs[si].name + ' sprintf=' + sprintfAddrs[si].addr});
}

var sprintfCount = 0;
for (var si = 0; si < sprintfAddrs.length; si++) {
    (function(spInfo) {
        try {
            Interceptor.attach(spInfo.addr, {
                onEnter: function(args) {
                    try {
                        var fmt = readAscii(args[1], 40);
                        if (fmt.indexOf('customize') >= 0 && fmt.indexOf('item') >= 0) {
                            var itemCode = args[2].toInt32();
                            var bt = Thread.backtrace(this.context, Backtracer.ACCURATE);
                            var btStrs = [];
                            for (var bi = 0; bi < bt.length; bi++) {
                                var rva = bt[bi].sub(base).toInt32();
                                btStrs.push('0x' + rva.toString(16));
                            }
                            sprintfCount++;
                            send({t: 'sprintf_item', n: sprintfCount,
                                  source: spInfo.name, fmt: fmt,
                                  itemCode: itemCode, backtrace: btStrs});
                        }
                    } catch(e) {}
                }
            });
            send({t: 'step', msg: spInfo.name + ' sprintf hook OK'});
        } catch(e) {
            send({t: 'step', msg: spInfo.name + ' sprintf hook失败: ' + e});
        }
    })(sprintfAddrs[si]);
}

send({t: 'ready', msg: 'xref诊断就绪 — 格式串交叉引用 + sprintf hook'});

rpc.exports = {
    status: function() {
        return JSON.stringify({sprintfCount: sprintfCount});
    }
};
"""


def main():
    global LOG_F

    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    LOG_F = open(LOG_FILE, 'w', encoding='utf-8')
    log(f'=== xref定位SetCharacterFeature === PID:{pid} ===')
    log(f'日志: {LOG_FILE}')

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
            elif t == 'xref':
                log(f'  [xref] {p["name"]}: RVA={p["rva"]} 指令={p["instr"]} ctx={p["ctx"]}')
            elif t == 'func_entry':
                log(f'  [函数入口] 引用RVA={p["for_rva"]} → 入口={p["entry"]} (RVA={p["entry_rva"]}) 距离={p["distance"]}B')
            elif t == 'hook_ok':
                log(f'  [Hook成功] {p["name"]} RVA={p["rva"]}')
            elif t == 'hook_fail':
                log(f'  [Hook失败] {p["name"]} RVA={p["rva"]}: {p["error"]}')
            elif t == 'func_call':
                log(f'  [函数调用] {p["name"]} RVA={p["rva"]} ecx={p["ecx"]}')
                log(f'    栈: {p["stack"]}')
                for i, addr in enumerate(p['backtrace'][:8]):
                    log(f'    bt[{i}] {addr}')
            elif t == 'itemcode_found':
                log(f'  [ItemCode命中!] {p["name"]} 栈偏移={p["stack_offset"]} 值={p["value"]}')
            elif t == 'sprintf_item':
                log(f'  [sprintf] #{p["n"]} fmt="{p["fmt"]}" ItemCode={p["itemCode"]}')
                for i, addr in enumerate(p['backtrace'][:10]):
                    log(f'    bt[{i}] {addr}')
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

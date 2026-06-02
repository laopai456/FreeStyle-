"""
hook_sprintf_minimal.py — 最小化 sprintf 替换测试
只 hook MSVCR100.dll!sprintf（系统 DLL，安全）
不加任何游戏 .text 段 hook，避免 Apollo 检测

目的: 测试静态→静态替换进练习场是否保持发型

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, json, frida
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'sprintf_minimal_{time.strftime("%Y%m%d_%H%M%S")}.txt')
LOG_F = None

# 美丽梦想(静态) → 黑金热血(静态)
SRC_IC = 50125461  # 美丽梦想发型 (pak767, 静态)
DST_IC = 50125691  # 黑金热血发型 (pak768, 静态) - 同类型

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

var SRC_IC = """ + str(SRC_IC) + """;
var DST_IC = """ + str(DST_IC) + """;

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

var patchCount = 0;
var totalItemSprintf = 0;

// 只 Hook MSVCR100 sprintf (系统DLL，安全)
var msvcr100 = Process.getModuleByName('MSVCR100.dll');
var sprintfAddr = msvcr100.getExportByName('sprintf');
send({t: 'step', msg: 'MSVCR100 sprintf=' + sprintfAddr});

Interceptor.attach(sprintfAddr, {
    onEnter: function(args) {
        try {
            // args[0]=buf, args[1]=fmt, args[2]=ItemCode
            var fmt = readAscii(args[1], 50);
            if (fmt.indexOf('customize') < 0) return;
            if (fmt.indexOf('item') < 0) return;

            var itemCode = args[2].toInt32();
            totalItemSprintf++;

            if (totalItemSprintf <= 200) {
                send({t: 'sprintf', n: totalItemSprintf, fmt: fmt, itemCode: itemCode});
            }

            // 替换目标ItemCode
            if (itemCode === SRC_IC) {
                args[2] = ptr(DST_IC);  // 改sprintf参数

                // 关键: 同时改[ebp-0xD8]，使LoadItemFile也拿到替换后的ItemCode
                var callerEbp = this.context.ebp;
                callerEbp.sub(0xD8).writeU32(DST_IC);

                patchCount++;
                send({t: 'patched', n: patchCount, orig: SRC_IC, new: DST_IC,
                      fmt: fmt, result_preview: 'i' + DST_IC + '.xml'});
            }
        } catch(e) {
            send({t: 'error', msg: 'sprintf hook: ' + e});
        }
    }
});

send({t: 'ready', msg: '最小化 sprintf 替换就绪: ' + SRC_IC + ' → ' + DST_IC});

rpc.exports = {
    status: function() {
        return JSON.stringify({
            patches: patchCount,
            totalSprintf: totalItemSprintf
        });
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
    log(f'=== 最小化 sprintf 替换测试 === PID:{pid} ===')
    log(f'替换: {SRC_IC}(美丽梦想发型,静态) → {DST_IC}(黑金热血发型,静态)')
    log(f'特点: 只 hook 系统DLL，不加游戏.text hook')
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
            elif t == 'sprintf':
                log(f'  [sprintf] #{p["n"]} fmt="{p["fmt"]}" IC={p["itemCode"]}')
            elif t == 'patched':
                log(f'  [替换!] #{p["n"]} {p["orig"]}→{p["new"]} → {p["result_preview"]}')
            elif t == 'error':
                log(f'  [错误] {p["msg"]}')
            else:
                log(f'  {json.dumps(p, ensure_ascii=False)[:200]}')
        elif msg['type'] == 'error':
            log(f'  [JS错误] {msg.get("description","")} 行{msg.get("lineNumber","")}')

    script.on('message', on_msg)
    script.load()

    log('')
    log('测试流程:')
    log('1. 进房间 → 观察发型是否为黑金热血')
    log('2. 进练习场 → 观察发型是否保持')
    log('3. 退出练习场 → 观察发型是否恢复')
    log('')
    log('命令: status | quit')

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
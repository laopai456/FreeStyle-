"""
hook_codepatch.py — 代码补丁方案，零Interceptor
直接用Memory.patchCode修改SetCharacterFeature中的3条ItemCode加载指令
将[ebp-0xD8]读取改为硬编码50125711，不创建trampoline

补丁点 (base=0x400000):
  0x1AE254B: mov edx,[ebp-0xD8] → mov edx, 50125711  (sprintf用)
  0x1AE2568: mov ecx,[ebp-0xDC] → mov ecx, 50125711  (LoadItemFile arg0)
  0x1AE2576: mov eax,[ebp-0xD8] → mov eax, 50125711  (LoadItemFile arg)

注意: 这只覆盖sprintf路径。练习场的第二条路径需要额外处理。

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, frida, json
sys.stdout.reconfigure(encoding='utf-8')

SRC_IC = 50125461  # 美丽梦想发型 (pak767)
DST_IC = 50125711  # 紫色超赛发型 (pak768)

def find_pid():
    import psutil
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and p.info['name'].lower() == 'freestyle.exe':
            return p.info['pid']
    return None

JS_CODE = r"""
'use strict';

var base = ptr('0x400000');
var DST_IC = """ + str(DST_IC) + """;
var SRC_IC = """ + str(SRC_IC) + """;

// 异常处理器 — 传递Apollo的断点
Process.setExceptionHandler(function(details) {
    return false;
});

// ==========================================
// 代码补丁: 硬编码ItemCode
// ==========================================

// DST_IC = 50125711 = 0x02FD6E5F
// Little-endian bytes: 5F 6E FD 02
var dstLe = [0x5F, 0x6E, 0xFD, 0x02];

function applyCodePatches() {
    var results = [];

    // 验证原始字节 — 只patch [ebp-0xD8] 的两条指令
    var p1 = base.add(0x1AE254B);  // mov edx, [ebp-0xD8] → sprintf用
    var orig1 = new Uint8Array(p1.readByteArray(6));
    var expected1 = [0x8B, 0x95, 0x28, 0xFF, 0xFF, 0xFF];
    var match1 = true;
    for (var i = 0; i < 6; i++) { if (orig1[i] !== expected1[i]) match1 = false; }

    var p2 = base.add(0x1AE2576);  // mov eax, [ebp-0xD8] → LoadItemFile用
    var orig2 = new Uint8Array(p2.readByteArray(6));
    var expected2 = [0x8B, 0x85, 0x28, 0xFF, 0xFF, 0xFF];
    var match2 = true;
    for (var i = 0; i < 6; i++) { if (orig2[i] !== expected2[i]) match2 = false; }

    results.push('Patch1 0x1AE254B (sprintf): ' + (match1 ? 'MATCH' : 'MISMATCH ' + toHex(orig1)));
    results.push('Patch2 0x1AE2576 (LoadItemFile): ' + (match2 ? 'MATCH' : 'MISMATCH ' + toHex(orig2)));

    if (!match1 || !match2) {
        return {ok: false, results: results};
    }

    // 应用补丁: mov reg, [ebp-0xD8] → mov reg, DST_IC + NOP
    Memory.patchCode(p1, 6, function(code) {
        code.writeU8(0xBA);           // mov edx, imm32
        code.writeU32(DST_IC);
        code.writeU8(0x90);           // nop
    });

    Memory.patchCode(p2, 6, function(code) {
        code.writeU8(0xB8);           // mov eax, imm32
        code.writeU32(DST_IC);
        code.writeU8(0x90);           // nop
    });

    results.push('2个代码补丁已应用!');

    // 验证补丁
    var v1 = new Uint8Array(p1.readByteArray(6));
    var v2 = new Uint8Array(p2.readByteArray(6));
    results.push('Verify1: ' + toHex(v1));
    results.push('Verify2: ' + toHex(v2));

    return {ok: true, results: results};
}

function toHex(arr) {
    var s = '';
    for (var i = 0; i < arr.length; i++) {
        s += ('0' + arr[i].toString(16)).slice(-2) + ' ';
    }
    return s.trim();
}

// ==========================================
// LoadItemFile hook — 覆盖练习场第二条路径
// 只hook这一个函数, 一次性patch后自动detach
// ==========================================
var lifAddr = base.add(0x1ACE1C0);
var lifListener = null;
var lifPatchCount = 0;

function hookLif() {
    if (lifListener) return false;
    lifListener = Interceptor.attach(lifAddr, {
        onEnter: function(args) {
            var ic = args[0].toInt32();
            if (ic === SRC_IC) {
                args[0] = ptr(DST_IC);
                var dstStr = DST_IC.toString();
                for (var j = 0; j < dstStr.length; j++) {
                    args[1].add(16 + j).writeU8(dstStr.charCodeAt(j));
                }
                lifPatchCount++;
                send({t: 'lif_patched', n: lifPatchCount});
            }
        }
    });
    return true;
}

function unhookLif() {
    if (!lifListener) return false;
    try { lifListener.detach(); } catch(e) {}
    lifListener = null;
    return true;
}

rpc.exports = {
    patch: function() {
        return JSON.stringify(applyCodePatches());
    },
    hookLif: function() {
        return hookLif();
    },
    unhookLif: function() {
        return unhookLif();
    },
    status: function() {
        return JSON.stringify({
            lifHooked: lifListener !== null,
            lifPatches: lifPatchCount
        });
    }
};

send({t: 'ready', msg: '代码补丁就绪'});
"""


def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    print(f'PID: {pid}')
    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    def on_msg(msg, data):
        if msg['type'] == 'send':
            p = msg['payload']
            t = p.get('t', '')
            if t == 'ready':
                print(f'  {p["msg"]}')
            elif t == 'lif_patched':
                print(f'  [LoadItemFile替换] #{p["n"]}')
            else:
                print(f'  {p}')
        elif msg['type'] == 'error':
            print(f'  [JS错误] {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()

    print()
    print('命令:')
    print('  patch    — 应用代码补丁 (sprintf+LoadItemFile路径)')
    print('  hooklif  — 挂钩LoadItemFile (练习场路径)')
    print('  unhooklif— 脱离LoadItemFile')
    print('  status   — 状态')
    print('  quit')
    print()
    print('流程:')
    print('  1. patch → 进房间 → 看到紫色发型')
    print('  2. hooklif → 进练习场 → 看到紫色发型 → unhooklif')
    print()

    try:
        while True:
            cmd = input('> ').strip().lower()
            if cmd in ('quit', 'q', 'exit'):
                break
            elif cmd == 'patch':
                result = json.loads(script.exports_sync.patch())
                for line in result.get('results', []):
                    print(f'  {line}')
                print(f'  结果: {"成功" if result.get("ok") else "失败"}')
            elif cmd == 'hooklif':
                r = script.exports_sync.hook_lif()
                print(f'  LoadItemFile hook: {"已设置" if r else "已存在"}')
            elif cmd == 'unhooklif':
                r = script.exports_sync.unhook_lif()
                print(f'  LoadItemFile hook: {"已脱离" if r else "未挂钩"}')
            elif cmd == 'status':
                st = json.loads(script.exports_sync.status())
                print(f'  lifHooked={st["lifHooked"]} lifPatches={st["lifPatches"]}')
    except (KeyboardInterrupt, EOFError):
        pass

    try:
        script.exports_sync.unhook_lif()
    except:
        pass
    script.unload()
    session.detach()
    print('已断开。')


if __name__ == '__main__':
    main()

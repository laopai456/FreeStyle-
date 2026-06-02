"""
patch_and_detach.py — 打补丁后立即脱离Frida
1. Attach Frida
2. 用Memory.patchCode修改2条指令
3. 立即detach Frida
4. 游戏继续运行，没有Frida痕迹

补丁:
  0x1AE254B: mov edx,[ebp-0xD8] → mov edx,50125711 (sprintf ItemCode)
  0x1AE2576: mov eax,[ebp-0xD8] → mov eax,50125711 (LoadItemFile ItemCode)

前置: sc.exe stop ApolloProtect
"""
import sys, os, time, frida, json
sys.stdout.reconfigure(encoding='utf-8')

DST_IC = 50125711  # 紫色超赛发型

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

var p1 = base.add(0x1AE254B);  // mov edx, [ebp-0xD8]
var p2 = base.add(0x1AE2576);  // mov eax, [ebp-0xD8]

// 验证原始字节
var o1 = new Uint8Array(p1.readByteArray(6));
var o2 = new Uint8Array(p2.readByteArray(6));
var e1 = [0x8B, 0x95, 0x28, 0xFF, 0xFF, 0xFF];
var e2 = [0x8B, 0x85, 0x28, 0xFF, 0xFF, 0xFF];
var ok1 = true, ok2 = true;
for (var i = 0; i < 6; i++) {
    if (o1[i] !== e1[i]) ok1 = false;
    if (o2[i] !== e2[i]) ok2 = false;
}

if (!ok1 || !ok2) {
    var s = '';
    for (var i = 0; i < 6; i++) s += ('0'+o1[i].toString(16)).slice(-2)+' ';
    s += ' | ';
    for (var i = 0; i < 6; i++) s += ('0'+o2[i].toString(16)).slice(-2)+' ';
    send({t: 'mismatch', bytes: s});
} else {
    // 打补丁: mov reg, [ebp-0xD8] → mov reg, DST_IC + NOP
    Memory.patchCode(p1, 6, function(code) {
        code.writeU8(0xBA);
        code.writeU32(DST_IC);
        code.writeU8(0x90);
    });
    Memory.patchCode(p2, 6, function(code) {
        code.writeU8(0xB8);
        code.writeU32(DST_IC);
        code.writeU8(0x90);
    });

    // 验证
    var v1 = new Uint8Array(p1.readByteArray(6));
    var v2 = new Uint8Array(p2.readByteArray(6));
    var s1 = '', s2 = '';
    for (var i = 0; i < 6; i++) {
        s1 += ('0'+v1[i].toString(16)).slice(-2)+' ';
        s2 += ('0'+v2[i].toString(16)).slice(-2)+' ';
    }
    send({t: 'patched', v1: s1, v2: s2});
}
"""


def main():
    pid = find_pid()
    if not pid:
        print('FreeStyle.exe 未运行')
        return

    print(f'PID: {pid}')
    print('打补丁中...')

    session = frida.attach(pid)
    script = session.create_script(JS_CODE)

    result = [None]

    def on_msg(msg, data):
        if msg['type'] == 'send':
            result[0] = msg['payload']
        elif msg['type'] == 'error':
            print(f'JS错误: {msg.get("description","")}')

    script.on('message', on_msg)
    script.load()
    time.sleep(0.5)

    # 立即脱离Frida
    script.unload()
    session.detach()

    r = result[0]
    if r and r.get('t') == 'patched':
        print(f'补丁成功!')
        print(f'  0x1AE254B: {r["v1"]}')
        print(f'  0x1AE2576: {r["v2"]}')
    elif r and r.get('t') == 'mismatch':
        print(f'字节不匹配: {r["bytes"]}')
    else:
        print(f'结果: {r}')

    print('Frida已脱离。进房间测试。')
    print('注意: 这只覆盖sprintf路径，练习场第二条路径需要LoadItemFile替换。')


if __name__ == '__main__':
    main()

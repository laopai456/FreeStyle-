"""
find_ic_in_obj.py — Hook 包构造函数, 搜索 this 对象中的 ItemCode

策略:
1. Hook 0x1922720 (包构造函数)
2. 触发时 dump ecx (this) 对象的内存
3. 搜索已知的背包 ItemCode (50122721 = 粉色网红主播)
4. 找到后报告偏移量

用法:
  1. 游戏运行中, 运行: py find_ic_in_obj.py
  2. 在游戏中装备/脱下 粉色网红主播发型
  3. 脚本自动捕获并报告 ItemCode 偏移

按 Ctrl+C 退出
"""
import frida, json, sys, struct, time

# 已知的背包 ItemCode
KNOWN_IC = 50122721  # 粉色网红主播发型

JS = r"""
'use strict';

var g_hooked = false;
var g_targetIC = """ + str(KNOWN_IC) + r""";

function hookPacketBuilder() {
    if (g_hooked) return;
    var pktBuilder = ptr(0x1922720);

    Interceptor.attach(pktBuilder, {
        onEnter: function(args) {
            // ecx = this pointer (game state object)
            var thisPtr = this.context.ecx;
            if (thisPtr.isNull()) return;

            // 搜索 this 对象内存中的 target ItemCode
            var needle = [];
            var ic = g_targetIC;
            for (var b = 0; b < 4; b++) {
                needle.push((ic >> (b * 8)) & 0xff);
            }

            var hits = [];
            try {
                // 扫描 this 对象前 0x2000 字节
                for (var off = 0; off < 0x2000; off += 4) {
                    try {
                        var val = thisPtr.add(off).readU32();
                        if (val === g_targetIC) {
                            hits.push({offset: off, addr: thisPtr.add(off).toString()});
                        }
                    } catch(e) {}
                }
            } catch(e) {}

            if (hits.length > 0) {
                var hitInfo = [];
                for (var i = 0; i < hits.length; i++) {
                    // 读取命中位置周围的上下文
                    var ctx = [];
                    for (var j = -8; j <= 8; j += 4) {
                        try {
                            ctx.push('+' + (hits[i].offset + j) + '=0x' + thisPtr.add(hits[i].offset + j).readU32().toString(16));
                        } catch(e) {
                            ctx.push('err');
                        }
                    }
                    hitInfo.push({offset: hits[i].offset, context: ctx.join(' ')});
                }
                send(JSON.stringify({
                    type: 'IC_HIT',
                    thisPtr: thisPtr.toString(),
                    ic: g_targetIC,
                    hits: hitInfo
                }));
            }

            // 也搜索 this 指针指向的子对象 (通过指针解引用)
            var ptrHits = [];
            for (var off = 0; off < 0x1000; off += 4) {
                try {
                    var subPtr = thisPtr.add(off).readPointer();
                    if (subPtr.isNull()) continue;
                    // 在子对象中搜索
                    for (var subOff = 0; subOff < 0x200; subOff += 4) {
                        try {
                            var val = subPtr.add(subOff).readU32();
                            if (val === g_targetIC) {
                                ptrHits.push({
                                    ptrOffset: off,
                                    subOffset: subOff,
                                    ptrAddr: subPtr.toString(),
                                    totalOffset: '+' + off.toString(16) + ' -> +' + subOff.toString(16)
                                });
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
            }

            if (ptrHits.length > 0) {
                send(JSON.stringify({
                    type: 'IC_PTR_HIT',
                    thisPtr: thisPtr.toString(),
                    ic: g_targetIC,
                    hits: ptrHits
                }));
            }
        }
    });
    g_hooked = true;
    send(JSON.stringify({type:'info', msg:'Hooked packet builder 0x1922720, searching for IC=' + g_targetIC}));
}

rpc.exports = {
    setic: function(ic) {
        g_targetIC = parseInt(ic);
        return JSON.stringify({ok: true, ic: g_targetIC});
    }
};

hookPacketBuilder();
""";

def main():
    pid = None
    if len(sys.argv) >= 2:
        pid = int(sys.argv[1])
    else:
        import subprocess
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                           capture_output=True, text=True)
        for line in r.stdout.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].isdigit():
                pid = int(parts[1])
                break

    if not pid:
        print("FreeStyle.exe not found")
        return

    print(f"PID={pid}")
    print(f"Searching for ItemCode {KNOWN_IC} (0x{KNOWN_IC:08X})")
    print("Now equip/unequip the item in-game. Press Ctrl+C to stop.\n")

    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}")
            return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except:
                print(f"  {p}")
                return
        t = p.get('type', '')
        if t == 'IC_HIT':
            print(f"\n  === ItemCode FOUND in this object! ===")
            print(f"  this = {p['thisPtr']}")
            print(f"  IC = {p['ic']} (0x{p['ic']:08X})")
            for h in p['hits']:
                print(f"  Offset +0x{h['offset']:X}  context: {h['context']}")
            print()
        elif t == 'IC_PTR_HIT':
            print(f"\n  === ItemCode FOUND via pointer! ===")
            print(f"  this = {p['thisPtr']}")
            for h in p['hits']:
                print(f"  this+0x{h['ptrOffset']:X} -> ptr {h['ptrAddr']} +0x{h['subOffset']:X}  ({h['totalOffset']})")
            print()
        elif t == 'info':
            print(f"  [*] {p['msg']}")
        else:
            print(f"  [{t}] {p}")

    script.on('message', on_message)
    script.load()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print("\nDone.")

if __name__ == '__main__':
    main()

"""
find_ic_equip.py — Hook 真装备函数 0x19247a0, 深度搜索 ItemCode

策略:
1. Hook 0x19247a0 (无 __chkstk, 应该安全)
2. 在 this 对象中搜索 ItemCode (直接 + 指针链 3 级)
3. 也搜索 float 参数转换后的值

用法: py find_ic_equip.py
  装备粉色网红主播 (50122721), 脚本报告所有命中
"""
import frida, json, sys, time

KNOWN_IC = 50122721

JS = r"""
'use strict';

var g_targetIC = """ + str(KNOWN_IC) + r""";

var equipFn = ptr(0x19247a0);
var g_hooked = false;

function hookEquip() {
    if (g_hooked) return;
    Interceptor.attach(equipFn, {
        onEnter: function(args) {
            var thisPtr = this.context.ecx;
            if (thisPtr.isNull()) return;

            // 读取 3 个 float 参数
            var arg1 = this.context.esp.add(4).readFloat();
            var arg2 = this.context.esp.add(8).readFloat();
            var arg3 = this.context.esp.add(12).readFloat();
            var intArg1 = arg1 | 0;
            var intArg2 = arg2 | 0;

            send(JSON.stringify({
                type: 'EQUIP_CALL',
                thisPtr: thisPtr.toString(),
                arg1_float: arg1,
                arg2_float: arg2,
                arg3_float: arg3,
                arg1_int: intArg1,
                arg2_int: intArg2,
                ic_at_e34: thisPtr.add(0xE34).readU32()
            }));

            // 深度搜索 ItemCode
            // Level 0: 直接搜索 this 对象
            var hits = [];
            for (var off = 0; off < 0x2000; off += 4) {
                try {
                    var val = thisPtr.add(off).readU32();
                    if (val === g_targetIC) {
                        hits.push({level: 0, offset: off});
                    }
                } catch(e) {}
            }

            // Level 1: this -> ptr -> 搜索
            for (var off = 0; off < 0x1000; off += 4) {
                try {
                    var subPtr = thisPtr.add(off).readPointer();
                    if (subPtr.isNull() || subPtr.compare(ptr(0x10000)) < 0) continue;
                    for (var subOff = 0; subOff < 0x400; subOff += 4) {
                        try {
                            var val = subPtr.add(subOff).readU32();
                            if (val === g_targetIC) {
                                hits.push({level: 1, ptrOff: off, subOff: subOff,
                                           ptrAddr: subPtr.toString()});
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
            }

            // Level 2: this -> ptr -> ptr -> 搜索
            for (var off = 0; off < 0x800; off += 4) {
                try {
                    var p1 = thisPtr.add(off).readPointer();
                    if (p1.isNull() || p1.compare(ptr(0x10000)) < 0) continue;
                    for (var sub1 = 0; sub1 < 0x200; sub1 += 4) {
                        try {
                            var p2 = p1.add(sub1).readPointer();
                            if (p2.isNull() || p2.compare(ptr(0x10000)) < 0) continue;
                            for (var sub2 = 0; sub2 < 0x200; sub2 += 4) {
                                try {
                                    var val = p2.add(sub2).readU32();
                                    if (val === g_targetIC) {
                                        hits.push({level: 2, off1: off, off2: sub1, off3: sub2,
                                                   p1: p1.toString(), p2: p2.toString()});
                                    }
                                } catch(e) {}
                            }
                        } catch(e) {}
                    }
                } catch(e) {}
            }

            if (hits.length > 0) {
                send(JSON.stringify({type: 'IC_HITS', count: hits.length, hits: hits}));
            } else {
                send(JSON.stringify({type: 'IC_NOT_FOUND'}));
            }
        }
    });
    g_hooked = true;
    send(JSON.stringify({type:'info', msg:'Hooked 0x19247a0 (real equip fn), IC=' + g_targetIC}));
}

hookEquip();
""";

def main():
    pid = None
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            pid = int(parts[1])
            break
    if not pid:
        print("FreeStyle.exe not found"); return

    print(f"PID={pid}  Searching for IC={KNOWN_IC} (0x{KNOWN_IC:08X})")
    print("Hooked 0x19247a0. Equip item now. Ctrl+C to stop.\n")

    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg['type'] != 'send':
            print(f"  [FRIDA] {msg}"); return
        p = msg['payload']
        if isinstance(p, str):
            try: p = json.loads(p)
            except: print(f"  {p}"); return
        t = p.get('type', '')
        if t == 'EQUIP_CALL':
            print(f"  EQUIP this={p['thisPtr']}  arg1={p['arg1_float']}({p['arg1_int']})  arg2={p['arg2_float']}({p['arg2_int']})  arg3={p['arg3_float']}")
            print(f"    +0xE34 = 0x{p['ic_at_e34']:08X}")
        elif t == 'IC_HITS':
            print(f"\n  === {p['count']} ItemCode HITS ===")
            for h in p['hits']:
                lv = h['level']
                if lv == 0:
                    print(f"    L0 this+0x{h['offset']:X}")
                elif lv == 1:
                    print(f"    L1 this+0x{h['ptrOff']:X} -> {h['ptrAddr']} +0x{h['subOff']:X}")
                elif lv == 2:
                    print(f"    L2 this+0x{h['off1']:X} -> {h['p1']} +0x{h['off2']:X} -> {h['p2']} +0x{h['off3']:X}")
            print()
        elif t == 'IC_NOT_FOUND':
            print(f"  ItemCode NOT found in 3-level search!")
        elif t == 'info':
            print(f"  [*] {p['msg']}")
        else:
            print(f"  [{t}] {p}")

    script.on('message', on_message)
    script.load()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
    try: script.unload()
    except: pass
    try: session.detach()
    except: pass
    print("Done.")

if __name__ == '__main__':
    main()

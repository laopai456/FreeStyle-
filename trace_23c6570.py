"""
trace_23c6570.py — Hook 实际装包装包函数, 追踪 ItemCode 来源

0x19247a0 (equip fn) 内部调用 0x23c6570, 我们 hook 0x23c6570:
- dump 所有参数和 this
- 在参数/this中搜索 ItemCode 范围 (0x02F00000~0x03200000)
- 回溯调用栈

用法: py trace_23c6570.py
  装备粉色网红主播 (50122721), 看输出
"""
import frida, json, sys, time

KNOWN_IC = 50122721
IC_MIN = 0x02F00000
IC_MAX = 0x03200000

JS = r"""
'use strict';

var g_targetIC = """ + str(KNOWN_IC) + r""";
var IC_MIN = 0x02F00000;
var IC_MAX = 0x03200000;

// Hook 0x23c6570 (被 0x19247a0 调用的实际发包函数)
var targetFn = ptr(0x23c6570);
var g_hooked = false;

function hookPktBuilder() {
    if (g_hooked) return;
    Interceptor.attach(targetFn, {
        onEnter: function(args) {
            var thisPtr = this.context.ecx;

            // 读参数 (可能是 thiscall + stack params)
            var stackBase = this.context.esp;
            var retAddr = stackBase.readU32();
            var arg0 = stackBase.add(4).readU32();
            var arg1 = stackBase.add(8).readU32();
            var arg2 = stackBase.add(12).readU32();
            var arg3 = stackBase.add(16).readU32();

            var result = {
                type: 'PKT_BUILDER',
                thisPtr: thisPtr.isNull() ? 'NULL' : thisPtr.toString(),
                retAddr: ptr(retAddr).toString(),
                arg0: '0x' + arg0.toString(16),
                arg1: '0x' + arg1.toString(16),
                arg2: '0x' + arg2.toString(16),
                arg3: '0x' + arg3.toString(16),
                eax: this.context.eax.toString(),
                edx: this.context.edx.toString(),
                ebx: this.context.ebx.toString(),
                esi: this.context.esi.toString(),
                edi: this.context.edi.toString()
            };

            // 搜索寄存器中是否有 ItemCode
            var regs = {
                eax: this.context.eax,
                edx: this.context.edx,
                ebx: this.context.ebx,
                esi: this.context.esi,
                edi: this.context.edi
            };
            result.regICs = {};
            for (var name in regs) {
                var v = regs[name].toInt32() >>> 0;
                if (v >= IC_MIN && v <= IC_MAX) {
                    result.regICs[name] = '0x' + v.toString(16);
                }
            }

            // 搜索 this 对象中的 ItemCode
            if (!thisPtr.isNull()) {
                var thisHits = [];
                for (var off = 0; off < 0x400; off += 4) {
                    try {
                        var val = thisPtr.add(off).readU32();
                        if (val >= IC_MIN && val <= IC_MAX) {
                            thisHits.push({off: off, val: '0x' + val.toString(16)});
                        }
                    } catch(e) {}
                }
                result.thisICs = thisHits;

                // 也搜索 this->ptr 一级
                var ptrHits = [];
                for (var off = 0; off < 0x100; off += 4) {
                    try {
                        var sub = thisPtr.add(off).readPointer();
                        if (sub.isNull() || sub.compare(ptr(0x10000)) < 0) continue;
                        for (var sOff = 0; sOff < 0x200; sOff += 4) {
                            try {
                                var val = sub.add(sOff).readU32();
                                if (val >= IC_MIN && val <= IC_MAX) {
                                    ptrHits.push({thisOff: off, subOff: sOff, val: '0x' + val.toString(16)});
                                }
                            } catch(e) {}
                        }
                    } catch(e) {}
                }
                result.ptrICs = ptrHits;
            }

            // 搜索栈上的 ItemCode
            var stackICs = [];
            for (var off = 0; off < 0x100; off += 4) {
                try {
                    var val = stackBase.add(off).readU32();
                    if (val >= IC_MIN && val <= IC_MAX) {
                        stackICs.push({off: off, val: '0x' + val.toString(16)});
                    }
                } catch(e) {}
            }
            result.stackICs = stackICs;

            // 回溯
            var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).map(DebugSymbol.fromAddress);
            result.backtrace = bt.map(function(s) { return s.toString(); });

            send(JSON.stringify(result));
        }
    });
    g_hooked = true;
    send(JSON.stringify({type:'info', msg:'Hooked 0x23c6570, equip now'}));
}

hookPktBuilder();
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

    print(f"PID={pid}  Hooking 0x23c6570 (packet builder)")
    print("Equip item now. Ctrl+C to stop.\n")

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
        if t == 'PKT_BUILDER':
            print(f"  === PKT BUILDER 0x23c6570 ===")
            print(f"  this={p['thisPtr']}  ret={p['retAddr']}")
            print(f"  args: {p['arg0']} {p['arg1']} {p['arg2']} {p['arg3']}")
            print(f"  regs: eax={p['eax']} edx={p['edx']} ebx={p['ebx']} esi={p['esi']} edi={p['edi']}")
            if p.get('regICs') and len(p['regICs']) > 0:
                print(f"  ** REG ICs: {json.dumps(p['regICs'])}")
            if p.get('thisICs') and len(p['thisICs']) > 0:
                print(f"  ** this ICs:")
                for h in p['thisICs']:
                    print(f"       this+0x{h['off']:X} = {h['val']}")
            if p.get('ptrICs') and len(p['ptrICs']) > 0:
                print(f"  ** this->ptr ICs:")
                for h in p['ptrICs']:
                    print(f"       this+0x{h['thisOff']:X} -> +0x{h['subOff']:X} = {h['val']}")
            if p.get('stackICs') and len(p['stackICs']) > 0:
                print(f"  ** stack ICs:")
                for h in p['stackICs']:
                    print(f"       esp+0x{h['off']:X} = {h['val']}")
            print(f"  backtrace:")
            for f in p.get('backtrace', [])[:8]:
                print(f"    {f}")
            print()
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

import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    disasmFrames: function() {
        var addrs = [0x19227b6, 0x1b90ed0, 0x573793, 0x1846194];
        var results = [];
        
        for (var ai = 0; ai < addrs.length; ai++) {
            var target = ptr(addrs[ai]);
            // 向前找函数入口 (push ebp; mov ebp, esp)
            var funcStart = null;
            for (var back = 0; back < 200; back++) {
                try {
                    var b0 = target.sub(back).readU8();
                    if (b0 === 0x55) {
                        var b1 = target.sub(back).add(1).readU8();
                        var b2 = target.sub(back).add(2).readU8();
                        if (b1 === 0x8B && b2 === 0xEC) {
                            funcStart = target.sub(back);
                            break;
                        }
                    }
                } catch(e) {}
            }
            
            // 从函数入口反汇编 30 条指令
            var start = funcStart || target.sub(0x20);
            var insns = [];
            var addr = start;
            for (var j = 0; j < 40; j++) {
                try {
                    var insn = Instruction.parse(addr);
                    insns.push({
                        addr: addr.toString(),
                        mn: insn.mnemonic,
                        op: insn.opStr,
                        size: insn.size
                    });
                    addr = addr.add(insn.size);
                } catch(e) {
                    insns.push({addr: addr.toString(), mn: '??', op: '', size: 1});
                    addr = addr.add(1);
                }
            }
            
            results.push({
                target: target.toString(),
                funcStart: funcStart ? funcStart.toString() : 'unknown',
                insns: insns
            });
        }
        return JSON.stringify(results);
    }
};
""";

pid = int(sys.argv[1]) if len(sys.argv) > 1 else None
if not pid:
    import subprocess
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FreeStyle.exe', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            pid = int(parts[1])
            break

print(f"PID={pid}")
session = frida.attach(pid)
script = session.create_script(JS)
script.load()

data = json.loads(script.exports_sync.disasmframes())
for entry in data:
    print(f"\n{'='*60}")
    print(f"Frame {entry['target']}  func_start={entry['funcStart']}")
    print(f"{'='*60}")
    for ins in entry['insns']:
        mark = ""
        if '0x50' in ins['op'] or 'item' in ins['op'].lower():
            mark = "  <<<"
        print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{mark}")

session.detach()

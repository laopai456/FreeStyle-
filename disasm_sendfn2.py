"""
disasm_sendfn2.py — 反汇编 0x24387f0 (实际发包函数)
找出 12B 装备 payload 从哪来

用法: py disasm_sendfn2.py
"""
import frida, json, sys

JS = r"""
'use strict';
rpc.exports = {
    disasm: function() {
        var target = ptr(0x24387f0);
        // 找函数入口
        var funcStart = null;
        for (var back = 0; back < 0x200; back++) {
            try {
                var addr = target.sub(back);
                var b0 = addr.readU8();
                var b1 = addr.add(1).readU8();
                var b2 = addr.add(2).readU8();
                if (b0 === 0x55 && b1 === 0x8B && b2 === 0xEC) {
                    funcStart = addr;
                    break;
                }
                if (b0 === 0x8B && b1 === 0xFF && b2 === 0x55) {
                    funcStart = addr;
                    break;
                }
            } catch(e) {}
        }

        var results = [];
        var addr = funcStart || target.sub(0x20);
        for (var i = 0; i < 300; i++) {
            try {
                var insn = Instruction.parse(addr);
                var mark = '';
                if (insn.mnemonic === 'call') mark += ' [CALL]';
                if (insn.mnemonic === 'ret') mark += ' [RET]';
                if (insn.mnemonic === 'jmp' && insn.opStr.indexOf('0x') === 0) mark += ' [JMP]';
                results.push({
                    addr: addr.toString(),
                    mn: insn.mnemonic,
                    op: insn.opStr,
                    size: insn.size,
                    mark: mark
                });
                addr = addr.add(insn.size);
                if (insn.mnemonic === 'ret' && i > 10) break;
            } catch(e) {
                results.push({addr: addr.toString(), mn: '??', op: '', size: 1, mark: ''});
                addr = addr.add(1);
            }
        }
        return JSON.stringify({
            funcStart: funcStart ? funcStart.toString() : 'NOT FOUND',
            count: results.length,
            insns: results
        });
    }
};
""";

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
    print("FreeStyle.exe not found")
    sys.exit(1)

print(f"PID={pid}")
session = frida.attach(pid)
script = session.create_script(JS)
script.load()

data = json.loads(script.exports_sync.disasm())
print(f"Func start: {data['funcStart']}")
print(f"Instructions: {data['count']}\n")
for ins in data['insns']:
    print(f"  {ins['addr']}: {ins['mn']:8s} {ins['op']}{ins['mark']}")

session.detach()
print("\nDone.")
